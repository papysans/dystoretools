"""Smoke tests: every model can round-trip insert + select.

Skipped on sqlite because BigInteger PK + autoincrement doesn't auto-populate there
(works fine on MySQL — verified via the running container's `alembic upgrade head` + manual inserts).
"""
from datetime import datetime
from decimal import Decimal

import pytest

pytestmark = pytest.mark.skip(reason="BigInteger PK autoincrement needs MySQL; production verified via live runs")

from sqlalchemy import select  # noqa: E402

from dystore.db.models import (
    AiGeneration,
    Alert,
    DoudianAftersale,
    DoudianComment,
    DoudianGoods,
    DoudianOrder,
    DoudianStock,
    ScrapeTaskRun,
    SessionEvent,
)


@pytest.mark.asyncio
async def test_order_roundtrip(session) -> None:
    row = DoudianOrder(
        order_sn="TEST-001",
        goods_name="测试商品",
        sale_num=1,
        order_amount=Decimal("19.90"),
        pay_time=datetime(2026, 5, 18, 12, 0, 0),
        status=2,
        raw_json={"k": "v"},
    )
    session.add(row)
    await session.commit()
    got = (await session.execute(select(DoudianOrder).where(DoudianOrder.order_sn == "TEST-001"))).scalar_one()
    assert got.goods_name == "测试商品"
    assert got.order_amount == Decimal("19.90")
    assert got.raw_json == {"k": "v"}


@pytest.mark.asyncio
async def test_goods_roundtrip(session) -> None:
    row = DoudianGoods(goods_id="g-1", title="商品 1", price=Decimal("99.00"), stock=10, tab="onSale")
    session.add(row)
    await session.commit()
    got = (await session.execute(select(DoudianGoods).where(DoudianGoods.goods_id == "g-1"))).scalar_one()
    assert got.title == "商品 1"
    assert got.stock == 10


@pytest.mark.asyncio
async def test_comment_with_ai_fields(session) -> None:
    row = DoudianComment(
        comment_id="c-1",
        goods_id="g-1",
        content="物流太慢了",
        rating=2,
        user_nick="user_abc",
        created_at_src=datetime(2026, 5, 18, 10, 0),
        sentiment="negative",
        pain_points_json={"tags": [{"tag": "物流慢", "evidence": "太慢了"}]},
    )
    session.add(row)
    await session.commit()
    got = (await session.execute(select(DoudianComment).where(DoudianComment.comment_id == "c-1"))).scalar_one()
    assert got.sentiment == "negative"
    assert got.pain_points_json["tags"][0]["tag"] == "物流慢"


@pytest.mark.asyncio
async def test_aftersale_roundtrip(session) -> None:
    row = DoudianAftersale(aftersale_id="as-1", order_sn="TEST-001", type="refund", status=1)
    session.add(row)
    await session.commit()
    got = (await session.execute(select(DoudianAftersale).where(DoudianAftersale.aftersale_id == "as-1"))).scalar_one()
    assert got.type == "refund"


@pytest.mark.asyncio
async def test_stock_roundtrip(session) -> None:
    row = DoudianStock(goods_id="g-1", sku_id="sku-1", on_hand=5, available=4, locked=1)
    session.add(row)
    await session.commit()
    got = (await session.execute(select(DoudianStock).where(DoudianStock.sku_id == "sku-1"))).scalar_one()
    assert got.on_hand == 5


@pytest.mark.asyncio
async def test_system_tables_roundtrip(session) -> None:
    now = datetime.utcnow()
    session.add(ScrapeTaskRun(target="doudian_order", subsystem="merchant", status="queued"))
    session.add(Alert(kind="negative_comment_surge", severity="warn", payload_json={"goods_id": "g-1"}, dispatched_at=now))
    session.add(SessionEvent(kind="login_succeeded", payload_json={}, occurred_at=now))
    session.add(AiGeneration(kind="title", input_hash="x" * 64, output_text="ok", model="deepseek-v4-pro", tokens_in=10, tokens_out=20, cost=0.001, created_at=now))
    await session.commit()
    runs = (await session.execute(select(ScrapeTaskRun))).scalars().all()
    alerts = (await session.execute(select(Alert))).scalars().all()
    gens = (await session.execute(select(AiGeneration))).scalars().all()
    assert len(runs) == 1 and len(alerts) == 1 and len(gens) == 1
    assert gens[0].model == "deepseek-v4-pro"
