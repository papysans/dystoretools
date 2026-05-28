from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import PeerGoods, PeerLivestream, PeerShop
from dystore.db.session import SessionLocal, get_session
from dystore.scraper.public.datasource import get_datasource

router = APIRouter(prefix="/api/v1/peer", tags=["peer"])


class WatchRequest(BaseModel):
    shop_id: str
    shop_name: str | None = None


@router.post("/watch")
async def watch(req: WatchRequest) -> dict:
    async with SessionLocal() as s:
        existing = (await s.execute(select(PeerShop).where(PeerShop.shop_id == req.shop_id))).scalar_one_or_none()
        if existing:
            return {"id": existing.id, "shop_id": existing.shop_id, "existed": True}
        row = PeerShop(shop_id=req.shop_id, shop_name=req.shop_name)
        s.add(row)
        await s.commit()
        await s.refresh(row)
    return {"id": row.id, "shop_id": row.shop_id, "existed": False}


@router.get("/list")
async def list_peers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(PeerShop).order_by(desc(PeerShop.id)))).scalars().all()
    return [{"id": r.id, "shop_id": r.shop_id, "shop_name": r.shop_name, "follower_count": r.follower_count} for r in rows]


@router.get("/{shop_id}/goods")
async def peer_goods(shop_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(PeerGoods).where(PeerGoods.peer_shop_id == shop_id).order_by(desc(PeerGoods.id)).limit(100))).scalars().all()
    return [{"goods_id": r.goods_id, "title": r.title, "peer_price": float(r.peer_price) if r.peer_price else None, "hot_sale": r.hot_sale} for r in rows]


@router.post("/{shop_id}/refresh")
async def refresh_peer(shop_id: str) -> dict:
    """Trigger a one-off fetch via the configured DataSource. Stub returns immediately."""
    ds = get_datasource()
    info = await ds.fetch_peer_shop(shop_id)
    return {"shop_id": shop_id, "fetched": info}


@router.post("/run-all")
async def run_all_peers() -> dict:
    """Manually trigger the scheduled peer-scrape pass over all configured shop ids."""
    from dystore.scraper.public.service import run_peer_scrape
    result = await run_peer_scrape()
    return {"status": "done", **result}
