from __future__ import annotations

import json
from typing import Any

import httpx

from dystore.db.models import LlmProvider
from dystore.llm.registry.crypto import decrypt_secret
from dystore.llm.types import LLMAdapter, LLMMessage, LLMResult, ToolCall, ToolSchema


class OpenAICompatibleAdapter(LLMAdapter):
    def __init__(self, provider: LlmProvider) -> None:
        self.provider = provider

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        tools: list[ToolSchema] | None = None,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResult:
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            **(self.provider.default_headers_json or {}),
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [_message_to_openai(message) for message in messages],
            "max_tokens": max_tokens,
            "stream": False,
        }
        if _is_deepseek_endpoint(self.provider, model):
            # DeepSeek V4 defaults to thinking mode; tool-call continuations then require
            # reasoning_content to be replayed. Disable it for stable OpenAI-compatible tools.
            payload["thinking"] = {"type": "disabled"}
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.provider.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        msg = data["choices"][0]["message"]
        usage = data.get("usage", {})
        tool_calls = [_parse_openai_tool_call(call) for call in msg.get("tool_calls") or []]
        return LLMResult(
            text=msg.get("content") or "",
            model=model,
            provider_id=self.provider.id,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            raw=data,
            tool_calls=tool_calls,
        )

    def _api_key(self) -> str:
        return decrypt_secret(self.provider.api_key_encrypted) if self.provider.api_key_encrypted else ""


class AnthropicAdapter(LLMAdapter):
    def __init__(self, provider: LlmProvider) -> None:
        self.provider = provider

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        tools: list[ToolSchema] | None = None,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResult:
        system, user_messages = _split_anthropic_messages(messages)
        headers = {
            "x-api-key": self._api_key(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            **(self.provider.default_headers_json or {}),
        }
        payload: dict[str, Any] = {"model": model, "messages": user_messages, "max_tokens": max_tokens}
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}
                for tool in tools
            ]
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{self.provider.base_url.rstrip('/')}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text") or "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.get("id") or "", name=block.get("name") or "", arguments=block.get("input") or {})
                )
        usage = data.get("usage", {})
        return LLMResult(
            text="".join(text_parts),
            model=model,
            provider_id=self.provider.id,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            raw=data,
            tool_calls=tool_calls,
        )

    def _api_key(self) -> str:
        return decrypt_secret(self.provider.api_key_encrypted) if self.provider.api_key_encrypted else ""


def adapter_for(provider: LlmProvider) -> LLMAdapter:
    if provider.adapter_kind == "openai_compat":
        return OpenAICompatibleAdapter(provider)
    if provider.adapter_kind == "anthropic":
        return AnthropicAdapter(provider)
    raise ValueError(f"unsupported adapter kind: {provider.adapter_kind}")


def _message_to_openai(message: LLMMessage) -> dict[str, Any]:
    out: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.role == "assistant" and message.tool_calls:
        out["content"] = None
        out["tool_calls"] = [
            {
                "id": call.get("id") or "",
                "type": "function",
                "function": {
                    "name": call.get("name") or "",
                    "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
                },
            }
            for call in message.tool_calls
        ]
    if message.role == "tool" and message.tool_call_id:
        out["tool_call_id"] = message.tool_call_id
    if message.name and message.role != "tool":
        out["name"] = message.name
    return out


def _parse_openai_tool_call(call: dict[str, Any]) -> ToolCall:
    fn = call.get("function") or {}
    raw_args = fn.get("arguments") or "{}"
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError:
        args = {"_raw": raw_args}
    return ToolCall(id=call.get("id") or "", name=fn.get("name") or "", arguments=args)


def _is_deepseek_endpoint(provider: LlmProvider, model: str) -> bool:
    haystack = " ".join([provider.name or "", provider.base_url or "", model or ""]).lower()
    return "deepseek" in haystack


def _split_anthropic_messages(messages: list[LLMMessage]) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    out: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
        elif message.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.tool_call_id or "",
                            "content": message.content,
                        }
                    ],
                }
            )
        else:
            out.append({"role": message.role, "content": message.content})
    return ("\n\n".join(system_parts) if system_parts else None), out
