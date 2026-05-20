"""Response-interceptor scrape engine.

For each target:
1. Open a fresh page in the persistent context.
2. Register page.on("response") handler filtered by spec.intercept.url_contains + method.
3. Perform pre_actions (clicks/fills) if any.
4. Navigate to spec.nav.url with the configured wait_until.
5. Wait spec.nav.settle_ms.
6. Run jsonpath extraction over each captured response payload.
7. Upsert into spec.sink.table with optional raw_json.
8. Persist scrape_task_run lifecycle, broadcast on /ws/tasks.
"""
import asyncio
import json
from datetime import datetime
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse
from playwright.async_api import BrowserContext, Page, Response
from sqlalchemy import text

from dystore.auth.expiry_detector import SessionExpired, check_after_navigation
from dystore.core.logging import get_logger
from dystore.db.models import ScrapeTaskRun
from dystore.db.session import SessionLocal
from dystore.scraper.antidetect import assert_not_quiet_hours_for_merchant, get_lock, human_delay
from dystore.scraper.schema import ScrapeSpec
from dystore.scraper.telemetry_filter import is_telemetry
from dystore.ws.broker import publish

log = get_logger(__name__)


async def run_target(
    spec: ScrapeSpec, ctx: BrowserContext, *, account: str = "default"
) -> dict[str, Any]:
    assert_not_quiet_hours_for_merchant(spec.subsystem)
    lock = get_lock(account, spec.nav.url)

    async with lock:
        return await _run_inner(spec, ctx)


async def _run_inner(spec: ScrapeSpec, ctx: BrowserContext) -> dict[str, Any]:
    started_at = datetime.utcnow()
    run = await _persist_run(spec, started_at)
    await _broadcast_task("task_started", run.id, spec.target)

    captured: list[dict] = []
    _auth_failure: dict[str, Any] = {"hit": False, "msg": ""}

    async def on_response(resp: Response) -> None:
        try:
            if is_telemetry(resp.url):
                return
            if spec.intercept.url_contains not in resp.url:
                return
            if resp.request.method != spec.intercept.method:
                return
            # Use body() + json.loads — more resilient against navigation interruption than resp.json()
            try:
                raw = await resp.body()
            except Exception as e:
                log.warning("scraper.body_unavailable", target=spec.target, url=resp.url[:120], err=str(e))
                return
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                return
            # Doudian auth-failure envelope: {"code":"10008","msg":"登录信息已失效..."} or similar
            code = body.get("code") if isinstance(body, dict) else None
            msg = (body.get("msg") if isinstance(body, dict) else "") or ""
            if str(code) in {"10008", "10009", "401", "403"} or "登录" in msg or "重新登录" in msg or "未登录" in msg:
                log.warning("scraper.auth_envelope_detected", target=spec.target, code=code, msg=msg[:80])
                _auth_failure["hit"] = True
                _auth_failure["msg"] = f"{code}: {msg}"[:300]
                return
            captured.append(body)
            log.info("scraper.captured", target=spec.target, url_tail=resp.url[-80:])
        except Exception as e:
            log.warning("scraper.interceptor_error", target=spec.target, error=str(e))

    page: Page = await ctx.new_page()
    page.on("response", on_response)
    try:
        for pre in spec.pre_actions:
            await _apply_pre_action(page, pre)
            await human_delay()

        try:
            await page.goto(spec.nav.url, wait_until=spec.nav.wait_until, timeout=60_000)
        except Exception as e:
            # Many fxg pages keep firing background XHRs forever; networkidle never settles.
            # Fall back to domcontentloaded — by then the redirect to /login is already final.
            if "wait_until" in str(e) or "networkidle" in str(e) or "Timeout" in str(e):
                log.info("scraper.networkidle_fallback", target=spec.target)
                await page.goto(spec.nav.url, wait_until="domcontentloaded", timeout=30_000)
            else:
                raise
        await check_after_navigation(page)
        if "/login/common" in page.url:
            raise SessionExpired(page.url)
        await page.wait_for_timeout(spec.nav.settle_ms)
        # Re-check after settle — session validation often runs deferred and redirects late
        if "/login/common" in page.url:
            log.warning("scraper.late_login_redirect", target=spec.target, captured=len(captured))
            raise SessionExpired(page.url)
        if _auth_failure["hit"]:
            raise SessionExpired(_auth_failure["msg"])
        items = list(_extract_items(captured, spec))
        await _upsert_items(items, spec, raw_payloads=captured)
        # Diagnostic: when responses captured but no items extracted, dump first payload
        # so operator can fix jsonpath/transforms without re-scraping.
        diagnostic: str | None = None
        if captured and not items:
            sample = json.dumps(captured[0], ensure_ascii=False)[:1800]
            diagnostic = f"captured={len(captured)} | no items extracted | first payload (truncated): {sample}"
        elif not captured:
            diagnostic = "no response captured matching intercept rule (page may not have triggered the XHR)"
        await _finish_run(run.id, "done", len(items), error=diagnostic)
        await _broadcast_task("task_done", run.id, spec.target, items=len(items))
        log.info("scraper.target_done", target=spec.target, items=len(items), captured=len(captured))
        return {"target": spec.target, "items": len(items), "captured_responses": len(captured)}

    except SessionExpired as e:
        await _finish_run(run.id, "auth_expired", 0, error=str(e))
        await _broadcast_task("task_failed", run.id, spec.target, error="auth_expired")
        # Do not re-raise — the run row is already recorded as auth_expired; re-raising would cause
        # the caller (scrape.py / scheduler) to record a duplicate "failed" row.
        return {"target": spec.target, "items": 0, "status": "auth_expired"}
    except Exception as e:
        await _finish_run(run.id, "failed", 0, error=f"{type(e).__name__}: {e}"[:2000])
        await _broadcast_task("task_failed", run.id, spec.target, error=str(e))
        log.exception("scraper.target_failed", target=spec.target)
        # Do not re-raise — engine owns the lifecycle row; raising would cause caller to record dup.
        return {"target": spec.target, "items": 0, "status": "failed", "error": str(e)}
    finally:
        await page.close()


