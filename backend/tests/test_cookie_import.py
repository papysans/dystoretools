import pytest

from dystore.api.v1.auth import capture_cookies_endpoint
from dystore.auth import cookie_import


@pytest.mark.asyncio
async def test_capture_current_cookies_marks_session_ready(monkeypatch) -> None:
    emitted: list[tuple[str, dict]] = []

    class FakePage:
        url = "https://fxg.jinritemai.com/ffa/mshop/homepage/index"

        async def goto(self, url: str, wait_until: str) -> None:
            assert "fxg.jinritemai.com" in url
            assert wait_until == "domcontentloaded"

        async def close(self) -> None:
            return None

    class FakeContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def new_page(self) -> FakePage:
            return FakePage()

        async def cookies(self) -> list[dict]:
            return [
                {"name": "SESSIONID", "value": "ok", "domain": ".jinritemai.com"},
                {"name": "ignored", "value": "x", "domain": ".example.com"},
            ]

    def fake_merchant_context(*, headless: bool | None = None) -> FakeContext:
        assert headless is True
        return FakeContext()

    async def fake_emit(kind: str, payload: dict | None = None) -> None:
        emitted.append((kind, payload or {}))

    monkeypatch.setattr(cookie_import, "merchant_context", fake_merchant_context)
    monkeypatch.setattr(cookie_import, "emit_session_event", fake_emit)

    result = await cookie_import.capture_current_cookies()

    assert result == {"captured": 1, "total_available": 2}
    assert emitted == [
        ("login_succeeded", {"via": "browser_capture", "count": 1}),
        ("session_ready", {"via": "browser_capture"}),
    ]


@pytest.mark.asyncio
async def test_capture_cookies_endpoint_returns_error_payload(monkeypatch) -> None:
    async def fail_capture() -> dict:
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr("dystore.api.v1.auth.capture_current_cookies", fail_capture)

    assert await capture_cookies_endpoint() == {"captured": 0, "error": "RuntimeError: browser unavailable"}


@pytest.mark.asyncio
async def test_capture_current_cookies_rejects_login_page(monkeypatch) -> None:
    emitted: list[tuple[str, dict]] = []

    class FakePage:
        url = "https://fxg.jinritemai.com/login/common"

        async def goto(self, url: str, wait_until: str) -> None:
            return None

        async def close(self) -> None:
            return None

    class FakeContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def new_page(self) -> FakePage:
            return FakePage()

        async def cookies(self) -> list[dict]:
            return [{"name": "SESSIONID", "value": "stale", "domain": ".jinritemai.com"}]

    def fake_merchant_context(*, headless: bool | None = None) -> FakeContext:
        return FakeContext()

    async def fake_emit(kind: str, payload: dict | None = None) -> None:
        emitted.append((kind, payload or {}))

    monkeypatch.setattr(cookie_import, "merchant_context", fake_merchant_context)
    monkeypatch.setattr(cookie_import, "emit_session_event", fake_emit)

    result = await cookie_import.capture_current_cookies()

    assert result == {"captured": 0, "error": "browser profile is not logged in yet"}
    assert emitted == []
