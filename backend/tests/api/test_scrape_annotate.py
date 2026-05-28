from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dystore.api.v1.scrape_annotate import router as annotate_router
from dystore.main import app


@pytest.fixture
def app_with_annotate_router():
    existing_paths = {r.path for r in app.routes}
    new_routes = [r for r in annotate_router.routes if r.path not in existing_paths]
    for r in new_routes:
        app.router.routes.append(r)
    try:
        yield app
    finally:
        for r in new_routes:
            if r in app.router.routes:
                app.router.routes.remove(r)


@pytest.mark.asyncio
async def test_annotate_now_returns_worker_result(app_with_annotate_router):
    expected = {"ok": 3, "failed": 0, "total": 3}
    with patch(
        "dystore.api.v1.scrape_annotate.annotate_pending",
        new=AsyncMock(return_value=expected),
    ):
        transport = ASGITransport(app=app_with_annotate_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/scrape/annotate-now")
    assert r.status_code == 200
    assert r.json() == expected


@pytest.mark.asyncio
async def test_annotate_now_returns_skipped_payload_without_error(app_with_annotate_router):
    expected = {
        "ok": 0,
        "failed": 0,
        "total": 0,
        "skipped": "budget_exhausted",
        "spend_yuan": 5.1,
    }
    with patch(
        "dystore.api.v1.scrape_annotate.annotate_pending",
        new=AsyncMock(return_value=expected),
    ):
        transport = ASGITransport(app=app_with_annotate_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/scrape/annotate-now")
    assert r.status_code == 200
    body = r.json()
    assert "skipped" in body
    assert body == expected
