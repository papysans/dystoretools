# dashboard-read-paths Specification

## Purpose
TBD - created by archiving change complete-dashboard-read-paths. Update Purpose after archive.
## Requirements
### Requirement: Goods list endpoint
The system SHALL expose `GET /api/v1/goods` that returns the latest snapshot of `doudian_goods` rows, with offset/limit pagination, optional `tab` and `check_status` filters, and a `total` field counting matching rows.

#### Scenario: Default list returns paginated goods with stock
- **WHEN** the client calls `GET /api/v1/goods?page=0&page_size=20`
- **THEN** the response body has `total: 24` (matching the current DB state) and `items` is an array of at most 20 entries, each containing `goods_id`, `title`, `price` (yuan, decimal), `stock`, `tab`, `check_status`, `scraped_at`

#### Scenario: Filter by tab
- **WHEN** the client calls `GET /api/v1/goods?tab=售卖中`
- **THEN** every returned item has `tab == "售卖中"` and `total` reflects the filtered count

#### Scenario: Pagination beyond last page returns empty items
- **WHEN** the client calls `GET /api/v1/goods?page=99&page_size=20`
- **THEN** the response has `total: 24` and `items: []`

### Requirement: Stock list endpoint
The system SHALL expose `GET /api/v1/stock` that returns the latest snapshot of `doudian_stock` rows joined with the goods title (from `doudian_goods.title`), with a `level` field derived as `out` (on_hand <= 0), `low` (on_hand < 5), `over` (on_hand > 200), or `normal`, and SKU-level rows expanded from `raw_json.skus[]` available behind a `?include=skus` query flag.

#### Scenario: List stock with derived level
- **WHEN** the client calls `GET /api/v1/stock?page=0&page_size=20`
- **THEN** `total: 20` and each item has `goods_id`, `title`, `on_hand`, `available`, `locked`, `level` ∈ {`out`, `low`, `normal`, `over`}, `scraped_at`

#### Scenario: SKU expansion
- **WHEN** the client calls `GET /api/v1/stock?include=skus&goods_id=3820752780126192049`
- **THEN** each returned item additionally contains an array `skus` where each entry has `sku_id`, `sku_name`, `stock_num` extracted from `raw_json.data[*].skus[*]`

### Requirement: Aftersale list endpoint
The system SHALL expose `GET /api/v1/aftersale` that returns the latest snapshot of `doudian_aftersale` with offset/limit pagination, optional `type` and `status` integer filters, and `type_label` / `status_label` strings resolved against the canonical enum table maintained in code (`type: 0→退款, 1→退货, 3→换货; status: 6→待审核, 7→进行中, 11→已完成, 27→已关闭`).

#### Scenario: List with enum labels
- **WHEN** the client calls `GET /api/v1/aftersale?page=0&page_size=20`
- **THEN** `total: 30` and each item has `aftersale_id`, `order_sn`, `type` (int), `type_label` (string), `status` (int), `status_label` (string), `refund_amount` (yuan), `deadline_at`, `scraped_at`

#### Scenario: Filter by status
- **WHEN** the client calls `GET /api/v1/aftersale?status=6`
- **THEN** every returned item has `status == 6` and `status_label == "待审核"`

### Requirement: Aftersale 18-dimension counts endpoint
The system SHALL expose `GET /api/v1/aftersale/counts` that returns the *latest snapshot* of the canonical 18 dimensions listed in `docs/api-catalog.md §6`, where "latest snapshot" means rows whose `scraped_at` equals `MAX(scraped_at)` in `aftersale_counts`.

#### Scenario: Returns exactly the canonical 18 dimensions
- **WHEN** the client calls `GET /api/v1/aftersale/counts`
- **THEN** the response is `{ scraped_at: <iso>, dims: { <dim_name>: <count>, ... } }` where `Object.keys(dims).length == 18` and the key set equals exactly `{all_audit_reg_spill, approaching_deadline_audit, urge_audit, presale_all_audit, refund_audit, return_audit, exchange_audit, resend_audit, repair_audit, wait_for_receive_and_delivery, return_for_receive, exchange_for_receive, wait_user_delivery, wait_user_sign, exchange_wait_user_sign, arbitrate_pending_negotiation, arbitrate_pending_evidence, arbitrate_pending}`

