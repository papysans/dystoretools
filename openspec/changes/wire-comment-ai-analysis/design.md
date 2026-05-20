## Context

The bootstrap change shipped `analysis/comment_worker.annotate_pending()` with a complete prompt, JSON-extraction heuristic, PII scrubber, gateway call, and DB update. The function works in isolation (unit-tested at write time). The scheduler — which is the only place that knows when a comment scrape just finished — never imports it. Result: 22/28 production rows have `sentiment IS NULL`, and the Comments page renders the AI promise as decorative text.

The fix is one-directional wire-up plus three small safety bolts:
1. Trigger automation
2. Daily catch-up safety net
3. Spend cap

Everything else — the worker logic, the model choice, the gateway, the table schema — is unchanged.

## Goals / Non-Goals

**Goals:**
- Move the comment AI pipeline from "exists in code" to "runs every day, no operator action required".
- Keep cost predictable and observably small (we report spend back, not just count).
- Make backfills cheap to trigger when the operator wants to refresh, without spinning up a custom script.

**Non-Goals:**
- No prompt-engineering tweaks. The current prompt is V1's contract; changing it belongs in a separate evaluation-driven change.
- No batching semantics change. `batch_size=50` per scrape, 200 in catch-up — picked to bound wall-clock latency, not optimized further.
- No new analysis features. Pain-point clustering across products, longitudinal trends, etc. live in V2.
- No admin auth / RBAC for the manual endpoint. Project is single-tenant single-user per `AGENT.md` §4.4.

## Decisions

### Decision 1: Post-scrape trigger lives in the scheduler, not the scraper engine
The scheduler is where comment scrapes get dispatched, so it knows when one finishes. Putting the trigger in `scraper/engine.py` would mean the engine has to know about the analysis layer — a backward dependency. Keeping it in the scheduler preserves the architecture's top-down direction (scheduler → scraper → DB; scheduler → analysis → DB).

**Alternative considered:** A DB trigger on `doudian_comment INSERT`. Rejected: opaque, off-band from the scheduler's task lifecycle, and we already broadcast task events through `/ws/tasks` from the scheduler.

**Alternative considered:** Listening on `/ws/tasks` for `task_finished` events and dispatching annotation. Rejected: introduces a self-listening loop; the in-process function call is simpler.

### Decision 2: Synchronous annotation within the window
`annotate_pending` is `await`-ed inline. With `batch_size=50` and ~1.5s per LLM call (rough V4 Flash p50), worst case wall-clock = 75s; typical comment-scrape windows allow 5+ minutes of slack. Inline keeps the task lifecycle observable: a scheduler window logs `done` only after annotation finishes.

**Alternative considered:** Background asyncio task. Rejected: harder to observe in logs, complicates the scrape_task_run lifecycle.

### Decision 3: Daily catch-up at 21:30 (the latest existing window)
21:30 is the last window before the 00:00–06:00 quiet hours. By then the day's comment scrapes (12:00, 18:00, 21:30 if applicable) have all had a chance to run. Catch-up there minimizes overnight orphan-row time.

**Alternative considered:** Running at 02:00 in the maintenance window. Rejected: quiet hours rule disallows merchant scrapes there, and even though LLM calls are not scrapes, putting the AI cost during quiet hours conflates two concerns. Keep AI work in active hours.

### Decision 4: Spend guard reads from `ai_generation` accounting, not maintains its own counter
`ai_generation` already records every LLM call with `cost_yuan`. A simple `SELECT SUM(cost_yuan) WHERE DATE(created_at)=CURDATE()` is the source of truth. No new Redis counter, no double accounting.

**Alternative considered:** Redis counter for fast reads. Rejected: a DB SUM over today's rows is sub-millisecond at this scale (sub-1000 rows per day), and the DB is already loaded by the worker for the comment SELECT.

### Decision 5: Manual endpoint is synchronous
`POST /api/v1/scrape/annotate-now` blocks until the worker finishes. For 22 rows that's ~30s, well within the operator's patience and HTTP timeout. If batch sizes grow, we can switch to fire-and-poll via the existing scrape_task_run table; for V1 inline is fine.

### Decision 6: Alert hook reuses existing `negative_comment_surge` rule, doesn't change thresholds
The bootstrap change's `alert-engine` capability defines the surge rule (count threshold, time window). This proposal does NOT touch those numbers — it only ensures the upstream signal (rows with `sentiment="negative"`) is actually produced, which it currently isn't for new arrivals. The alert engine's existing subscription will then fire normally.

### Decision 7: Parallelism in tasks.md
Backend wiring touches 3 files (`scheduler.py`, `comment_worker.py`, new `api/v1/scrape_annotate.py`) — these can be done in parallel by 3 subagents because they share no code. Tests can be written by a 4th lane in parallel against the same files (mocks). The 5th sequential step is end-to-end smoke. So 4 parallel lanes + 1 serial finish.

## Risks / Trade-offs

- **[Risk] LLM provider rate-limit during catch-up of large backlog** → Mitigation: existing gateway has retries with exponential backoff. Worst case the catch-up reports partial progress, daily budget caps spend.
- **[Risk] Prompt drift: model returns invalid JSON for some Chinese comments** → Existing heuristic `_extract_json` and `log.warning("analysis.parse_failed", ...)`. Affected rows stay NULL and retry tomorrow. Bounded harm.
- **[Risk] Inline annotation extends scheduler window beyond expected duration** → Quiet-hours constraint is hour-based, not duration-based; even 5-minute overruns are safe. Logged for visibility.
- **[Trade-off] Synchronous manual endpoint can timeout for very large backlogs** → Accepted because: (a) one-shot operator action, (b) 200-row cap protects, (c) async-poll endpoint is a trivial follow-up if the operator ever runs into it.
- **[Risk] Budget guard silently halts useful work** → Mitigation: response carries `skipped: "budget_exhausted"`; manual API surfaces it explicitly; daily-spend log line at 21:30 alerts the operator to bump `LLM_DAILY_BUDGET_YUAN` if recurrent.

## Migration Plan

1. Apply backend code changes (3 lanes parallel) + tests (4th lane parallel).
2. Set `LLM_DAILY_BUDGET_YUAN=5` in `.env`.
3. Restart api container so the scheduler picks up the new windowing logic.
4. Manually `POST /api/v1/scrape/annotate-now` once to backfill the 22 existing NULL rows. Verify `SELECT COUNT(*) FROM doudian_comment WHERE sentiment IS NULL` returns 0 (modulo rows that arrived during the call).
5. Browser-check Comments page — sentiment labels and pain-point tags should now render real values for the backfilled rows.
6. Rollback: revert the scheduler hook + the API route. Worker code can stay in place (does no harm idle).

## Open Questions

- Should `LLM_DAILY_BUDGET_YUAN` default be ¥5 or higher? **Resolved**: ¥5. At measured costs (~¥0.001/cycle, ~¥0.001 per 50-comment backfill batch), ¥5 supports >2,000 batches/day — vastly more than the scheduler can produce. The cap exists to bound bugs, not normal use.
- Should the manual API require any token / signature? **Resolved**: no. AGENT.md §4.4 explicitly disallows multi-tenant code paths; the API is bound to `127.0.0.1` via the existing docker-compose port mapping, which is the project's authorization model.
- Do we need a CLI counterpart to the manual endpoint? **Open**: deferred. The HTTP endpoint covers the operator-from-browser case; CLI users can `curl` it. Revisit if friction emerges.
