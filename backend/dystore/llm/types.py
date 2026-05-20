from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class LLMMessage:
    role: MessageRole
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMResult:
    text: str = ""
    model: str = ""
    provider_id: int | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    raw: dict[str, Any] | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def terminal_text(self) -> bool:
        return bool(self.text) and not self.tool_calls

    def to_dict(self, *, ai_generation_id: int | None = None) -> dict:
        data = {
            "text": self.text,
            "model": self.model,
            "provider_id": self.provider_id,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "raw": self.raw,
            "tool_calls": [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in self.tool_calls
            ],
        }
        if ai_generation_id is not None:
            data["ai_generation_id"] = ai_generation_id
        return data


class LLMAdapter:
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        tools: list[ToolSchema] | None = None,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResult:
        raise NotImplementedError

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        tools: list[ToolSchema] | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        result = await self.complete(messages, model=model, tools=tools, max_tokens=max_tokens, stream=False)
        if result.text:
            yield result.text
