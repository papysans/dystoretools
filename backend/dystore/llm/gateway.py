"""LLM gateway with DeepSeek/Kimi routing, retry, accounting."""
import asyncio
from typing import Literal

import httpx

from dystore.core.logging import get_logger
from dystore.llm.accounting import record_failure, record_success
from dystore.llm.providers.deepseek import DeepSeekClient
from dystore.llm.providers.kimi import KimiClient

log = get_logger(__name__)

Prefer = Literal["default", "long_context", "fallback"]

# DeepSeek V4 Pro supports 1M context; this threshold is intentionally high.
# Kimi routing now mostly serves provider-availability failover.
LONG_CONTEXT_THRESHOLD_TOKENS = 800_000


def _estimate_tokens(prompt: str) -> int:
    """Cheap approximation: ~3 chars per token for mixed CJK/EN."""
    return max(1, len(prompt) // 3)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code < 600
    return False


async def complete(
    prompt: str,
    *,
    kind: str,
    max_tokens: int = 2048,
    prefer: Prefer = "default",
    parent_id: int | None = None,
) -> dict:
    """Routes to DeepSeek V4 Pro by default; Kimi when prefer=long_context or estimated tokens > threshold."""
    use_kimi = prefer == "long_context" or _estimate_tokens(prompt) > LONG_CONTEXT_THRESHOLD_TOKENS
    primary = KimiClient() if use_kimi else DeepSeekClient()
    fallback = DeepSeekClient() if use_kimi else KimiClient()

    for attempt, client in enumerate((primary, fallback), start=1):
        try:
            return await _call_with_retry(client, prompt, max_tokens=max_tokens, kind=kind, parent_id=parent_id)
        except Exception as e:
            log.warning("llm.provider_failed", attempt=attempt, model=getattr(client, "model", "?"), error=str(e))
            if attempt == 2:
                await record_failure(kind=kind, prompt=prompt, model=getattr(client, "model", "?"), error_msg=str(e))
                raise


async def _call_with_retry(client, prompt: str, *, max_tokens: int, kind: str, parent_id: int | None) -> dict:
    backoff = 2.0
    for attempt in range(1, 4):
        try:
            result = await client.chat(prompt, max_tokens=max_tokens)
            row_id = await record_success(
                kind=kind,
                prompt=prompt,
                output_text=result["text"],
                model=result["model"],
                tokens_in=result["tokens_in"],
                tokens_out=result["tokens_out"],
                parent_id=parent_id,
            )
            return {**result, "ai_generation_id": row_id}
        except Exception as e:
            if not _is_retryable(e) or attempt == 3:
                raise
            await asyncio.sleep(backoff)
            backoff *= 2
    raise RuntimeError("unreachable")