#### Scenario: Missing dimension reports zero
- **WHEN** a canonical dimension has no row in the latest snapshot (e.g. server stopped returning it)
- **THEN** the response still contains that key with value `0` and does not 500

### Requirement: Member dashboard endpoint
The system SHALL expose `GET /api/v1/member/dashboard` that returns three sections derived from `member_dashboard_agg` (aggregate KPIs), `member_dashboard_day` (time series), and `member_dashboard_hist` (purchase-count histogram), all from the most recent scraped_at per source.

#### Scenario: Aggregate KPIs come from raw_json.data.data_head
- **WHEN** the client calls `GET /api/v1/member/dashboard`
- **THEN** the response has an `agg` array where each item has `index_name`, `index_display`, `value` (number in yuan if `unit == "price"`, else raw number), `unit`, `change_value` (ratio), `peer_excellent` (ratio), sourced from `member_dashboard_agg.raw_json.data.data_head[*]` of the latest row

#### Scenario: Daily series returns last 7 dates
- **WHEN** the client calls `GET /api/v1/member/dashboard`
- **THEN** the response has `daily` as an array of `{date, metric, value}` ordered ascending by `date`, with at most 30 most recent dates

#### Scenario: Histogram is de-duplicated
- **WHEN** `member_dashboard_hist` contains multiple scrape rounds for the same `bucket`
- **THEN** only the rows from `MAX(scraped_at)` are returned

### Requirement: Frontend pages consume the new endpoints
The system SHALL render the four currently-empty pages (Goods, Stock, Aftersale, Member) using the new endpoints, with no remaining static "—" placeholders when the DB has data.

#### Scenario: Goods page shows the goods table
- **WHEN** the user navigates to `/goods`
- **THEN** the page issues `GET /api/v1/goods?page=0&page_size=20`, renders a table with the columns 商品标题 / 价格 / 库存 / 状态 / 抓取时间, and the row count equals the response `items.length`

#### Scenario: Stock page shows level KPIs
- **WHEN** the user navigates to `/stock`
- **THEN** the page issues `GET /api/v1/stock?page=0&page_size=50` and displays four KPI tiles (低库存 / 缺货 / 超量 / 正常) populated from the count of items per `level`, plus the underlying table

#### Scenario: Aftersale page shows 18-dim grid
- **WHEN** the user navigates to `/aftersale`
- **THEN** the page issues `GET /api/v1/aftersale/counts` and renders 18 KPI tiles in a grid, plus issues `GET /api/v1/aftersale` and renders the after-sale order table with localized type/status labels

#### Scenario: Member page renders charts
- **WHEN** the user navigates to `/member`
- **THEN** the page issues `GET /api/v1/member/dashboard` and renders (a) four KPI tiles from `agg`, (b) an ECharts line chart from `daily`, (c) an ECharts bar chart from `hist`

### Requirement: Aftersale enum module is the single source of truth
The system SHALL maintain a single `web/src/api/enums.ts` module exporting `AFTERSALE_TYPE` and `AFTERSALE_STATUS` records, with values verified from current DB samples, and any frontend code that maps these ints to Chinese labels MUST import from this module.

#### Scenario: Both backend and frontend use the same enum
- **WHEN** the backend resolves `type_label` for a row with `type: 0`
- **THEN** it returns "退款", matching `AFTERSALE_TYPE[0]` in the frontend enum module

### Requirement: Spec-layer bug fixes
The system SHALL persist `date` for `doudian_member_hist`, persist `is_alarming` as boolean for `doudian_sku_diagnose`, and populate `member_dashboard_agg.indices_json` from the response's `data.data_head[*].index_name` array on each scrape.

#### Scenario: New member_hist scrape has date populated
- **WHEN** the scheduler runs `doudian_member_hist` after this change ships
- **THEN** every newly inserted row has `date == DATE(scraped_at)` and not NULL

#### Scenario: sku_diagnose preserves boolean
- **WHEN** the scheduler runs `doudian_sku_diagnose` after this change ships
- **THEN** rows have `diagnose_type` either `"true"` / `"false"` (lowercase) or — preferred — the column accepts and stores boolean directly per the column type

#### Scenario: indices_json backfilled and populated going forward
- **WHEN** any new `member_dashboard_agg` row is written
- **THEN** its `indices_json` column contains an array of all `index_name` values present in `raw_json.data.data_head`, and the existing 2 rows have been backfilled via one-shot SQL

