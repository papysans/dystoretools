## ADDED Requirements

### Requirement: Persistent Browser Context for Merchant Session
The system SHALL maintain the merchant's logged-in 抖店 session using a Playwright persistent Chromium context rooted at `~/.dystore/playwright/doudian/`, launched with `channel="chrome"`, locale `zh-CN`, timezone `Asia/Shanghai`, and the user's installed Chrome browser binary.

#### Scenario: First-run cold start
- **WHEN** the scraper starts and the persistent context directory does not exist
- **THEN** the system SHALL create the directory, launch a headed Chromium with `channel="chrome"`, navigate to `https://fxg.jinritemai.com/login/common`, and emit a `session_required` event on `/ws/auth-required`

#### Scenario: Warm restart with valid session
- **WHEN** the scraper starts and the persistent context directory contains cookies for `.jinritemai.com` that the platform accepts
- **THEN** the system SHALL reuse the existing context without re-opening the login page and SHALL NOT emit any auth-required event

### Requirement: Manual One-Time Login Flow
The system SHALL require the human user to complete the initial login (email + password) and any platform-triggered risk verification (email OTP) by hand in a visible browser window. The system MUST NOT automate password entry, OTP retrieval, or risk-verification answers.

#### Scenario: Risk verification surfaces during login
- **WHEN** the platform redirects the login submission to a page containing the text `安全验证`
- **THEN** the system SHALL leave the visible window open, halt all background scraping, and publish a `risk_verification_required` event on `/ws/auth-required` so the frontend can prompt the user

#### Scenario: Successful login completion
- **WHEN** the page URL changes from `/login/common*` to a non-login path under `https://fxg.jinritemai.com/`
- **THEN** the system SHALL persist the new cookies to the context directory, record a `login_succeeded` row in `session_event`, and publish a `session_ready` event on `/ws/auth-required`

### Requirement: Session Expiry Detection
The system SHALL detect session expiry by two complementary signals: (a) any navigation that lands on a URL containing `/login/common`, and (b) periodic polling of `/ecomauth/loginv1/session_check` every 15 minutes during active scrape windows.

#### Scenario: Mid-scrape session expiry
- **WHEN** the scraper navigates to a target page and the post-navigation URL contains `/login/common`
- **THEN** the system SHALL abort the current scrape task, mark its `scrape_task_run` row with `status="auth_expired"`, publish `session_expired` on `/ws/auth-required`, and stop dispatching new merchant-domain tasks until re-auth completes

#### Scenario: Heartbeat failure
- **WHEN** the 15-minute `session_check` call returns a non-success status during a scrape window
- **THEN** the system SHALL treat the next scheduled scrape as if mid-scrape expiry occurred (queue paused, user prompted)

### Requirement: No Automated Re-Login Attempts
The system MUST NOT attempt to log in programmatically. All credential re-entry MUST be performed by the human user through a visible browser window opened by the system.

#### Scenario: Re-auth required
- **WHEN** session expiry is detected
- **THEN** the system SHALL open a visible Chromium window to `https://fxg.jinritemai.com/login/common` and wait for the human user; the system SHALL NOT call any internal "auto-login" routine
