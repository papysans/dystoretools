> **Parallelism notation**
>
> - `[parallel]` sections contain independent lanes (A/B/C/...) that touch disjoint files. Dispatch one subagent per lane.
> - `[serial]` sections must complete in order.
> - All 4 lanes in section 2 can run concurrently. Section 1 is a single-file env edit (1 task), section 3 ties everything together.

## 1. Config `[serial]`

- [x] 1.1 Add `LLM_DAILY_BUDGET_YUAN=5` to `.env.example`. Document in the same line: `# daily cap on comment-annotation LLM spend (CNY); worker exits early once exceeded`.

## 2. Backend wiring `[parallel]` — 4 lanes, one subagent each

### Lane A — Worker spend guard + summary
- [x] 2.A.1 Edit `backend/dystore/analysis/comment_worker.py`: at the top of `annotate_pending`, query today's spend from `ai_generation` (`SELECT COALESCE(SUM(cost_yuan), 0) FROM ai_generation WHERE DATE(created_at) = CURDATE()`).
- [x] 2.A.2 If spend >= `os.getenv("LLM_DAILY_BUDGET_YUAN", "5")` cast to float, return `{"ok": 0, "failed": 0, "total": 0, "skipped": "budget_exhausted", "spend_yuan": spend}` immediately.
- [x] 2.A.3 Within the iteration loop, re-check spend every N iterations (N=10). If exceeded mid-batch, break the loop, commit pending writes, return `{"ok": ok, "failed": failed, "total": done_so_far, "skipped": "budget_exhausted", "spend_yuan": spend}`.
- [x] 2.A.4 After the loop, add `negative_new` count (number of rows newly classified as `sentiment="negative"` in this run) to the return dict.
- [x] 2.A.5 When `total == 0` (no NULL rows), return `{"ok": 0, "failed": 0, "total": 0, "skipped": "no_pending"}`.

### Lane B — Scheduler post-scrape hook
- [x] 2.B.1 Edit `backend/dystore/scheduler/scheduler.py`. After the `for spec in merchant_targets` loop completes successfully, check whether any spec.target was in `{"doudian_comment_list", "doudian_comment_negative"}`. If yes, `await annotate_pending(batch_size=50)` and log the summary.
- [x] 2.B.2 In the same `_dispatch_window`, add an unconditional `if label == "2130": await annotate_pending(batch_size=200)` block after the comment-hook block. Log summary.
- [x] 2.B.3 Import `annotate_pending` at module top.
- [x] 2.B.4 Add a try/except around each annotate call so a worker failure does NOT mark the window as failed — log `log.exception("scheduler.annotate_failed", label=label)` and continue.

### Lane C — Admin API endpoint
- [x] 2.C.1 Create `backend/dystore/api/v1/scrape_annotate.py` with `router = APIRouter(prefix="/api/v1/scrape", tags=["scrape"])` and `POST /annotate-now` calling `await annotate_pending(batch_size=200)`, returning its summary as JSON.
- [x] 2.C.2 Register the router in `dystore/main.py` (or `api/v1/__init__.py`, matching the existing pattern for `scrape.py`).
- [x] 2.C.3 Add a single OpenAPI `description`/`summary` describing the endpoint as "trigger comment annotation backfill on demand".

### Lane D — Alert hook on negative classification
- [x] 2.D.1 In `comment_worker.annotate_pending`, after the loop, if `negative_new >= 1`, call a small helper (new function in `dystore/alerts/`) to check the surge rule and emit `/ws/alerts` if threshold is met.
- [x] 2.D.2 If the alerts module doesn't already have a "feed me comment classifications" API, add a thin entry point `process_negative_classifications(comment_ids: list[str])` that the worker invokes; the alert engine's existing surge rule consumes from there.
- [x] 2.D.3 Confirm the existing `negative_comment_surge` alert type / threshold is unchanged; this lane only wires the producer.

## 3. Tests `[parallel]` — independent of section 2 lanes

> Each test file is independent. Mocked LLM, mocked DB session. These can run in parallel with section 2 (since they only assert structure) but must finish before section 4.

### Lane A — Worker tests
- [x] 3.A.1 Create `backend/tests/analysis/test_comment_worker_budget.py`. Test: when `SUM(cost_yuan)` returns >= budget, `annotate_pending` returns the budget-exhausted summary without making any LLM call (assert via mock that `complete()` was not called).
- [x] 3.A.2 Test: when there are 0 NULL rows, returns `{ok:0, failed:0, total:0, skipped:"no_pending"}`.
- [x] 3.A.3 Test: structured-summary contract — keys `ok`, `failed`, `total` always present.

### Lane B — Scheduler hook test
- [x] 3.B.1 Create `backend/tests/scheduler/test_post_scrape_annotate.py`. With a mocked `run_target` and mocked `annotate_pending`, assert that after a successful comment-class scrape `annotate_pending` was awaited exactly once.
- [x] 3.B.2 Test: a non-comment target (e.g., `doudian_order`) does NOT trigger annotation.
- [x] 3.B.3 Test: when entering the `2130` label, annotation is invoked even if no comment scrape ran in this window.

### Lane C — API endpoint test
- [x] 3.C.1 Create `backend/tests/api/test_scrape_annotate.py`. With mocked `annotate_pending`, POST `/api/v1/scrape/annotate-now` returns the summary as JSON, HTTP 200.
- [x] 3.C.2 Test: when worker returns `skipped: "budget_exhausted"`, response is HTTP 200 (not error) and body carries the skipped reason.

## 4. End-to-end smoke `[serial]`

- [x] 4.1 Set `LLM_DAILY_BUDGET_YUAN=5` in `.env`. Restart api container (`docker compose restart api`).
- [x] 4.2 `curl -X POST http://127.0.0.1:8080/api/v1/scrape/annotate-now` — expect a JSON summary with non-zero `ok` (since DB has 22 NULL rows).
- [x] 4.3 `docker compose exec mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -D"$MYSQL_DATABASE" -N -e "SELECT sentiment, COUNT(*) FROM doudian_comment GROUP BY sentiment"'` — expect sentiment distribution now includes `positive`/`neutral`/`negative` counts; `NULL` count down to 0 or only newly-arrived.
- [x] 4.4 Browser-test `/comments` at `http://127.0.0.1:5173` — confirm sentiment column shows real labels (not all "中性"), pain points column shows tags for any comments that have them.
- [x] 4.5 Wait for next scheduler 21:30 window OR simulate via `docker compose exec api python -c "import asyncio; from dystore.scheduler.scheduler import _dispatch_window; asyncio.run(_dispatch_window('2130'))"`. Assert logs show `scheduler.annotate_done`.
- [x] 4.6 Run `cd backend && pytest -q backend/tests/{analysis,scheduler,api}/test_*annotate*.py backend/tests/api/test_scrape_annotate.py` — all green.
- [x] 4.7 Run `openspec validate wire-comment-ai-analysis --strict` to ensure all artifacts pass schema check before archive.
