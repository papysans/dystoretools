## ADDED Requirements

### Requirement: Response-Interceptor Scrape Pattern
The system SHALL extract merchant-backend data by registering a Playwright `page.on("response", ...)` handler before navigation, filtering responses by URL pattern and HTTP method, and parsing the JSON body of matching responses. The system MUST NOT construct, sign, or replay `fxg.jinritemai.com/api/*` requests using `httpx` or any other non-browser HTTP client.

#### Scenario: Scrape order list via interceptor
- **WHEN** a scrape task targets the order list
- **THEN** the system SHALL register a response handler matching `/api/order/searchlist`, navigate to `/ffa/morder/order/list`, wait until `networkidle`, and persist every captured JSON payload

#### Scenario: Attempted direct HTTP replay is rejected
- **WHEN** code under review issues a request to any `fxg.jinritemai.com/api/*` path via `httpx`, `aiohttp`, or `requests`
- **THEN** the implementation SHALL be considered non-compliant with this requirement and code review SHALL block the change

### Requirement: Declarative YAML Target Specs
Each merchant-backend scrape target SHALL be defined by a single YAML file under `backend/dystore/scraper/specs/` with fields: `target`, `subsystem`, `nav` (`url`, `wait_until`, `settle_ms`), `schedule` (cron), `intercept` (`url_contains`, `method`), `extract` (`jsonpath`, `fields` map), `sink` (`table`, `upsert_key`, `store_raw`). Custom interactions are declared as a `pre_actions` list of click/fill/select steps.

#### Scenario: Adding a new scrape target
- **WHEN** a developer wants to scrape a previously-unscoped merchant page
- **THEN** the developer SHALL add one YAML file under `backend/dystore/scraper/specs/` and SHALL NOT add any Python class or module for that target

#### Scenario: Spec validation at startup
- **WHEN** the scraper starts
- **THEN** the system SHALL validate every YAML spec against a Pydantic schema and SHALL refuse to start if any spec is malformed

### Requirement: Raw Payload Preservation
Every row inserted by a scrape task SHALL include the full upstream JSON object in a `raw_json` column. The system SHALL never discard upstream fields it has not modelled in the SQL schema.

#### Scenario: Schema evolves after data already scraped
- **WHEN** a new field is added to a scrape spec's `extract.fields` map
- **THEN** the system SHALL be able to re-derive the new field from `raw_json` on existing rows without re-scraping the upstream page

### Requirement: Anti-Detection Rules
The MerchantScraper subsystem MUST satisfy all of: real Chrome via `channel="chrome"`; `playwright-stealth` plugin loaded; per-action random delay sampled from U(3, 10) seconds; no `fxg.*`, `compass_api/*`, `stock/*`, `product/*`, `shopuser/*`, or `after_sale/*` requests between 00:00 and 06:30 local time; at most one in-flight scrape task per (account, domain) tuple; persistent context directory MUST NOT be cleared between runs.

#### Scenario: Two scrapes attempt to run concurrently
- **WHEN** the scheduler dispatches a second merchant-domain task while a first is in flight
- **THEN** the system SHALL queue the second task and only dispatch it after the first completes

#### Scenario: Task scheduled during 0–6am window
- **WHEN** a scrape spec's cron fires at 02:30 against a `fxg.*` URL
- **THEN** the system SHALL skip the firing and log `skipped_quiet_hours` to `scrape_task_run`

#### Scenario: Stealth plugin missing at startup
- **WHEN** the scraper starts and `playwright-stealth` is not installed or fails to load
- **THEN** the system SHALL refuse to start and exit with a non-zero code

### Requirement: Telemetry-Endpoint Filtering
The system SHALL filter out responses from `mon.zijieapi.com`, `lf3-config.bytetcc.com`, `lf3-fe.ecombdstatic.com`, and other static/telemetry hosts in the response interceptor. Only `fxg.jinritemai.com`, `lgw.jinritemai.com`, and `compass_api/*` responses SHALL be considered for extraction.

#### Scenario: Telemetry batch arrives during scrape
- **WHEN** a `POST mon.zijieapi.com/monitor_browser/collect/batch/` response arrives during scraping
- **THEN** the system SHALL ignore it without attempting JSON parse or persistence
