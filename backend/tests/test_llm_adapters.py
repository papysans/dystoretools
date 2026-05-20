import httpx
import pytest

from dystore.db.models import LlmProvider
from dystore.llm.adapters import AnthropicAdapter, OpenAICompatibleAdapter
from dystore.llm.types import LLMMessage, ToolSchema


@pytest.mark.asyncio
async def test_openai_adapter_parses_text(monkeypatch) -> None:
    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = LlmProvider(id=1, name="x", adapter_kind="openai_compat", base_url="https://example.com")
    result = await OpenAICompatibleAdapter(provider).complete([LLMMessage("user", "hi")], model="m")
    assert result.text == "ok"
    assert result.tokens_in == 1


@pytest.mark.asyncio
async def test_openai_adapter_parses_tool_call(monkeypatch) -> None:
    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {"name": "run_readonly_sql", "arguments": "{\"sql\":\"select 1\"}"},
                                }
                            ]
                        }
                    }
                ],
                "usage": {},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = LlmProvider(id=1, name="x", adapter_kind="openai_compat", base_url="https://example.com")
    result = await OpenAICompatibleAdapter(provider).complete(
        [LLMMessage("user", "hi")],
        model="m",
        tools=[ToolSchema(name="run_readonly_sql", description="sql", parameters={"type": "object"})],
    )
    assert result.tool_calls[0].name == "run_readonly_sql"
    assert result.tool_calls[0].arguments == {"sql": "select 1"}


@pytest.mark.asyncio
async def test_openai_adapter_formats_tool_roundtrip(monkeypatch) -> None:
    captured = {}

    async def fake_post(self, url, headers=None, json=None):
        captured.update(json or {})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "done"}}], "usage": {}},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = LlmProvider(id=1, name="x", adapter_kind="openai_compat", base_url="https://example.com")
    await OpenAICompatibleAdapter(provider).complete(
        [
            LLMMessage(
                "assistant",
                "",
                tool_calls=[{"id": "call_1", "name": "run_readonly_sql", "arguments": {"sql": "select 1"}}],
            ),
            LLMMessage("tool", "{\"ok\":true}", tool_call_id="call_1", name="run_readonly_sql"),
        ],
        model="m",
    )

    assert captured["messages"][0]["tool_calls"][0]["type"] == "function"
    assert captured["messages"][0]["tool_calls"][0]["function"]["name"] == "run_readonly_sql"
    assert captured["messages"][1]["role"] == "tool"
    assert captured["messages"][1]["tool_call_id"] == "call_1"


@pytest.mark.asyncio
async def test_anthropic_adapter_parses_tool_call(monkeypatch) -> None:
    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "content": [
                    {"type": "text", "text": "thinking"},
                    {"type": "tool_use", "id": "toolu_1", "name": "describe_schema", "input": {"table": "x"}},
                ],
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = LlmProvider(id=2, name="a", adapter_kind="anthropic", base_url="https://example.com")
    result = await AnthropicAdapter(provider).complete([LLMMessage("user", "hi")], model="claude")
    assert result.text == "thinking"
    assert result.tool_calls[0].name == "describe_schema"
    assert result.tokens_out == 4
