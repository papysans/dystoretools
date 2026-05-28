## ADDED Requirements

### Requirement: Nine-Window Daily Schedule
The system SHALL register the following APScheduler cron triggers, mirroring the operations rhythm from source PDF2: `00:10`, `01:00`, `07:30`, `10:00`, `12:00`, `15:00`, `18:00`, `21:30`, `02:00`. The `01:00` and `02:00` windows SHALL only execute local-database tasks (archive, backup) and SHALL NOT issue any HTTP requests to `*.jinritemai.com` or `*.oceanengine.com`.

#### Scenario: 01:00 window fires
- **WHEN** the scheduler triggers the 01:00 window
- **THEN** the system SHALL run database archive and backup tasks only, and SHALL NOT dispatch any scrape task whose `subsystem` is `merchant` or `public`

#### Scenario: 07:30 window fires
- **WHEN** the scheduler triggers the 07:30 window
- **THEN** the system SHALL dispatch the merchant-scrape targets whose YAML `schedule.cron` matches that time

### Requirement: Task Lifecycle Persistence and Broadcast
Every scrape task dispatch SHALL create a `scrape_task_run` row with fields `id`, `target`, `subsystem`, `started_at`, `finished_at`, `status` (one of `queued`, `running`, `done`, `failed`, `skipped_quiet_hours`, `auth_expired`, `data_source_failed`), `items_count`, `error_msg`. The system SHALL broadcast the row's lifecycle transitions on the `/ws/tasks` WebSocket channel.

#### Scenario: Task succeeds
- **WHEN** a scrape task completes successfully with N parsed items
- **THEN** the system SHALL update `status="done"`, `items_count=N`, `finished_at=<now>` and broadcast a `task_done` message on `/ws/tasks` containing the row's id and counts

#### Scenario: Task fails with exception
- **WHEN** a scrape task raises an unhandled exception
- **THEN** the system SHALL capture the exception class name and first 2 KB of the message into `error_msg`, set `status="failed"`, and broadcast `task_failed` on `/ws/tasks`

### Requirement: Single-Concurrency Lock per (Account, Domain)
The scheduler SHALL hold an in-process asyncio lock keyed by (`account_id`, `domain`) such that at most one in-flight scrape exists per pair. Tasks attempting to acquire a held lock SHALL queue, not fail.

#### Scenario: Two cron windows fire close together
- **WHEN** the `10:00` window dispatches a merchant task and the `12:00` window dispatches another merchant task while the first is still running
- **THEN** the second task SHALL wait for the first to release the lock before starting

### Requirement: Manual Run Override
The system SHALL expose an HTTP endpoint `POST /api/v1/scrape/run` accepting a `target` parameter that immediately dispatches the named scrape outside the cron schedule. The manual dispatch SHALL still respect the quiet-hours rule and the single-concurrency lock.

#### Scenario: Manual run during quiet hours against merchant target
- **WHEN** the user requests a manual run of a merchant target at 03:00
- **THEN** the system SHALL refuse with HTTP 409 and a body indicating quiet-hours protection
