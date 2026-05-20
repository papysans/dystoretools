## ADDED Requirements

### Requirement: MySQL 8 Schema with utf8mb4 and Alembic Migrations
The system SHALL persist relational data in MySQL 8 using `utf8mb4` character set and `utf8mb4_0900_ai_ci` collation. All schema changes SHALL be expressed as Alembic migrations. The system MUST NOT use `Base.metadata.create_all()` in any code path that runs in non-test environments.

#### Scenario: Fresh install brings up schema
- **WHEN** the user runs `alembic upgrade head` on an empty database
- **THEN** the system SHALL create all tables listed in `docs/requirements.md` §6 and report no errors

#### Scenario: Developer modifies a model without migration
- **WHEN** a Pull Request changes a SQLAlchemy model but does not include a corresponding Alembic revision
- **THEN** the CI SHALL detect the divergence (via `alembic check` or equivalent) and block the merge

### Requirement: Async SQLAlchemy 2.0 Sessions
All database access in request and worker code paths SHALL use SQLAlchemy 2.0 async sessions obtained from a single application-level `async_sessionmaker`. The system MUST NOT use synchronous SQLAlchemy sessions in async contexts.

#### Scenario: Endpoint queries the order table
- **WHEN** a FastAPI handler queries `doudian_order`
- **THEN** it SHALL acquire an `AsyncSession` via dependency injection and use `await session.execute(...)`

### Requirement: Time-Series Tables Partitioned by Month
Tables that grow with `scraped_at` (`compass_core_data`, `compass_core_trend`, `member_dashboard_day`, `member_dashboard_hist`, `aftersale_counts`, `comment_tag_stat`) SHALL be MySQL-RANGE-partitioned by month on `scraped_at`. A nightly job SHALL drop partitions older than 12 months.

#### Scenario: Nightly retention job runs
- **WHEN** the `01:00` cron window fires and a partition older than 12 months exists
- **THEN** the system SHALL drop the oldest partition via `ALTER TABLE ... DROP PARTITION` and log the freed-space estimate to `scrape_task_run`

### Requirement: Redis 7 for Four Roles
The system SHALL deploy Redis 7 and use it exclusively for: (a) merchant + public scraper cookie/token state, (b) WebSocket pub-sub fan-out across processes, (c) APScheduler job state, (d) per-domain rate-limit counters. Persistent business data SHALL NOT be stored in Redis.

#### Scenario: WebSocket message reaches multiple subscribers
- **WHEN** the alert engine publishes a message on the Redis channel `ws:alerts`
- **THEN** every connected `/ws/alerts` WebSocket subscriber SHALL receive the message exactly once
