# comment-analysis Specification

## Purpose
TBD - created by archiving change wire-comment-ai-analysis. Update Purpose after archive.
## Requirements
### Requirement: Automatic post-scrape annotation
The system SHALL invoke `annotate_pending(batch_size=50)` automatically after a successful `doudian_comment_list` or `doudian_comment_negative` scrape, within the same scheduler window, before the window completes.

#### Scenario: Comment scrape finishes with new rows
- **WHEN** `run_target` for `doudian_comment_list` returns with `status="done"` and inserted >= 1 new comment row
- **THEN** the scheduler invokes `annotate_pending(batch_size=50)` and waits for it to complete (logging a summary), before marking the window done

#### Scenario: Comment scrape fails
- **WHEN** `run_target` for `doudian_comment_list` raises or returns `status="failed"`
- **THEN** the scheduler does NOT invoke annotation in that window; the daily catch-up job is the safety net

### Requirement: Daily annotation catch-up
The system SHALL run `annotate_pending(batch_size=200)` once daily at the 21:30 scheduler window regardless of whether a comment scrape ran that day, so any orphan rows with `sentiment IS NULL` are eventually classified.

#### Scenario: Daily catch-up runs after the 21:30 window
- **WHEN** the scheduler enters the `2130` window
- **THEN** after dispatching any merchant scrape targets in that window, the scheduler invokes `annotate_pending(batch_size=200)` and logs the result

#### Scenario: No NULL rows pending
- **WHEN** the catch-up runs and `SELECT COUNT(*) FROM doudian_comment WHERE sentiment IS NULL` is 0
- **THEN** `annotate_pending` returns `{ok: 0, failed: 0, total: 0}` without making any LLM call

### Requirement: Daily spend guard
The system SHALL refuse to run `annotate_pending` further once today's AI spend (sum of `ai_generation.cost_yuan` where `DATE(created_at) = CURDATE()`) exceeds `LLM_DAILY_BUDGET_YUAN` (env var, default ¥5), logging a warning and returning a `{skipped: "budget_exhausted", spend_yuan: <amount>}` summary instead.

#### Scenario: Budget exhausted mid-batch
- **WHEN** `annotate_pending` is mid-iteration and the running spend reaches the budget
- **THEN** the worker stops issuing new LLM calls, commits whatever was already written, and returns the summary including the partial counts

#### Scenario: Budget unset
- **WHEN** `LLM_DAILY_BUDGET_YUAN` is unset
- **THEN** the default of ¥5 is applied; the system never runs unbounded

### Requirement: Manual annotation trigger
The system SHALL expose `POST /api/v1/scrape/annotate-now` (admin / single-user surface) that triggers `annotate_pending(batch_size=200)` synchronously and returns the worker's summary JSON. The endpoint MUST honour the daily spend guard.

#### Scenario: Operator forces a backfill
- **WHEN** an authenticated client POSTs to `/api/v1/scrape/annotate-now`
- **THEN** the response is `{ok, failed, total, spend_yuan}` and any newly annotated rows are visible in `doudian_comment` immediately

#### Scenario: Budget already exhausted
- **WHEN** the same endpoint is called after the daily budget is spent
- **THEN** the response is `{skipped: "budget_exhausted", spend_yuan}` with HTTP 200 (not an error — the operator was informed cleanly)

### Requirement: Cost-tier model selection
The system SHALL call `llm.gateway.complete(kind="comment_sentiment", ...)` for every annotation, which routes to DeepSeek V4 Flash (the cost-optimized tier) per `memory/llm_choice.md`. The worker MUST NOT hardcode a model name; routing decisions belong to the gateway.

#### Scenario: Annotation request uses the gateway
- **WHEN** `annotate_comment(comment_id)` issues an LLM call
- **THEN** it calls `complete(prompt, kind="comment_sentiment", max_tokens=512)` and does not pass an explicit model parameter

### Requirement: Alert hook on negative classification
After `annotate_pending` finishes, the system SHALL count rows newly classified as `sentiment="negative"` in that batch and, if the count crosses the threshold defined in the `negative_comment_surge` alert rule (existing), emit a single alert on `/ws/alerts` referencing those comment IDs.

#### Scenario: Negative surge detected
- **WHEN** a batch annotation tags >= N comments as negative within one run (N defined by the existing alert rule)
- **THEN** an alert row is inserted with `type="negative_comment_surge"` and broadcast on `/ws/alerts`

#### Scenario: Below threshold
- **WHEN** fewer than N comments are tagged negative in a batch
- **THEN** no alert is emitted (existing rule's individual-row signals are unaffected)

### Requirement: Worker returns structured summary
`annotate_pending` SHALL return `{ok, failed, total, skipped?: string, spend_yuan?: number, negative_new?: number}` so callers (scheduler hook, manual API, tests) can act on the result without parsing logs.

#### Scenario: Worker returns structured summary
- **WHEN** `annotate_pending` finishes any batch
- **THEN** the returned dict has at minimum `ok`, `failed`, `total` integer keys; on early-exit paths it additionally has `skipped: "budget_exhausted" | "no_pending"`

