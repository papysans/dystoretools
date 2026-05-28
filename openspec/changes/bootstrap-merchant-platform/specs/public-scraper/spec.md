## ADDED Requirements

### Requirement: Physical Isolation From MerchantScraper
The PublicScraper subsystem SHALL run in a separate Playwright persistent context rooted at `~/.dystore/playwright/public/`, use headless Chromium, and MUST NOT share cookies, IP, or fingerprint with the MerchantScraper. The MerchantScraper account's cookies SHALL never be loaded into PublicScraper contexts and vice versa.

#### Scenario: Cookie sharing prevented at boot
- **WHEN** the system starts both scrapers
- **THEN** the two persistent context directories SHALL be distinct and the system SHALL verify at startup that no shared cookies exist between them

### Requirement: DataSource Interface for Pluggable Backends
The system SHALL expose a `DataSource` interface with methods `fetch_peer_shop(...)`, `fetch_peer_goods(...)`, `fetch_peer_livestream(...)`. The default implementation SHALL be `PlaywrightDataSource`. The system SHALL accept additional implementations (e.g., `HuituDataSource` for 灰豚 API, `ChanMamaDataSource` for 蝉妈妈 API) selectable by configuration, without changes to consumer code.

#### Scenario: Switching to a 3rd-party API fallback
- **WHEN** the user sets `PUBLIC_SCRAPER_BACKEND=huitu` in `.env` and provides a valid API key
- **THEN** the system SHALL route `fetch_peer_shop` calls to `HuituDataSource` and SHALL NOT launch Playwright for those calls

#### Scenario: Backend unavailable at runtime
- **WHEN** the selected `DataSource` raises an unrecoverable error
- **THEN** the system SHALL log the failure, mark the affected `scrape_task_run` as `status="data_source_failed"`, and SHALL NOT silently fall back to a different backend

### Requirement: Anonymous Anti-Detection
The PublicScraper SHALL use a rotating cookie pool stored in Redis under the namespace `public-scraper:cookies:*`, randomized User-Agent per session, and per-domain rate limiting of at most 1 request per 6 seconds. The 0–06:30 quiet-hours rule SHALL NOT apply (public pages permit anytime access).

#### Scenario: Rate limit exceeded
- **WHEN** the per-domain request budget is exhausted
- **THEN** the system SHALL queue subsequent requests against that domain rather than dropping them, and SHALL log a `rate_limited` event without halting the task
