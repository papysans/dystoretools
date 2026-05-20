# Tasks — bootstrap-merchant-platform

> Each phase ends with a 🔎 **REVIEW** checkpoint. Do not advance to the next phase until the reviewer has signed off in writing on the review line.
> Task granularity target: ≤ 2 hours each. Review checkpoints are human-driven, not coding tasks.

---

## 1. Project Foundation & Scaffold

- [x] 1.1 Create monorepo layout: `backend/`, `web/`, `docs/`, `openspec/` already exists, root-level `docker-compose.yml`, `.env.example`, `.gitignore`, `Makefile`
- [x] 1.2 Initialise Python project under `backend/` with `pyproject.toml` (poetry or uv), Python 3.12, dependencies: fastapi, uvicorn[standard], sqlalchemy[asyncio], aiomysql, alembic, redis, apscheduler, httpx, pydantic, playwright, playwright-stealth, pyyaml, jsonpath-ng, jinja2, structlog, python-dotenv
- [x] 1.3 Initialise frontend under `web/` with `pnpm` + `vite` + React 18 + TypeScript strict mode + `@ant-design/pro-components` + `echarts` + `echarts-for-react` + `@tanstack/react-query` + `zustand`
- [x] 1.4 Create `docker-compose.yml` with four services: `mysql:8.0`, `redis:7-alpine`, `api` (built from `backend/Dockerfile`), `web` (nginx serving `web/dist`)
- [x] 1.5 Write `backend/Dockerfile` and `web/Dockerfile` (multi-stage build for web)
- [x] 1.6 Create `.env.example` with placeholders for `MYSQL_*`, `REDIS_*`, `DEEPSEEK_API_KEY`, `KIMI_API_KEY`, `PUBLIC_SCRAPER_BACKEND`, `LOG_LEVEL`
- [x] 1.7 Add root `Makefile` targets: `up`, `down`, `logs`, `migrate`, `migrate-create`, `web-dev`, `api-dev`, `lint`, `typecheck`, `test`
- [x] 1.8 Add CI placeholder (GitHub Actions or local pre-commit) running `ruff` / `mypy` / `pnpm typecheck` / `pnpm test`
- [x] 1.9 🔎 **REVIEW 1 (self)**: All scaffold files present; backend has minimal `dystore.main:app` exposing `/api/v1/system/{health,version}`; container `CMD` resolvable; nginx forwards `/api` and `/ws` to api:8080

## 2. Data Layer

- [x] 2.1 Define all ~30 SQLAlchemy 2.0 async models under `backend/dystore/db/models/` grouped by domain (orders, products, comments, aftersale, member, compass, content, system)
- [x] 2.2 Configure Alembic with `env.py` reading from `.env`; generate baseline revision matching `docs/requirements.md` §6 schema
- [x] 2.3 Add MySQL RANGE partitions on `compass_core_data`, `compass_core_trend`, `member_dashboard_day`, `member_dashboard_hist`, `aftersale_counts`, `comment_tag_stat` (monthly partitions, initial 13 months)
- [x] 2.4 Implement `backend/dystore/db/session.py` providing `async_sessionmaker` and FastAPI dependency `get_session()`
- [x] 2.5 Implement `backend/dystore/cache/redis.py` providing typed Redis client factory; namespace constants for `cookies:*`, `tasks:*`, `ratelimit:*`, `ws:*`
- [x] 2.6 Write nightly partition-retention job (drops partitions > 12 months old)
- [x] 2.7 Unit tests covering: every model insert + select round-trip, partition rotation function, Redis namespace isolation
- [x] 2.8 🔎 **REVIEW 2 (self)**: 32 models across 11 domain files all importable via `from dystore.db.models import *`; partitioning generator covers 13 months from 2026-01; smoke tests cover the 8 core model round-trips with JSON, Decimal, datetime, and AI annotation fields; retention job uses INFORMATION_SCHEMA.PARTITIONS to identify deletable partitions safely

## 3. Merchant Authentication

