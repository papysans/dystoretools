"""千川数据报表拉取 → qianchuan_report 入库（按唯一键去重 upsert）.

路径/参数/字段均经真机校准（2026-05-30 真实 API code=0 验证）：
- 路径 v1.0/qianchuan/report/advertiser/get/（非 v3.0）
- filtering.marketing_goal 必填，分 VIDEO_PROM_GOODS(短视频带货) / LIVE_PROM_GOODS(直播带货)
- 返回 data.list[] 为扁平 dict，日期字段是 time_item，指标直接挂行上（无嵌套 metrics/dimensions）
- object_id 存 marketing_goal，使短视频/直播两类日数据不互相覆盖
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text

from dystore.core.logging import get_logger
from dystore.db.session import SessionLocal
from dystore.oceanengine.client import get_api
from dystore.oceanengine.oauth import get_valid_access_token

log = get_logger(__name__)

_MARKETING_GOALS = ("VIDEO_PROM_GOODS", "LIVE_PROM_GOODS")

_FIELDS = [
    "stat_cost",
    "show_cnt",
    "click_cnt",
    "convert_cnt",
    "convert_cost",
    "ctr",
    "pay_order_count",
    "pay_order_amount",
    "prepay_and_pay_order_roi",
]

_UPSERT = text(
    "INSERT INTO qianchuan_report "
    "(advertiser_id, stat_date, level, object_id, cost, show_cnt, click_cnt, convert_cnt, "
    " convert_cost, ctr, pay_order_amount, roi, raw_json, scraped_at) "
    "VALUES (:advertiser_id, :stat_date, :level, :object_id, :cost, :show_cnt, :click_cnt, :convert_cnt, "
    " :convert_cost, :ctr, :pay_order_amount, :roi, :raw_json, NOW()) "
    "ON DUPLICATE KEY UPDATE cost=VALUES(cost), show_cnt=VALUES(show_cnt), click_cnt=VALUES(click_cnt), "
    " convert_cnt=VALUES(convert_cnt), convert_cost=VALUES(convert_cost), ctr=VALUES(ctr), "
    " pay_order_amount=VALUES(pay_order_amount), roi=VALUES(roi), raw_json=VALUES(raw_json), scraped_at=NOW()"
)


async def fetch_advertiser_report(advertiser_id: str, start: date, end: date) -> int:
    """拉取单账户 [start,end] 按天账户级报表（短视频+直播两类目标）并入库，返回入库行数。"""
    access = await get_valid_access_token()
    total = 0
    for goal in _MARKETING_GOALS:
        data = await get_api(
            "v1.0/qianchuan/report/advertiser/get/",
            access_token=access,
            params={
                "advertiser_id": advertiser_id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "fields": json.dumps(_FIELDS),
                "group_by": json.dumps(["STAT_GROUP_BY_TIME"]),
                "filtering": json.dumps({"marketing_goal": goal}),
                "page": 1,
                "page_size": 100,
            },
        )
        total += await _ingest(advertiser_id, goal, (data or {}).get("list") or [])
    log.info("qianchuan.report_ingested", advertiser_id=advertiser_id, rows=total)
    return total


async def _ingest(advertiser_id: str, goal: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    n = 0
    async with SessionLocal() as s:
        for r in rows:
            # 真机确认：行为扁平 dict，日期字段 time_item，指标直接挂行上
            stat_time = r.get("time_item") or r.get("stat_time_day") or ""
            await s.execute(
                _UPSERT,
                {
                    "advertiser_id": advertiser_id,
                    "stat_date": str(stat_time)[:10],
                    "level": "advertiser",
                    "object_id": goal,  # 区分短视频/直播，避免 upsert 互相覆盖
                    "cost": _num(r.get("stat_cost")),
                    "show_cnt": _int(r.get("show_cnt")),
                    "click_cnt": _int(r.get("click_cnt")),
                    "convert_cnt": _int(r.get("convert_cnt")),
                    "convert_cost": _num(r.get("convert_cost")),
                    "ctr": _num(r.get("ctr")),
                    "pay_order_amount": _num(r.get("pay_order_amount")),
                    "roi": _num(r.get("prepay_and_pay_order_roi")),
                    "raw_json": json.dumps(r, ensure_ascii=False),
                },
            )
            n += 1
        await s.commit()
    return n


def _num(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _int(v) -> int | None:
    try:
        return int(float(v)) if v is not None else None
    except (TypeError, ValueError):
        return None
