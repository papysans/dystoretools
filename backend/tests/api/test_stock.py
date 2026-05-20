import pytest
from httpx import ASGITransport, AsyncClient

from dystore.db import session as db_session
from dystore.main import app


@pytest.fixture(autouse=True)
async def _reset_engine():
    """Dispose the shared async engine after each test so pooled
    connections do not get attached to a stale event loop."""
    yield
    await db_session.engine.dispose()


@pytest.mark.asyncio
async def test_list_stock_returns_total_20():
    # The /api/v1/stock endpoint uses MAX(scraped_at) per goods_id, so it
    # returns one row per unique goods_id (10), not raw snapshots (20).
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/stock", params={"page": 0, "page_size": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 10
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_stock_each_item_has_level():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/stock", params={"page": 0, "page_size": 50})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 1
    valid = {"out", "low", "normal", "over"}
    for item in body["items"]:
        assert "level" in item
        assert item["level"] in valid


@pytest.mark.asyncio
async def test_stock_levels_structure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/stock/levels")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"out", "low", "normal", "over"}
    out, low, normal, over = body["out"], body["low"], body["normal"], body["over"]
    for v in (out, low, normal, over):
        assert isinstance(v, int)
        assert v >= 0
    total = out + low + normal + over
    assert total >= 1
    assert total == body["out"] + body["low"] + body["normal"] + body["over"]


@pytest.mark.asyncio
async def test_list_stock_include_skus_returns_skus_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/stock", params={"page": 0, "page_size": 50, "include": "skus"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 1
    for item in body["items"]:
        assert "skus" in item
        assert isinstance(item["skus"], list)
