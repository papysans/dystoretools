## ADDED Requirements

### Requirement: Sentiment and Pain-Point Annotation per Comment
For every new row in `doudian_comment`, the system SHALL enqueue an AI analysis task that populates the `sentiment` (one of `positive`, `neutral`, `negative`) and `pain_points_json` (list of `{tag: str, evidence: str}`) columns. Processing latency from comment ingest to annotation SHALL be under 10 minutes during the 12:00 daily window.

#### Scenario: New negative comment arrives during 10:00 scrape
- **WHEN** a comment with rating ≤ 2 is inserted at 10:05
- **THEN** the system SHALL annotate `sentiment="negative"` and populate `pain_points_json` no later than 12:10 of the same day

#### Scenario: AI worker fails on a single comment
- **WHEN** the LLM gateway raises a non-transient error on one comment
- **THEN** the system SHALL leave `sentiment=NULL`, `pain_points_json=NULL`, log the failure, and continue processing other comments

### Requirement: Cross-Product Negative-Comment Clustering
The system SHALL compute, at the 21:30 daily window, a clustering of the past 30 days of negative comments grouped by canonical pain-point tag, producing `comment_tag_stat` rows scoped to the entire shop (`scope='shop'`) and per goods (`scope='goods'`). The clustering SHALL respect tags already discovered in `pain_points_json` rather than re-mining from raw text.

#### Scenario: Daily clustering job runs
- **WHEN** the 21:30 window dispatches the clustering job
- **THEN** the system SHALL write a fresh batch of `comment_tag_stat` rows with `scraped_at=<now>` for every pain-point tag with ≥ 3 occurrences in the past 30 days

### Requirement: Longitudinal Pain-Point Trend
The system SHALL expose, via REST and the comments dashboard page, a per-tag time-series of negative-comment frequency over the past 30 / 90 / 365 days. The series SHALL be derived from `comment_tag_stat` rows; the system MUST NOT recompute the series from `doudian_comment` on every request.

#### Scenario: Operator opens a pain-point trend chart
- **WHEN** the user requests a 90-day trend for tag `物流慢` via `GET /api/v1/comments/pain-point/trend?tag=物流慢&days=90`
- **THEN** the system SHALL return one data point per day from existing `comment_tag_stat` rows and SHALL respond within 500 ms

### Requirement: Differentiation From Platform GPT-Reply
The system MUST NOT generate single-comment reply suggestions targeted at the same use case as the platform's native `shop_comment_gpt_reply` feature. The system SHALL focus its AI capability on cross-product clustering, longitudinal trend, and shop-wide synthesis.

#### Scenario: Code review proposes a single-comment reply generator
- **WHEN** a Pull Request adds an endpoint `POST /api/v1/comments/{id}/reply-draft` that wraps a per-comment LLM call
- **THEN** the change SHALL be rejected as overlapping with platform-native functionality
