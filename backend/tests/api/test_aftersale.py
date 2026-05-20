import pytest
from httpx import ASGITransport, AsyncClient

from dystore.api.v1._enums import AFTERSALE_CANONICAL_DIMS
from dystore.db import session as db_session
from dystore.main import app


@pytest.fixture(autouse=True)
async def _reset_engine():
    """Dispose the shared async engine after each test so pooled
    connections do not get attached to a stale event loop."""
    yield
    await db_session.engine.dispose()


@pytest.mark.asyncio
async def test_list_aftersale_returns_total_30():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/aftersale", params={"page": 0, "page_size": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 30
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_aftersale_filter_status_6():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/aftersale", params={"status": 6, "page_size": 200})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 1
    assert all(item["status"] == 6 for item in body["items"])
    assert all(item["status_label"] == "待审核" for item in body["items"])


@pytest.mark.asyncio
async def test_aftersale_counts_has_18_canonical_dims():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/aftersale/counts")
    assert r.status_code == 200
    body = r.json()
    assert "dims" in body
    assert "scraped_at" in body
    assert len(body["dims"]) == 18


@pytest.mark.asyncio
async def test_aftersale_counts_keys_match_canonical():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/aftersale/counts")
    assert r.status_code == 200
    body = r.json()
    assert set(body["dims"].keys()) == set(AFTERSALE_CANONICAL_DIMS)