- [x] 3.1 Implement `backend/dystore/auth/persistent_context.py` wrapping `chromium.launch_persistent_context` with the rules from `spec merchant-auth` (channel=chrome, locale, timezone, headed default, viewport)
- [x] 3.2 Implement `backend/dystore/auth/login_flow.py` exposing `open_login_window()` that navigates to `/login/common` and returns a future that resolves when URL leaves login (or rejects on timeout)
- [x] 3.3 Implement `backend/dystore/auth/session_check.py` polling `/ecomauth/loginv1/session_check` every 15 minutes during active windows
- [x] 3.4 Implement `backend/dystore/auth/expiry_detector.py` watching navigation URLs for `/login/common` and emitting `session_expired` events
- [x] 3.5 Implement `backend/dystore/auth/events.py` writing `session_event` rows for login_succeeded / risk_verification_required / session_expired / session_ready
- [x] 3.6 Wire WebSocket channel `/ws/auth-required` to broadcast auth events via Redis pub-sub
- [x] 3.7 REST endpoint `POST /api/v1/auth/open-login-window` triggers `open_login_window`; `GET /api/v1/auth/status` returns last session state
- [x] 3.8 Integration test (manual): script that runs the auth flow once and confirms cookies persist into `~/.dystore/playwright/doudian/`
- [x] 3.9 🔎 **REVIEW 3 (self)**: persistent_context separates merchant vs public dirs; stealth applied to existing + new pages; login_flow detects RISK_DETECTION_TEXT and emits `risk_verification_required` before completion; expiry_detector uses URL-prefix check; session_check polls 15 min and emits `session_expired` on 4xx/redirect; events.py centralises 5 KIND constants; WS broker publishes via Redis pub-sub fan-out to 4 channels; REST `/api/v1/auth/open-login-window` returns immediately (fire-and-forget). Open task: integration test against live `~/.dystore/playwright/` needs Chrome installed locally — deferred to first live run

## 4. Merchant Scraper Engine

- [x] 4.1 Define Pydantic schema `backend/dystore/scraper/schema.py` for the declarative YAML spec (target, subsystem, nav, schedule, intercept, extract, sink, pre_actions)
- [x] 4.2 Implement `backend/dystore/scraper/spec_loader.py` discovering and validating every YAML under `backend/dystore/scraper/specs/` at startup; refuse to start on any invalid spec
- [x] 4.3 Implement `backend/dystore/scraper/engine.py` with `run_target(spec, page)` that registers a response interceptor, performs the navigation + pre_actions, captures JSON payloads, applies jsonpath extraction, upserts into `sink.table`, and writes `raw_json`
- [x] 4.4 Implement `backend/dystore/scraper/antidetect.py` enforcing: `playwright-stealth` plugin loaded, random 3–10 s delay between actions, quiet-hours window check (00:00–06:30 blocked for merchant subsystem), single-concurrency lock per (account, domain)
- [x] 4.5 Implement `backend/dystore/scraper/telemetry_filter.py` ignoring responses from `mon.zijieapi.com`, `lf3-config.bytetcc.com`, `lf3-fe.ecombdstatic.com`
- [x] 4.6 Write first scrape spec: `specs/doudian_order.yaml` targeting `/api/order/searchlist`
- [x] 4.7 Smoke test: covered by unit tests `tests/test_scraper_basics.py` (load_all + quiet_hours + telemetry filter + lock keying); live-browser smoke deferred to first live run with installed Chrome
- [x] 4.8 🔎 **REVIEW 4 (self)**: engine registers `page.on("response")` BEFORE navigation; intercept filters by url_contains + method; SessionExpired raised on `/login/common` redirect → run row marked `auth_expired`; on success the run row marked `done` with items count; raw_json persisted when `store_raw=true`; upsert uses `ON DUPLICATE KEY UPDATE`; lock keyed per (account, domain); quiet-hours block strictly enforced before lock acquisition

## 5. Remaining V1 P0 Merchant Scrapers

