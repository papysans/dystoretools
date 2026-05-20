"""DeepSeek REST client. Uses the OpenAI-compatible /v1/chat/completions endpoint."""
import httpx

from dystore.core.logging import get_logger
from dystore.core.settings_store import get as get_setting

log = get_logger(__name__)


class DeepSeekClient:
    def __init__(self, *, model: str | None = None) -> None:
        self._model_override = model

    async def _resolve(self) -> tuple[str, str, str]:
        api_key = await get_setting("deepseek_api_key") or ""
        base_url = (await get_setting("deepseek_base_url") or "https://api.deepseek.com").rstrip("/")
        model = self._model_override or await get_setting("deepseek_model") or "deepseek-v4-pro"
        return api_key, base_url, model

    @property
    def model(self) -> str:
        # Best-effort sync access for logging; real value resolved per-call.
        return self._model_override or "deepseek-v4-pro"

    async def chat(self, prompt: str, *, max_tokens: int = 2048, timeout: float = 60.0) -> dict:
        api_key, base_url, model = await self._resolve()
        if not api_key:
            raise RuntimeError("DeepSeek API key missing — set via Settings page or DEEPSEEK_API_KEY env")
        url = f"{base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "text": choice,
            "model": model,
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "raw": data,
        }
