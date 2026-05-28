"""LLM gateway with DeepSeek/Kimi routing, retry, accounting."""
import asyncio
from collections.abc import Sequence
from typing import Literal

import httpx
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from dystore.core.logging import get_logger
from dystore.db.models import LlmModel, LlmProvider
from dystore.db.session import SessionLocal
from dystore.llm.adapters import adapter_for
from dystore.llm.accounting import record_failure, record_success
from dystore.llm.providers.deepseek import DeepSeekClient
from dystore.llm.providers.kimi import KimiClient
from dystore.llm.pii_scrub import Scrubber
from dystore.llm.types import LLMMessage, LLMResult, ToolSchema

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
    provider_id: int | None = None,
    model_name: str | None = None,
    tools: Sequence[ToolSchema] | None = None,
) -> dict:
    scrubbed_prompt = Scrubber().scrub(prompt)
    try:
        registry_result = await _complete_via_registry(
            [LLMMessage(role="user", content=scrubbed_prompt)],
            kind=kind,
            max_tokens=max_tokens,
            prefer=prefer,
            parent_id=parent_id,
            provider_id=provider_id,
            model_name=model_name,
            tools=list(tools or []),
        )
        if registry_result is not None:
            return registry_result
    except Exception as e:
        log.warning("llm.registry_route_failed", error=str(e))

    return await _complete_legacy(scrubbed_prompt, kind=kind, max_tokens=max_tokens, prefer=prefer, parent_id=parent_id)


async def complete_messages(
    messages: list[LLMMessage],
    *,
    kind: str,
    max_tokens: int = 2048,
    prefer: Prefer = "default",
    parent_id: int | None = None,
    provider_id: int | None = None,
    model_name: str | None = None,
    tools: Sequence[ToolSchema] | None = None,
    scrub_pii: bool = True,
) -> dict:
    if scrub_pii:
        scrubber = Scrubber()
        llm_messages = [
            LLMMessage(
                role=m.role,
                content=scrubber.scrub(m.content),
                tool_call_id=m.tool_call_id,
                name=m.name,
                tool_calls=m.tool_calls,
            )
            for m in messages
        ]
    else:
        llm_messages = messages
    result = await _complete_via_registry(
        llm_messages,
        kind=kind,
        max_tokens=max_tokens,
        prefer=prefer,
        parent_id=parent_id,
        provider_id=provider_id,
        model_name=model_name,
        tools=list(tools or []),
    )
    if result is not None:
        return result
    prompt = "\n\n".join(f"{m.role}: {m.content}" for m in llm_messages)
    return await _complete_legacy(prompt, kind=kind, max_tokens=max_tokens, prefer=prefer, parent_id=parent_id)


async def _complete_via_registry(
    messages: list[LLMMessage],
    *,
    kind: str,
    max_tokens: int,
    prefer: Prefer,
    parent_id: int | None,
    provider_id: int | None,
    model_name: str | None,
    tools: list[ToolSchema],
) -> dict | None:
    selected = await _resolve_model(provider_id=provider_id, model_name=model_name, prefer=prefer, need_tools=bool(tools))
    if selected is None:
        return None
    provider, model = selected
    adapter = adapter_for(provider)
    prompt_hash_material = "\n\n".join(f"{m.role}: {m.content}" for m in messages)
    try:
        result = await _call_adapter_with_retry(adapter, messages, model=model, tools=tools, max_tokens=max_tokens)
    except Exception as exc:
        await record_failure(
            kind=kind,
            prompt=prompt_hash_material,
            model=model.model_name,
            provider_id=provider.id,
            error_msg=str(exc),
        )
        raise
    tool_calls_json = [
        {"id": call.id, "name": call.name, "arguments": call.arguments}
        for call in result.tool_calls
    ] or None
    row_id = await record_success(
        kind=kind,
        prompt=prompt_hash_material,
        output_text=result.text,
        model=result.model,
        provider_id=result.provider_id,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        parent_id=parent_id,
        tool_calls_json=tool_calls_json,
    )
    return result.to_dict(ai_generation_id=row_id)


async def _complete_legacy(
    prompt: str,
    *,
    kind: str,
    max_tokens: int,
    prefer: Prefer,
    parent_id: int | None,
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


async def _call_adapter_with_retry(
    adapter,
    messages: list[LLMMessage],
    *,
    model: LlmModel,
    tools: list[ToolSchema],
    max_tokens: int,
) -> LLMResult:
    backoff = 2.0
    for attempt in range(1, 4):
        try:
            return await adapter.complete(messages, model=model.model_name, tools=tools, max_tokens=max_tokens)
        except Exception as e:
            if not _is_retryable(e) or attempt == 3:
                raise
            await asyncio.sleep(backoff)
            backoff *= 2
    raise RuntimeError("unreachable")


async def _resolve_model(
    *,
    provider_id: int | None,
    model_name: str | None,
    prefer: Prefer,
    need_tools: bool,
) -> tuple[LlmProvider, LlmModel] | None:
    try:
        async with SessionLocal() as s:
            q = select(LlmProvider, LlmModel).join(LlmModel, LlmModel.provider_id == LlmProvider.id).where(
                LlmProvider.enabled.is_(True),
                LlmModel.enabled.is_(True),
            )
            if provider_id is not None:
                q = q.where(LlmProvider.id == provider_id)
            if model_name is not None:
                q = q.where(LlmModel.model_name == model_name)
            if provider_id is None and model_name is None:
                if prefer == "long_context":
                    q = q.order_by(desc(LlmModel.context_window))
                else:
                    q = q.where(LlmModel.is_default_for_chat.is_(True))
            rows = (await s.execute(q)).all()
    except SQLAlchemyError:
        return None
    for provider, model in rows:
        caps = set(model.capabilities_json or [])
        if "chat" not in caps:
            continue
        if need_tools and "function_calling" not in caps:
            continue
        return provider, model
    return None
