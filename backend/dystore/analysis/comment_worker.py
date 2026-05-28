"""AI worker that fills sentiment + pain_points_json on doudian_comment rows.

Differentiation from platform GPT-reply: we do *classification + tag extraction*
across many comments, not single-comment reply generation.
"""
import json
import os
from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy import select as sa_select

from dystore.core.logging import get_logger
from dystore.db.models import AiGeneration, DoudianComment
from dystore.db.session import SessionLocal
from dystore.llm.gateway import complete
from dystore.llm.pii_scrub import Scrubber

log = get_logger(__name__)

PROMPT_TEMPLATE = """你是抖店评论分析助手。对下列商品评论给出 JSON 输出：

{{
  "sentiment": "positive" | "neutral" | "negative",
  "pain_points": [
    {{"tag": "<短语，最多 6 字>", "evidence": "<原文片段>"}}
  ]
}}

仅当评论明确表达不满才填 pain_points，否则返回空数组。tag 用中文，统一化（如"物流慢"而非"快递太慢"）。

评论：
{content}
"""


async def annotate_comment(comment_id: str) -> dict | None:
    async with SessionLocal() as s:
        row = (await s.execute(select(DoudianComment).where(DoudianComment.comment_id == comment_id))).scalar_one_or_none()
        if row is None:
            return None
        if row.sentiment is not None:
            return {"comment_id": comment_id, "skipped": "already_annotated"}
        content = row.content or ""
        user_nick = row.user_nick

    scrub = Scrubber()
    scrubbed = scrub.scrub(content, nicks=[user_nick] if user_nick else [])
    prompt = PROMPT_TEMPLATE.format(content=scrubbed)

    try:
        result = await complete(prompt, kind="comment_sentiment", max_tokens=512)
    except Exception as e:
        log.warning("analysis.llm_failed", comment_id=comment_id, error=str(e))
        return {"comment_id": comment_id, "error": str(e)}

    text = result["text"].strip()
    try:
        parsed = json.loads(_extract_json(text))
    except Exception as e:
        log.warning("analysis.parse_failed", comment_id=comment_id, raw=text[:200], error=str(e))
        return {"comment_id": comment_id, "error": "parse_failed"}

    sentiment = parsed.get("sentiment") or "neutral"
    pain_points = {"tags": parsed.get("pain_points", [])}

    async with SessionLocal() as s:
        await s.execute(
            update(DoudianComment)
            .where(DoudianComment.comment_id == comment_id)
            .values(sentiment=sentiment, pain_points_json=pain_points)
        )
        await s.commit()
    return {"comment_id": comment_id, "sentiment": sentiment, "tags": len(pain_points["tags"])}


def _extract_json(text: str) -> str:
    """Heuristically pull a JSON object out of a model reply that may wrap it in markdown."""
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                return p
    return text


async def _today_spend_yuan() -> float:
    # why: sum today's LLM cost rows (column is `cost`, not `cost_yuan`)
    async with SessionLocal() as s:
        spend = (await s.execute(
            sa_select(func.coalesce(func.sum(AiGeneration.cost), 0.0))
            .where(func.date(AiGeneration.created_at) == date.today())
        )).scalar_one() or 0.0
    return float(spend)


async def annotate_pending(batch_size: int = 50) -> dict:
    budget = float(os.getenv("LLM_DAILY_BUDGET_YUAN", "5"))
    spend = await _today_spend_yuan()
    if spend >= budget:
        return {"ok": 0, "failed": 0, "total": 0, "skipped": "budget_exhausted", "spend_yuan": spend}

    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(DoudianComment.comment_id).where(DoudianComment.sentiment.is_(None)).limit(batch_size)
            )
        ).scalars().all()

    if len(rows) == 0:
        return {"ok": 0, "failed": 0, "total": 0, "skipped": "no_pending"}

    ok, failed, negative_new = 0, 0, 0
    for idx, cid in enumerate(rows):
        # why: re-check budget every 10 comments since cost accrues per LLM call
        if idx > 0 and idx % 10 == 0:
            spend = await _today_spend_yuan()
            if spend >= budget:
                log.warning("analysis.batch_budget_exhausted_midway", processed=ok + failed, spend_yuan=spend)
                return {
                    "ok": ok,
                    "failed": failed,
                    "total": ok + failed,
                    "skipped": "budget_exhausted",
                    "spend_yuan": spend,
                }
        r = await annotate_comment(cid)
        if r and "error" in r:
            failed += 1
        else:
            ok += 1
            if r and r.get("sentiment") == "negative":
                negative_new += 1

    total = ok + failed
    log.info("analysis.batch_done", ok=ok, failed=failed, total=total, negative_new=negative_new)

    if negative_new >= 1:
        try:
            from dystore.alerts.rules import run_negative_comment_surge
            await run_negative_comment_surge()
        except Exception as e:
            log.warning("analysis.alert_check_failed", error=str(e))

    return {"ok": ok, "failed": failed, "total": total, "negative_new": negative_new}
