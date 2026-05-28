## Why

The customer is a 抖店 (Douyin) merchant who needs automated operations analysis and AI-assisted content generation without the friction of applying for the official 抖店 Open API (requires a business-license qualification they do not have). Today they manually browse the merchant backend (`fxg.jinritemai.com`) and copy data into spreadsheets — slow, error-prone, and never feeds AI for content generation or comment analysis. This change bootstraps the entire `dystoretools` platform: a single-user, single-machine tool that scrapes the merchant backend via a logged-in Playwright session, persists data in MySQL, and exposes a React dashboard with WebSocket realtime updates and LLM-driven analysis.

## What Changes

- Scaffold the greenfield project: Python 3.12 / FastAPI backend, React 18 + Ant Design Pro frontend, MySQL 8 + Redis 7 datastores, Docker Compose packaging.
- Implement Playwright-based **MerchantScraper** that drives the merchant's logged-in browser session and intercepts JSON responses (no direct API replay — the `a_bogus` per-request signature makes that infeasible).
- Implement **PublicScraper** (V2) for anonymous peer-monitoring and 抖音公开页 抓取, physically isolated from MerchantScraper (separate user-data-dir, no shared cookies/IPs).
- Declarative YAML scrape-target specs (one file per target — no per-page Python class).
- 9-window daily APScheduler matching the operations rhythm captured in source PDF2 (no 00:00–06:00 merchant-backend access — risk control).
- Persistent Chromium context for session reuse; visible-window auto-recovery when the platform surfaces a risk-verification challenge (email OTP, etc.).
- LLM gateway with provider switching (DeepSeek primary / Kimi backup) via thin REST wrappers — no LangChain.
- AI analysis pipelines: comment sentiment + pain-point clustering, cross-product negative-comment trends, content-generation (titles / details / livestream scripts / short-video scripts) drawing on stored shop data.
- Realtime WebSocket channels: `/ws/dashboard`, `/ws/tasks`, `/ws/alerts`, `/ws/auth-required`.
- Alert engine consuming the platform's native signals (18-dim aftersale counts, `commentIndexWarning`, low-stock signals from `sku_stock_diagnose`) plus our own anomaly detection on time-series.
- Dashboard surfaces consuming the platform-computed 罗盘 (Compass) analytics endpoints directly — avoids re-aggregating what bytedance already computed.
- **BREAKING (project-level)**: Replaces the OpenClaw orchestration approach proposed in the source PDFs with a direct FastAPI service.
- **Excluded from this change**: official 抖店 Open API path, 千川/云图 integration, RAG / vector store, 飞鸽 IM auto-reply, multi-tenancy/RBAC.

## Capabilities

### New Capabilities

- `merchant-auth`: Persistent Playwright Chromium profile, manual one-time login (email + password + OTP if challenged), session-expiry detection, visible-window re-auth flow surfaced via WebSocket.
- `merchant-scraper`: Declarative YAML target specs, response-interceptor scrape engine, anti-detection (real Chrome channel, stealth plugin, human-like timing, single concurrency per domain, no 0–6am).
- `public-scraper`: V2-only anonymous scraper for peer shops and 抖音公开页. Separate user-data-dir + headless + cookie pool. Pluggable 3rd-party API fallback (灰豚/蝉妈妈) behind a `DataSource` interface.
- `scrape-scheduler`: APScheduler with 9 cron windows mirroring source PDF2. Task lifecycle (queued / running / done / failed) persisted to `scrape_task_run` and broadcast to `/ws/tasks`.
- `data-storage`: MySQL 8 schema (~30 tables across 7 domains) via SQLAlchemy 2.0 async + Alembic; Redis 7 for cookie/session, task queue, WS pub-sub, rate-limit counters; time-series tables partitioned by `scraped_at` month.
- `llm-gateway`: Thin async REST wrapper with provider routing (DeepSeek default, Kimi for long-context), per-call accounting to `ai_generation`, PII scrubbing before prompt assembly.
- `comment-analysis`: AI worker consuming `doudian_comment`; produces `sentiment`, `pain_points_json`, cross-product clustering, longitudinal pain-point trends; differentiated from platform-native GPT-reply (we do clustering and time-series — platform does single-reply).
- `content-generation`: LLM-driven titles, product details, livestream scripts, short-video scripts; outputs saved to `ai_generation`; UI surface for prompt templates and post-edit.
- `member-insights`: Ingests the three `member_dashboard/v2/*` endpoints + `user_profile/get_audience_feature` into `member_dashboard_*` and `audience_feature` tables; renders the member dashboard.
- `compass-analytics`: Ingests `/compass_api/*` (search core data + trend + diagnosis + industry-word rank + shop-video list) into `compass_*` tables; renders search-ops analytics page. V2 scope; relies on data that is platform-pre-aggregated.
- `alert-engine`: Subscribes to fresh scrape arrivals; emits typed alerts (negative-comment surge, low/dead stock, aftersale-deadline-approaching across 18 dims, 销量异动, 违规通知) to `alert` and broadcasts on `/ws/alerts`.
- `realtime-dashboard`: React 18 + Vite + TypeScript + Ant Design Pro SPA. Pages: 总览 · 订单 · 商品 · 库存 · 评论 · 售后 · 用户 · 罗盘 · 文案工坊 · 任务 · 告警. WebSocket clients for each realtime channel; React Query for server cache, Zustand for local state. ECharts for visualisation.

### Modified Capabilities

(none — greenfield project; `openspec/specs/` is empty)

## Impact

- **Code**: Entire greenfield codebase. Two packages introduced: `backend/dystore/*` (Python) and `web/` (TypeScript). Infrastructure via `docker-compose.yml` at repo root.
- **Storage**: New local MySQL 8 instance (~5 GB after 1 year at observed shop volume); new local Redis 7 instance (<200 MB working set).
- **External dependencies**: Playwright (Chromium via installed Chrome `channel="chrome"`), `playwright-stealth`, SQLAlchemy 2.0, Alembic, FastAPI, Uvicorn, APScheduler, httpx, pydantic v2, React 18, Vite, Ant Design Pro, ECharts. LLM APIs: DeepSeek and Kimi.
- **Account / risk surface**: Uses the merchant's real 抖店 account. The platform's risk engine *may* flag the shop if anti-detection rules in `docs/scraping-patterns.md` §7 are violated. Mitigation is part of `merchant-scraper` spec.
- **Operational footprint**: Single Docker Compose deployment on the user's machine (4 services: mysql, redis, api, web). No external infra. Sessions live in `~/.dystore/playwright/`; secrets in `.env` (gitignored).
- **Out-of-scope follow-ups (V3 candidates)**: 千川后台 (qianchuan.jinritemai.com), 云图 (yuntu.oceanengine.com), RAG / vector store, IM auto-reply, mobile companion app, multi-shop support.
