## ADDED Requirements

### Requirement: Ingest Member Dashboard Endpoints Daily
The system SHALL scrape, at the 12:00 daily window, the three endpoints `/api/member/dashboard/v2/get_shop_dashboard_aggregate_data`, `…/get_shop_dashboard_daily_data`, `…/get_shop_dashboard_histogram_data` and persist them to `member_dashboard_agg`, `member_dashboard_day`, `member_dashboard_hist` respectively.

#### Scenario: 12:00 member ingest runs
- **WHEN** the 12:00 window fires and the merchant session is valid
- **THEN** the system SHALL invoke the three scrape specs and SHALL insert at least one row per table reflecting today's data

### Requirement: Ingest Audience Feature
The system SHALL scrape `/api/marketing/user_profile/get_audience_feature` with `userType=2&referenceUserType=0` at the 12:00 daily window and persist results to `audience_feature`.

#### Scenario: Audience profile updates daily
- **WHEN** the 12:00 window fires
- **THEN** the system SHALL ingest at least one `audience_feature` row per feature kind returned by the upstream

### Requirement: Member Dashboard Page Renders Native Data
The frontend SHALL render the 用户运营 page entirely from `member_dashboard_*` and `audience_feature` rows. The system MUST NOT re-aggregate raw orders to compute member KPIs that the platform already provides.

#### Scenario: Operator opens the member dashboard
- **WHEN** the user navigates to /web/member
- **THEN** the page SHALL load aggregate cards, daily trend lines, and histogram bars from `member_dashboard_*` tables, with the most recent `scraped_at` displayed in the header
