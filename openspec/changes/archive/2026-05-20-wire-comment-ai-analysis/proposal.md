## Why

`backend/dystore/analysis/comment_worker.py` ships a complete LLM annotation pipeline (`annotate_pending(batch_size=50)`) that fills `sentiment` ∈ {positive, neutral, negative} and `pain_points_json` on rows in `doudian_comment`. The scraper drops 28 comments per cycle (verified 2026-05-20). **But nothing in the codebase ever calls `annotate_pending`.** A `grep -rn annotate_pending backend/` returns exactly one match — the function definition itself.

Consequences in the live system:
- `doudian_comment` table: 22 of 28 rows have `sentiment IS NULL`; `pain_points_json` is uniformly empty.
- The Comments page UI faithfully renders this: every row shows "中性" (the frontend's fallback label for NULL) and "—" for pain points. The page's promise — "AI 情感判定 · 痛点聚类" — is unfulfilled.
- The alert engine's `negative_comment_surge` rule, which subscribes to comments tagged `sentiment="negative"`, never fires from the main scrape because the main `doudian_comment_list` scrape leaves sentiment NULL. The 6 existing `negative`-tagged rows came from `doudian_comment_negative` (a separate scrape target that calls the platform's pre-filtered negative-comments endpoint and labels rows in that handler) — but that misses any newly arriving negative comments that the platform hasn't classified yet.

The fix is small but real: wire `annotate_pending` into the scheduler so each comment-scrape window is followed by an annotation pass. Cost is bounded — DeepSeek V4 Flash, ~512 output tokens per comment, ~22 comments backfill ≈ ¥0.005 one-time; ongoing batches ≈ ¥0.001 per scrape cycle.

## What Changes

- Add a post-scrape hook in `backend/dystore/scheduler/scheduler.py` that triggers `annotate_pending(batch_size=50)` whenever a comment-class scrape (`doudian_comment_list` or `doudian_comment_negative`) finishes successfully. Implementation: append the call inside `_dispatch_window` after `run_target` returns, gated on `spec.target in {"doudian_comment_list", "doudian_comment_negative"}`.
- Add a daily catch-up cron at 21:30 (the existing `2130` window) that runs `annotate_pending(batch_size=200)` regardless of whether a comment scrape ran — covers cases where the scraper failed but earlier comments are still un-annotated.
- Add a spend guard in `comment_worker.annotate_pending`: read today's accumulated AI spend from `ai_generation` accounting; if it exceeds `LLM_DAILY_BUDGET_YUAN` (env var, default `¥5`), log a warning and return early without making LLM calls.
- Route `comment_worker.complete()` calls through the `kind="comment_sentiment"` LLM gateway path — already implemented, just confirm it picks V4 Flash (cost-optimized).
- Add `POST /api/v1/scrape/annotate-now` admin trigger so the operator can force a backfill on demand without waiting for the next 21:30 window.
- Add an alert hook: after `annotate_pending` finishes, if any row newly classified as `sentiment="negative"` lands, broadcast on `/ws/alerts` via the existing `negative_comment_surge` alert type (currently the rule is driven by raw count thresholds — this proposal does NOT change those thresholds, only ensures the upstream classification produces signal in the first place).
- **Non-goal**: no change to the prompt template, the JSON parsing heuristic, or the PII scrubber. All three were validated when the worker was first written.
- **Non-goal**: no cross-product clustering, no longitudinal trends, no AI dashboard surface. Those are V2-scope per `bootstrap-merchant-platform` `comment-analysis` capability.

## Capabilities

### New Capabilities

(none — this change wires existing code into existing surfaces; no new bounded contexts)

### Modified Capabilities

- `comment-analysis`: the `bootstrap-merchant-platform` change introduced this capability with a worker but did not require automatic invocation. This change adds the requirement that the worker runs automatically after each comment scrape, with cost guarding and a manual trigger endpoint. Delta only (ADDED requirements within the existing spec); existing requirements unchanged.

> Note: `openspec/specs/` is currently empty because `bootstrap-merchant-platform` has not been archived. The spec file authored here for `comment-analysis` will be a delta against the future archived spec; until then, the delta semantics are captured as ADDED requirements in this change's `specs/comment-analysis/spec.md` and reviewed alongside the parent change's archive.

## Impact

- **Code (backend)**: 1 edit to `scheduler.py` (~10 LOC: post-target hook + daily catch-up job). 1 edit to `comment_worker.py` (~15 LOC: daily-spend guard + return summary). 1 new file `api/v1/scrape_annotate.py` (~25 LOC: admin endpoint).
- **Code (tests)**: 1 new file `backend/tests/analysis/test_comment_worker_wired.py` (~40 LOC: mocked LLM, asserts annotation flows trigger after comment scrape).
- **Config**: 1 env var `LLM_DAILY_BUDGET_YUAN` (default 5) added to `.env.example`.
- **Storage**: No schema change. Existing `ai_generation` accounting table provides the spend lookup.
- **Cost**: ~¥0.001 per scrape cycle ongoing; ~¥0.005 one-time backfill of the 22 NULL rows.
- **Risk**: LLM provider outages → worker logs warning and exits non-fatally (already implemented). Spend guard caps blast radius if a future bug double-triggers.
- **Verifiability**: Smoke = trigger `POST /api/v1/scrape/annotate-now`, then `SELECT COUNT(*) FROM doudian_comment WHERE sentiment IS NULL` drops to 0 (or stays at whatever rows newly arrived). Comments page shows real sentiment labels and pain-point tags.
