## ADDED Requirements

### Requirement: Typed Alert Categories
The system SHALL emit alerts under typed categories, each with severity in `info`, `warn`, `critical`: `negative_comment_surge`, `aftersale_deadline_approaching`, `aftersale_urge`, `aftersale_arbitrate_pending`, `low_stock`, `dead_stock`, `sales_anomaly_drop`, `sales_anomaly_spike`, `shop_violation`, `experience_score_drop`, `compass_warning`. Every emitted alert SHALL produce a row in the `alert` table.

#### Scenario: Five new negative comments in one hour for one goods
- **WHEN** the comment-analysis worker finishes annotating and detects ≥ 5 negative comments for a single `goods_id` within the past 60 minutes
- **THEN** the system SHALL insert one `alert` row with `kind=negative_comment_surge`, `severity=warn`, `payload_json={goods_id, count, sample_comment_ids}`

### Requirement: Aftersale 18-Dim Alerts Derived From Counts
The system SHALL derive aftersale alerts from the 18-dimension counts returned by `/shopuser/aftersale/counts`. The mapping SHALL be: any count in the `approaching_deadline_audit` or `urge_audit` dims → `aftersale_deadline_approaching`; any count in the `arbitrate_pending*` dims → `aftersale_arbitrate_pending`. Counts SHALL be re-checked every scrape window.

#### Scenario: Five orders pending arbitration appear
- **WHEN** a scrape sets `arbitrate_pending_evidence=5`
- **THEN** the system SHALL emit one `alert` row with `kind=aftersale_arbitrate_pending`, `severity=critical`, `payload_json={dim:'arbitrate_pending_evidence', count:5}`

### Requirement: WebSocket Broadcast
Every newly-inserted `alert` row SHALL be broadcast on `/ws/alerts` to all connected subscribers within 1 second of insertion.

#### Scenario: Frontend subscribed and alert fires
- **WHEN** an `alert` row is inserted while the frontend has an open `/ws/alerts` WebSocket
- **THEN** the frontend SHALL receive the alert payload within 1 second

### Requirement: Manual Acknowledgement
The system SHALL expose `POST /api/v1/alerts/{id}/ack` setting `acked_at=<now>` for the named alert. Acknowledged alerts SHALL still be visible in the alert center but visually de-emphasised.

#### Scenario: Operator acknowledges an alert
- **WHEN** the operator clicks "确认" on an alert in the UI
- **THEN** the system SHALL set `acked_at` and SHALL broadcast an `alert_acked` event on `/ws/alerts` so other open sessions update their UI

### Requirement: Anomaly Detection Baseline
The system SHALL detect sales-anomaly alerts (`sales_anomaly_drop`, `sales_anomaly_spike`) by comparing the trailing 1-hour `doudian_order` row count against the median count for the same 1-hour-of-day across the past 7 days. A delta exceeding ± 3 × MAD SHALL fire an alert.

#### Scenario: Sudden sales drop in evening hour
- **WHEN** the 21:30 window finishes and the 20:00–21:00 order count is ≤ median − 3 × MAD
- **THEN** the system SHALL emit `sales_anomaly_drop` with `severity=warn` and a payload containing observed vs. expected counts
