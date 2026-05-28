import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from dystore.api.v1 import member as member_api
from dystore.api.v1.member import router as member_router
from dystore.db import session as db_session


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(member_router)
    return app


@pytest.fixture(autouse=True)
async def _reset_engine():
    """Dispose the shared async engine after each test so pooled
    connections do not get attached to a stale event loop."""
    yield
    await db_session.engine.dispose()
    # Silence reference to keep import used.
    assert member_api.router is member_router


@pytest.mark.asyncio
async def test_member_dashboard_agg_has_kpis():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/member/dashboard")
    assert r.status_code == 200
    body = r.json()
    agg = body["agg"]
    assert isinstance(agg, list)
    assert len(agg) >= 1
    required_keys = {"index_name", "index_display", "value", "unit"}
    for item in agg:
        assert required_keys.issubset(item.keys())


@pytest.mark.asyncio
async def test_member_dashboard_daily_returns_seven_rows_ascending():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/member/dashboard")
    assert r.status_code == 200
    daily = r.json()["daily"]
    assert isinstance(daily, list)
    assert len(daily) == 7
    dates = [item["date"] for item in daily]
    assert dates == sorted(dates)
    for item in daily:
        assert {"date", "metric", "value"}.issubset(item.keys())


@pytest.mark.asyncio
async def test_member_dashboard_hist_dedups_to_eight_buckets():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/member/dashboard")
    assert r.status_code == 200
    hist = r.json()["hist"]
    assert isinstance(hist, list)
    assert len(hist) == 8
    buckets = [item["bucket"] for item in hist]
    assert len(set(buckets)) == 8
    for item in hist:
        assert {"bucket", "value", "dim"}.issubset(item.keys())
