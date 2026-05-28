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
async def test_list_goods_returns_total_24():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/goods", params={"page": 0, "page_size": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 24
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_goods_filter_tab_on_sale():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/goods", params={"tab": "售卖中", "page_size": 200})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 1
    assert all(item["tab"] == "售卖中" for item in body["items"])


@pytest.mark.asyncio
async def test_list_goods_pagination_beyond_last_page():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/goods", params={"page": 99, "page_size": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 24
