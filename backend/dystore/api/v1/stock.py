from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import DoudianGoods, DoudianStock
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


def _derive_level(on_hand: int | None) -> str:
    n = on_hand or 0
    if n <= 0:
        return "out"
    if n < 5:
        return "low"
    if n > 200:
        return "over"
    return "normal"


def _extract_skus(raw_json: dict | None, goods_id: str) -> list[dict]:
    if not raw_json:
        return []
    data = raw_json.get("data")
    if not isinstance(data, list):
        return []
    for product in data:
        if not isinstance(product, dict):
            continue
        if str(product.get("product_id")) != str(goods_id):
            continue
        skus = product.get("skus") or []
        result = []
        for sku in skus:
            if not isinstance(sku, dict):
                continue
            result.append({
                "sku_id": sku.get("sku_id") or sku.get("id"),
                "sku_name": sku.get("sku_name") or sku.get("name"),
                "stock_num": sku.get("stock_num") or sku.get("stock") or sku.get("on_hand"),
                **{k: v for k, v in sku.items() if k not in {"sku_id", "id", "sku_name", "name", "stock_num", "stock", "on_hand"}},
            })
        return result
    return []


@router.get("")
async def list_stock(
    page: int = 0,
    page_size: int = Query(50, le=200),
    include: str | None = None,
    goods_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Latest stock row per goods_id by MAX(scraped_at)
    latest_sq = (
        select(DoudianStock.goods_id, func.max(DoudianStock.scraped_at).label("max_ts"))
        .group_by(DoudianStock.goods_id)
        .subquery()
    )
    join_clause = (DoudianStock.goods_id == latest_sq.c.goods_id) & (
        DoudianStock.scraped_at == latest_sq.c.max_ts
    )
    total_q = (
        select(func.count(DoudianStock.id))
        .join(latest_sq, join_clause)
    )
    if goods_id is not None:
        total_q = total_q.where(DoudianStock.goods_id == goods_id)
    total = (await session.execute(total_q)).scalar_one()
    q = (
        select(DoudianStock, DoudianGoods.title)
        .join(latest_sq, join_clause)
        .outerjoin(DoudianGoods, DoudianGoods.goods_id == DoudianStock.goods_id)
    )
    if goods_id is not None:
        q = q.where(DoudianStock.goods_id == goods_id)
    q = q.order_by(DoudianStock.goods_id).offset(page * page_size).limit(page_size)
    rows = (await session.execute(q)).all()
    include_skus = bool(include) and "skus" in include.lower()
    items: list[dict] = []
    for stock, title in rows:
        item = {
            "goods_id": stock.goods_id,
            "title": title,
            "on_hand": stock.on_hand,
            "available": stock.available,
            "locked": stock.locked,
            "level": _derive_level(stock.on_hand),
            "scraped_at": stock.scraped_at.isoformat() if stock.scraped_at else None,
        }
        if include_skus:
            item["skus"] = _extract_skus(stock.raw_json, stock.goods_id)
        items.append(item)
    return {"total": int(total), "items": items}


@router.get("/levels")
async def stock_levels(session: AsyncSession = Depends(get_session)) -> dict:
    latest_sq = (
        select(DoudianStock.goods_id, func.max(DoudianStock.scraped_at).label("max_ts"))
        .group_by(DoudianStock.goods_id)
        .subquery()
    )
    q = select(DoudianStock.on_hand).join(
        latest_sq,
        (DoudianStock.goods_id == latest_sq.c.goods_id)
        & (DoudianStock.scraped_at == latest_sq.c.max_ts),
    )
    counts = {"out": 0, "low": 0, "normal": 0, "over": 0}
    for (on_hand,) in (await session.execute(q)).all():
        counts[_derive_level(on_hand)] += 1
    return counts