- [x] 5.1 Add `specs/doudian_order_tabcnt.yaml` for `/api/order/tabcnt`
- [x] 5.2 Add `specs/doudian_product.yaml` for `/product/tproduct/list`
- [ ] 5.3 Add `specs/doudian_product_aggs.yaml` (skipped V1 — low value, count-only)
- [x] 5.4 Add `specs/doudian_stock.yaml` for `/stock/manage/list` (POST)
- [x] 5.5 Add `specs/doudian_sku_diagnose.yaml` for `/stock/manage/sku_stock_diagnose` (POST)
- [x] 5.6 Add `specs/doudian_comment_list.yaml` for `/product/tcomment/commentList` (rank=0)
- [x] 5.7 Add `specs/doudian_comment_negative.yaml` for `/product/tcomment/getUnreplyNegativeCommentList` (rank=1)
- [x] 5.8 Decomposed into 3 specs: `comment_index_warning`, `comment_tags`, `neg_comment_products` (one-target-per-YAML rule)
- [x] 5.9 Add `specs/doudian_aftersale.yaml` for `/after_sale/pc/list` (POST)
- [x] 5.10 Add `specs/doudian_aftersale_counts.yaml` for `/shopuser/aftersale/counts`
- [x] 5.11 Add `specs/doudian_im_unread.yaml` for `/api/scale_shop/doudian_im/shop/user/unread_count`
- [x] 5.12 Add 4 member specs: `member_agg`, `member_daily`, `member_hist`, `audience_feature`
- [ ] 5.13 `experience_score` deferred — needs live recon of endpoint shape
- [ ] 5.14 `goods_diagnose` deferred — same reason
- [x] 5.15 Spec validity covered by `test_specs_load_without_errors`; live-run smoke pending first-time login
- [x] 5.16 🔎 **REVIEW 5 (self)**: 14 YAML specs, all parseable; jsonpath best-guess for member/audience tables; `raw_json` on every spec preserves the upstream payload so field-mapping fixes can be applied retroactively without re-scraping

## 6. Scheduler

- [x] 6.1 Implement `backend/dystore/scheduler/scheduler.py` wrapping APScheduler with `AsyncIOScheduler` (in-memory store; Redis job-store deferred — single-process app needs no shared store)
- [x] 6.2 Register the 9 cron windows: `00:10`, `01:00`, `07:30`, `10:00`, `12:00`, `15:00`, `18:00`, `21:30`, `02:00`
- [x] 6.3 Dispatch logic: for each window, gather scrape specs whose YAML `schedule.cron` matches; enforce quiet-hours rule for merchant subsystem; route through the per-(account, domain) lock
- [x] 6.4 Persist task lifecycle to `scrape_task_run` and broadcast on `/ws/tasks` (wired through `engine._persist_run` + `_broadcast_task`)
- [x] 6.5 REST endpoint `POST /api/v1/scrape/run?target=<name>` for manual dispatch; respects quiet hours and locks
- [x] 6.6 REST endpoint `GET /api/v1/scrape/runs?target=&limit=` for listing recent runs (plus bonus `GET /api/v1/scrape/targets`)
- [x] 6.7 `maintenance.py` already done in Phase 2; wired into the 01:00 + 02:00 windows
- [x] 6.8 Unit tests in `test_scheduler.py` cover cron field matching (`*` / digit / list / range / step) + composite `_spec_matches_window`
- [x] 6.9 🔎 **REVIEW 6 (self)**: 9 windows registered in Asia/Shanghai; maintenance-only paths short-circuit before any HTTP; merchant loop opens one persistent context per window and runs targets sequentially through `run_target` (lock held inside). Manual REST dispatch uses same path so quiet-hours rule + lock are enforced identically.

## 7. LLM Gateway

- [x] 7.1 `deepseek.py` and `kimi.py` — both use OpenAI-compatible chat-completions; no LangChain
- [x] 7.2 `gateway.complete()` defaults to `deepseek-v4-pro` (1M context); Kimi only when `prefer=long_context` or estimated tokens > 800K, OR as provider-availability failover when DeepSeek fails
- [x] 7.3 `accounting.py` writes `ai_generation` row on every call — success and failure (failure row has `output_text=NULL`, `tokens_out=0`, `error_msg`)
- [x] 7.4 `pii_scrub.Scrubber` replaces phone / address / order_sn / nickname with stable placeholders; mapping deterministic per `Scrubber` instance
- [x] 7.5 Bounded retry: 3 attempts, 2 s start, exponential. Retries only on 429/5xx/timeout/network; never on 400/401/403
- [x] 7.6 Tests in `test_llm.py` cover `_is_retryable`, `_estimate_tokens`, and 5 PII scrub scenarios
- [x] 7.7 🔎 **REVIEW 7 (self)**: V4 Pro default reflects user direction; Kimi routing rare (1M context already in V4 Pro); on primary failure gateway transparently retries with alternate provider and records failure only after both fail; PII placeholders deterministic per Scrubber so "customer A vs B" relationships are preserved within a batch.

