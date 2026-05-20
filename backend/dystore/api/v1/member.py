from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import (
    MemberDashboardAgg,
    MemberDashboardDay,
    MemberDashboardHist,
)
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/member", tags=["member"])


def _extract_agg_items(raw_json: dict | None) -> list[dict]:
    if not isinstance(raw_json, dict):
        return []
    data = raw_json.get("data")
    if not isinstance(data, dict):
        return []
    data_head = data.get("data_head")
    if not isinstance(data_head, list):
        return []
    items: list[dict] = []
    for entry in data_head:
        try:
            value_block = entry["value"]
            unit = value_block["unit"]
            raw_value = value_block["value"]
            if unit == "price":
                value = raw_value / 100
            else:
                value = raw_value
            change_value = entry.get("change_value") or {}
            peer_excellent = entry.get("peer_excellent") or {}
            items.append(
                {
                    "index_name": entry["index_name"],
                    "index_display": entry["index_display"],
                    "value": value,
                    "unit": unit,
                    "change_value": change_value.get("value")
                    if isinstance(change_value, dict)
                    else None,
                    "peer_excellent": peer_excellent.get("value")
                    if isinstance(peer_excellent, dict)
                    else None,
                }
            )
        except (KeyError, TypeError):
            continue
    return items


@router.get("/dashboard")
async def member_dashboard(
    session: AsyncSession = Depends(get_session),
) -> dict:
    # --- agg: latest member_dashboard_agg.raw_json.data.data_head ---
    latest_agg = (
        await session.execute(
            select(MemberDashboardAgg)
            .order_by(MemberDashboardAgg.scraped_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    agg_items = _extract_agg_items(latest_agg.raw_json) if latest_agg else []

    # --- daily: last 30 dates ascending ---
    day_rows = (
        await session.execute(
            select(MemberDashboardDay)
            .order_by(MemberDashboardDay.date.asc())
            .limit(30)
        )
    ).scalars().all()
    daily_items = [
        {
            "date": row.date.isoformat() if row.date else None,
            "metric": row.metric,
            "value": float(row.value) if row.value is not None else None,
        }
        for row in day_rows
    ]

    # --- hist: latest snapshot, deduplicated by (bucket, value, dim) ---
    latest_hist_scraped_at = (
        await session.execute(select(func.max(MemberDashboardHist.scraped_at)))
    ).scalar_one()
    hist_items: list[dict] = []
    if latest_hist_scraped_at is not None:
        hist_rows = (
            await session.execute(
                select(MemberDashboardHist)
                .where(MemberDashboardHist.scraped_at == latest_hist_scraped_at)
                .order_by(MemberDashboardHist.id.asc())
            )
        ).scalars().all()
        seen: set[tuple] = set()
        for row in hist_rows:
            key = (row.bucket, row.value, row.dim)
            if key in seen:
                continue
            seen.add(key)
            hist_items.append(
                {
                    "bucket": row.bucket,
                    "value": float(row.value) if row.value is not None else None,
                    "dim": row.dim,
                }
            )

    return {"agg": agg_items, "daily": daily_items, "hist": hist_items}