def _apply_transform(name: str, value: Any) -> Any:
    if value is None:
        return None
    try:
        if name == "unix_to_datetime":
            return datetime.fromtimestamp(int(value))
        if name == "unix_ms_to_datetime":
            return datetime.fromtimestamp(int(value) / 1000)
        if name == "cents_to_yuan":
            return float(value) / 100.0
        if name == "to_str":
            return str(value)
        if name == "mmdd_to_date":
            # Doudian chart axes use "MM/DD" relative to today's year.
            month, day = str(value).split("/")
            return datetime(datetime.utcnow().year, int(month), int(day)).date()
        if name == "today_date":
            # Anchor a row to the day it was scraped (input value is ignored).
            return datetime.utcnow().date()
        if name == "pct_to_float":
            # "99.26%" → 99.26
            s = str(value).strip().rstrip("%")
            return float(s)
    except Exception:
        return None
    return value


def _extract_items(captured: list[dict], spec: ScrapeSpec):
    # raw_only short-circuit: one row per payload, only raw_json populated downstream.
    if spec.sink.raw_only:
        for payload in captured:
            yield {}, payload
        return
    list_expr = jsonpath_parse(spec.extract.jsonpath)
    field_exprs = {k: jsonpath_parse(v) for k, v in spec.extract.fields.items()}
    transforms = spec.extract.transforms or {}
    static_fields = spec.extract.static_fields or {}
    iterate_object = spec.extract.iterate_object
    key_field = spec.extract.iterate_key_field
    value_field = spec.extract.iterate_value_field
    for payload in captured:
        matches = [m.value for m in list_expr.find(payload)]
        for item in matches:
            # Flat-dict iteration mode: emit one row per (key, value) pair.
            # Skip nested dicts/lists and None — not safe for scalar columns / can violate NOT NULL.
            if iterate_object and isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, (dict, list)) or v is None:
                        continue
                    row = {key_field: str(k), value_field: v}
                    if value_field in transforms:
                        row[value_field] = _apply_transform(transforms[value_field], row[value_field])
                    for sk, sv in static_fields.items():
                        row[sk] = _apply_transform(transforms[sk], sv) if sk in transforms else sv
                    yield row, payload
                continue
            row: dict[str, Any] = {}
            for col, expr in field_exprs.items():
                vals = [m.value for m in expr.find(item)]
                v = vals[0] if vals else None
                if col in transforms:
                    v = _apply_transform(transforms[col], v)
                row[col] = v
            for sk, sv in static_fields.items():
                row[sk] = _apply_transform(transforms[sk], sv) if sk in transforms else sv
            yield row, payload