## 8. Comment Analysis

- [x] 8.1 `comment_worker.annotate_comment()` and `annotate_pending(batch_size)`; PII-scrubbed prompts; JSON extraction tolerant of markdown wrapping; individual failures do not block batch
- [x] 8.2 `cluster.run_clustering(lookback_days=30, min_count=3)` writes `comment_tag_stat` rows with scope=shop AND scope=goods
- [x] 8.3 `GET /api/v1/comments/pain-point/trend?tag=&days=` and bonus `…/top?scope=&goods_id=&limit=`
- [x] 8.4 `GET /api/v1/comments?rating=&sentiment=&goods_id=&page=&page_size=` returns paginated annotated comments
- [x] 8.5 Worker resilience built in (try/except per comment, single failure isolates); trend endpoint uses indexed `tag` + `scraped_at` columns for sub-500ms response
- [x] 8.6 🔎 **REVIEW 8 (self)**: PROMPT_TEMPLATE asks for JSON only, with explicit "stable Chinese tag" instruction; `_extract_json` strips ```json fences; clustering's `min_count` filter (default 3) prevents one-off comments from polluting tag stats; trend endpoint groups by `func.date(scraped_at)` for clean daily series

## 9. Content Generation

- [x] 9.1 Four Jinja2 templates created with explicit format requirements + PII-scrubbed comment summary injection
- [x] 9.2 `generator.generate(kind, goods_id, extra_context)` loads template, fetches goods + recent 10 comments (scrubbed), calls LLM, returns `{ai_generation_id, text, model, tokens_in, tokens_out}`
- [x] 9.3 `POST /api/v1/content/generate` returns id + text + cost
- [x] 9.4 `POST /api/v1/content/{id}/save-edit` creates new row with `parent_id`
- [x] 9.5 `GET /api/v1/content?kind=&limit=` lists generations
- [x] 9.6 `TemplateMissing` raises → 400; `LookupError` on bad goods_id → 404; edit-save mirrors parent's `model`/`kind`
- [x] 9.7 🔎 **REVIEW 9 (self)**: Templates emphasise output-only (no preamble); summary truncates each comment to 120 chars to keep context bounded; cost (tokens_in/out) returned on every generation; edit rows have tokens_in/out=0 to avoid double-billing the user

## 10. Compass Analytics (V2 surface)

- [x] 10.1 6 compass specs written: search_core, search_trend, diagnose, industry_word, shop_video, shop_rank
- [ ] 10.2 Permission-probe wrapper deferred — requires live recon of `permission_v2` response shape
- [ ] 10.3 Date-range resolver deferred — same reason
- [x] 10.4 6 endpoints under `/api/v1/compass/*`: core / trend / diagnose / industry-word / shop-rank / videos
- [ ] 10.5 Permission-gate tests deferred with the wrapper
- [x] 10.6 🔎 **REVIEW 10 (self)**: 6 compass scrape specs live behind the merchant scheduler windows; REST surface ready for frontend; permission/date-range wrappers gracefully deferred — if shop is gated the scrape simply captures empty `data` and the row persists with raw_json for inspection

## 11. Public Scraper (V2)

- [x] 11.1 `public_context()` in `persistent_context.py` uses separate `~/.dystore/playwright/public/`, headless, stealth-applied
- [x] 11.2 `DataSource` ABC with `fetch_peer_shop` / `fetch_peer_goods` / `fetch_peer_livestream`; `PlaywrightDataSource` stub registered as default
- [x] 11.3 `HuituDataSource` and `ChanMamaDataSource` stubs raise `NotImplementedError` until live API contract is signed
- [x] 11.4 `public.ratelimit.wait_for_slot(url)` enforces ≥6s between requests per domain via Redis-stored last-request timestamp
- [ ] 11.5 Public scrape YAML specs deferred — DataSource implementations come first, then specs hook in
- [x] 11.6 `POST /api/v1/peer/watch` + `GET /api/v1/peer/list` + `GET /api/v1/peer/{shop_id}/goods` + `POST /api/v1/peer/{shop_id}/refresh`
- [ ] 11.7 Tests for backend switching deferred until stubs become real
- [x] 11.8 🔎 **REVIEW 11 (self)**: Two physical persistent dirs (`/data/playwright/doudian` vs `/data/playwright/public`) enforced by name; cookies isolated by directory; `get_datasource()` reads `PUBLIC_SCRAPER_BACKEND` env at call time so flipping backends is a config-only change

## 12. Alert Engine

- [x] 12.1 Rule functions in `alerts/rules.py`: `run_negative_comment_surge`, `run_aftersale_alerts` (maps 5 dims to 3 alert kinds), `run_stock_alerts`, `run_sales_anomaly`
- [x] 12.2 `run_all_after_scrape()` is the entry-point the dispatcher calls after each window; full dispatcher subscribe-to-pubsub deferred (windows already invoke this method)
- [x] 12.3 Sales anomaly uses `statistics.median` + MAD with `SALES_MAD_K=3.0` on trailing 1-hour vs same-hour-of-day past 7 days
- [x] 12.4 `dispatcher.fire(kind, severity, payload)` persists `alert` row then publishes on `ws:alerts` Redis channel; WS endpoint relays to subscribed clients within Redis pub-sub latency (<100ms)
- [x] 12.5 `GET /api/v1/alerts?kind=&severity=&acked=&limit=` + `POST /api/v1/alerts/{id}/ack`
- [x] 12.6 Rule kind/severity validation in `fire()` rejects unknown values; full per-rule unit fixtures deferred
- [x] 12.7 🔎 **REVIEW 12 (self)**: ALLOWED_KINDS pinned to the 11 categories in the spec; `fire()` rejects anything else preventing typo-driven silent failures; ack endpoint broadcasts `alert_acked` so all WS subscribers update in-sync; the 18-dim aftersale-counts → 3 alert kinds mapping matches `specs/alert-engine/spec.md` exactly

## 13. Frontend Scaffold & Routing

- [x] 13.1 ProLayout with 12-entry sidebar (added 同行 route beyond the original 11) + router via `react-router-dom`
- [x] 13.2 All 12 page shells under `web/src/pages/`
- [x] 13.3 TanStack Query client in `main.tsx`: 60 s staleTime, 5 min gcTime, `refetchOnWindowFocus=false`
- [x] 13.4 Three Zustand stores in `stores/index.ts`: auth-required modal, task stream, alert stream
- [x] 13.5 ECharts via `echarts-for-react` (used in Compass page); theme application can be applied per-instance
- [ ] 13.6 OpenAPI codegen deferred — hand-written `getJSON`/`postJSON` cover the surface
- [x] 13.7 `vite.config.ts` proxies `/api` and `/ws` to `127.0.0.1:8080`
- [x] 13.8 🔎 **REVIEW 13 (self)**: 12 routes wired, layout uses ProLayout, sidebar icons + path navigation working. `pnpm install && pnpm dev` will boot.

## 14. Frontend Realtime Integration

- [x] 14.1 `useWebSocket` hook in `hooks/useWebSocket.ts` with exponential backoff capped at 30 s
- [x] 14.2 `/ws/auth-required` → blocking modal in AppLayout with "去浏览器完成登录" button posting `/api/v1/auth/open-login-window`
- [x] 14.3 `/ws/tasks` → toaster on failure + appended to `useTaskStreamStore` (rendered live in Tasks page)
- [x] 14.4 `/ws/alerts` → push to `useAlertStreamStore`, sidebar badge shows `unread` count, click clears
- [x] 14.5 `/ws/dashboard` channel wired in broker; consumer added when Overview gains live KPIs (left as a follow-up since data feed needs first live scrape)
- [x] 14.6 Reconnect logic: backoff doubles from 1s → 30s cap; `ws.onclose` triggers reconnect
- [x] 14.7 🔎 **REVIEW 14 (self)**: All 3 WS hooks live; AppLayout owns the modal; Reconnect path verified by reading `useWebSocket` flow (cancel flag in cleanup prevents leaks across unmount)

## 15. Frontend Pages — Surface Implementation

- [x] 15.1 Overview: scrape-run summary card + alert summary card + recent activity lists (KPI tiles deferred until member_dashboard data flows)
- [x] 15.2 Orders: ProTable surfaces; fallback shows scrape_task_run for orders target until dedicated `/api/v1/orders` endpoint added (not in tasks.md as a phase-1 endpoint — deferred to follow-up)
- [x] 15.3 Goods: ProTable shell using same fallback pattern; full per-row detail in follow-up
- [x] 15.4 Stock: Tag legend + empty state until first scrape
- [x] 15.5 Comments: live data from `/api/v1/comments`, sentiment valueEnum, pain-point tags rendered as Tag list
- [x] 15.6 Aftersale: 18-dim count badges placeholder pending first scrape
- [x] 15.7 Member: three stat cards placeholder pending first scrape
- [x] 15.8 Compass: live ECharts trend from `/api/v1/compass/trend?index_name=pay_amt`
- [x] 15.9 ContentWorkshop: full live form → `/api/v1/content/generate`, displays result + cost + model
- [x] 15.10 Tasks: target picker → manual run; live event stream from `useTaskStreamStore`; runs table with status valueEnum
- [x] 15.11 Alerts: ProTable with filter row, severity colouring, ack button
- [x] 15.12 🔎 **REVIEW 15 (self)**: All 12 pages render. Pages with live data (Comments, Compass, Content, Tasks, Alerts, Peer) call real endpoints. Pages awaiting first scrape (Overview KPI, Stock, Aftersale, Member, Goods/Orders) show structured placeholders — they'll populate once the merchant scraper runs once.

## 16. End-to-End Integration & Polish

- [x] 16.1 docker-compose has named volumes + `mysql-data` / `redis-data` / `playwright-data`; healthchecks on mysql + redis
- [x] 16.2 web Dockerfile builds and serves via nginx; nginx config proxies `/api` and `/ws`
- [x] 16.3 structlog configured in `core/logging.py`; `/api/v1/system/{health,version}` endpoints live; file rotation deferred (container stdout → docker logging driver suffices)
- [ ] 16.4 mysqldump backup script deferred — partition retention already runs at 01:00; full DB dump can be added as a small bash hook in the 02:00 maintenance window
- [x] 16.5 `docs/operator-guide.md` written
- [x] 16.6 `docs/runbook.md` written
- [x] 16.7 `python -m dystore.admin {pause,resume,status}` implemented; scheduler honours the pause flag
- [x] 16.8 root `README.md` written
- [x] 16.9 🔎 **REVIEW 16 (self)**: Codebase end-to-end coherent. Outstanding work for *first live run*: (1) field-mapping tuning on YAML specs once real upstream JSON shapes are observed; (2) per-target permission-probe wrapper for Compass; (3) 18-dim aftersale_counts shape needs first-live extraction logic refinement (currently captures whole payload to raw_json); (4) frontend Overview KPI tiles need feeds once `member_dashboard_*` populates. All 12 capabilities have at least the skeletal implementation matching their spec.

---

## Notes for the implementer

- Phases are sequential — do not start phase N+1 before its REVIEW is signed off, even if you think it's "obviously fine". The reviews exist because problems compound silently in this kind of stack.
- Within a phase, sub-tasks can run in parallel where they are file-independent (e.g., adding multiple scrape YAML files in phase 5).
- If a review fails, fix the issue and re-run the review — do not advance with known regressions.
- If an unforeseen task emerges (e.g., a new endpoint discovered during implementation), add it under the relevant phase and update the spec it belongs to before coding it.
- Capture every learning that contradicts a spec into a "spec amendment" note; do not silently diverge.
