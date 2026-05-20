## ADDED Requirements

### Requirement: Ingest Compass Search Analytics
The system SHALL scrape `/compass_api/shop/mall/dd_search/search_analysis/core_data` and `…/core_data_trend_v2` at the 12:00 and 18:00 daily windows, persisting to `compass_core_data` and `compass_core_trend`. The system SHALL respect the upstream `date_range_v2` config — if the upstream reports the requested date range is unavailable, the system SHALL skip the call and log `compass_range_unavailable`.

#### Scenario: 12:00 window fetches today's core data
- **WHEN** the 12:00 window fires
- **THEN** the system SHALL fetch core data for the trailing 7-day window and write rows to `compass_core_data`

### Requirement: Ingest Compass Diagnosis and Recommendations
The system SHALL scrape `/compass_api/shop/mall/search_diagnosis/tab_num_v2`, `…/optimize_list`, `…/recommend_optimized_product_v2`, `…/batch_tool_card_v2` at the 18:00 daily window, persisting to `compass_diagnose`. The platform's recommendations SHALL be exposed verbatim on the 罗盘 dashboard with a "来自抖店罗盘" attribution.

#### Scenario: Platform recommends optimizing 5 products
- **WHEN** `/compass_api/.../recommend_optimized_product_v2` returns 5 candidates
- **THEN** the system SHALL persist 5 `compass_diagnose` rows and the dashboard 罗盘 page SHALL list all 5 with the platform attribution badge

### Requirement: Ingest Industry Word Ranking
The system SHALL scrape `/compass_api/shop/mall/search_analysis/industry_words/doudian_rank_v3` for the merchant's primary industry and category at the 18:00 daily window, persisting to `compass_industry_word`. The ranking SHALL be queryable per industry+category+rank_type in the dashboard.

#### Scenario: Operator views industry-word trend
- **WHEN** the user opens 罗盘 → 行业词
- **THEN** the system SHALL render the latest rankings from `compass_industry_word`, grouped by `rank_type`, with each row showing rank delta vs. the prior scrape

### Requirement: Ingest Shop Video List
The system SHALL scrape `/compass_api/shop/mall/dd_search/after_watch/shop_video_list` at the 18:00 daily window, persisting to `shop_video`. The list SHALL be the source for self-owned short-video analytics — the system MUST NOT scrape 抖音公开页 for the merchant's own videos.

#### Scenario: Self-video data appears
- **WHEN** the 18:00 window fires and the shop has self-published videos
- **THEN** the system SHALL persist at least one `shop_video` row per video returned, including play_count and gmv fields

### Requirement: Permission Gate Probing
Before scraping any Compass target, the system SHALL invoke `/compass_api/shop/mall/search_diagnosis/permission` (or the analogous gate per target). If the response indicates the shop is gated out, the system SHALL skip the target and record `permission_denied` in `scrape_task_run` without raising.

#### Scenario: Shop lacks diagnosis permission
- **WHEN** the permission probe returns a gated response
- **THEN** the system SHALL skip the scrape and SHALL NOT mark the task as failed