async def _upsert_items(items, spec: ScrapeSpec, *, raw_payloads: list[dict]) -> None:
    if not items:
        return
    cols = list(next(iter([row for row, _ in items[:1]]), {}).keys()) if items else []
    # raw_only mode (or any sink with store_raw) needs the raw_json column.
    if (spec.sink.store_raw or spec.sink.raw_only) and "raw_json" not in cols:
        cols.append("raw_json")
    if not cols:
        return

    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    if spec.sink.upsert_key:
        update_clause = ", ".join(f"{c}=VALUES({c})" for c in cols if c != spec.sink.upsert_key)
        sql = text(
            f"INSERT INTO {spec.sink.table} ({col_list}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )
    else:
        sql = text(f"INSERT INTO {spec.sink.table} ({col_list}) VALUES ({placeholders})")

    async with SessionLocal() as session:
        for row, raw in items:
            if spec.sink.store_raw or spec.sink.raw_only:
                row["raw_json"] = json.dumps(raw, ensure_ascii=False)
            # Backfill any column the row is missing (e.g. when items mix shapes)
            # so the prepared statement has a value for every named bind.
            for c in cols:
                row.setdefault(c, None)
            # SQLAlchemy can't bind raw Python dict/list to non-JSON columns; serialise.
            for k, v in list(row.items()):
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v, ensure_ascii=False)
            await session.execute(sql, row)
        await session.commit()


async def _apply_pre_action(page: Page, pre) -> None:
    if pre.action == "click" and pre.selector:
        await page.click(pre.selector, timeout=pre.timeout_ms)
    elif pre.action == "fill" and pre.selector:
        await page.fill(pre.selector, str(pre.value or ""), timeout=pre.timeout_ms)
    elif pre.action == "select" and pre.selector:
        await page.select_option(pre.selector, value=str(pre.value or ""), timeout=pre.timeout_ms)
    elif pre.action == "wait_for" and pre.selector:
        await page.wait_for_selector(pre.selector, timeout=pre.timeout_ms)
    elif pre.action == "scroll":
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(0.5)


async def _persist_run(spec: ScrapeSpec, started_at: datetime) -> ScrapeTaskRun:
    async with SessionLocal() as session:
        run = ScrapeTaskRun(
            target=spec.target,
            subsystem=spec.subsystem,
            started_at=started_at,
            status="running",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run


async def _finish_run(run_id: int, status: str, items_count: int, *, error: str | None = None) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                "UPDATE scrape_task_run "
                "SET status=:s, finished_at=:f, items_count=:c, error_msg=:e "
                "WHERE id=:id"
            ),
            {"s": status, "f": datetime.utcnow(), "c": items_count, "e": error, "id": run_id},
        )
        await session.commit()


async def _broadcast_task(kind: str, run_id: int, target: str, **extra) -> None:
    await publish("tasks", {"kind": kind, "run_id": run_id, "target": target, **extra})
