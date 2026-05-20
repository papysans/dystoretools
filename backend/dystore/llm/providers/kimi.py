"""Kimi (Moonshot) REST client. Uses OpenAI-compatible /v1/chat/completions endpoint."""
import httpx

from dystore.core.settings_store import get as get_setting


class KimiClient:
    def __init__(self, *, model: str | None = None) -> None:
        self._model_override = model

    @property
    def model(self) -> str:
        return self._model_override or "moonshot-v1-128k"

    async def _resolve(self) -> tuple[str, str, str]:
        api_key = await get_setting("kimi_api_key") or ""
        base_url = (await get_setting("kimi_base_url") or "https://api.moonshot.cn/v1").rstrip("/")
        model = self._model_override or await get_setting("kimi_model") or "moonshot-v1-128k"
        return api_key, base_url, model

    async def chat(self, prompt: str, *, max_tokens: int = 2048, timeout: float = 90.0) -> dict:
        api_key, base_url, model = await self._resolve()
        if not api_key:
            raise RuntimeError("Kimi API key missing — set via Settings page or KIMI_API_KEY env")
        url = f"{base_url}/chat/completions"
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
        return {
            "text": data["choices"][0]["message"]["content"],
            "model": model,
            "tokens_in": data.get("usage", {}).get("prompt_tokens", 0),
            "tokens_out": data.get("usage", {}).get("completion_tokens", 0),
            "raw": data,
        }
