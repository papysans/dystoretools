## Context

`dystoretools` is a greenfield single-user desktop tool for a 抖店 (Douyin) merchant operator. The customer has a verified merchant account on `fxg.jinritemai.com` but **no business-license qualification**, which blocks them from the official 抖店 Open API. The source materials (5 PDF dialogs with 豆包) proposed an OpenClaw orchestration architecture; that approach was rejected by the user. Instead we own the entire stack: a FastAPI service with a Playwright scraper that drives the merchant's own logged-in session.

A 2026-05-18 recon session (see `docs/api-catalog.md`, `docs/menu-map.md`, `docs/scraping-patterns.md`) established four load-bearing constraints that shape every decision below:

1. **Every `fxg.jinritemai.com/api/*` request carries a per-request `a_bogus` signature** computed by obfuscated bytedance JavaScript. Direct `httpx` replay returns 403. Therefore the scraper must drive a real browser and intercept responses — not replay requests.
2. **First login from a new fingerprint triggers email-OTP risk verification.** Persistent context across runs is mandatory; re-login must surface to the human, not be retried programmatically.
3. **Platform-native analytics (罗盘 / Compass) already pre-aggregate** search-ops, diagnosis, optimization suggestions, industry-word rankings, and shop-video stats. We ingest those endpoints directly rather than recomputing.
4. **The platform also ships its own GPT-reply / comment-hosting / AI智能成片 features.** Our AI value-add must be *differentiated*: cross-product clustering, longitudinal pain-point trends, multi-source comprehensive analysis — not single-comment reply generation.

## Goals / Non-Goals

**Goals:**
- Stand up a working V1+V2 (combined) end-to-end on the user's machine via `docker compose up`.
- Replicate the 9-window operational rhythm of the merchant's existing manual workflow (PDF2) inside an APScheduler.
- Provide a single React dashboard that surfaces orders / products / inventory / comments / aftersale / member analytics / compass analytics / content workshop / task monitor / alert center, with WebSocket realtime updates.
- Provide AI value the platform doesn't: cross-product comment clustering, longitudinal pain-point trend, multi-format content generation drawing on shop-specific data.
- Keep the merchant account safe through enforced anti-detection rules (real Chrome channel, stealth, human pacing, no 0–6am, single concurrency per domain).

**Non-Goals:**
- Official 抖店 Open API integration. Ever.
- 千川 / 云图 backends — deferred to V3.
- RAG / vector store — deferred to V3 (user direction).
- 飞鸽 IM auto-reply — removed for risk reasons.
- Multi-tenancy, RBAC, multi-shop, hosted SaaS, mobile app.
- Re-implementing the `a_bogus` signing algorithm.
- General-purpose abstraction layers (no plugin system, no AI gateway abstraction beyond the thin LLM provider switch).

## Decisions

### Backend language: Python 3.12 over Node.js / Go / Java
Python wins because the project is data-/AI-heavy: Playwright has a mature async Python binding, pandas remains the de-facto data manipulation toolkit, and LLM provider SDKs (DeepSeek, Kimi) ship Python-first. Node would share a language with the frontend but its async-long-task ergonomics are worse for the scraper. Go would beat Python on raw throughput but loses on LLM/data ecosystem; this tool's bottleneck is browser-driving wall-clock time, not CPU.

### Scraping mechanism: Playwright response interceptor over httpx replay or sign-reverse-engineering
**Chosen:** Drive `chromium.launch_persistent_context` with installed Chrome (`channel="chrome"`), navigate to target pages, intercept JSON responses via `page.on("response", …)`.

**Rejected:** (a) httpx replay with stolen cookies — fails on `a_bogus` integrity check. (b) reverse-engineering the sign algorithm — bytedance rotates the algorithm roughly quarterly; ongoing maintenance burden is unbounded.

**Consequence:** scrape throughput is bounded by browser navigation (~1 page per 5–10s with human-like delays). For the single-shop, single-user case this is well within requirements.

### Scrape spec format: declarative YAML over per-target Python classes
Each scrape target is a YAML file under `backend/dystore/scraper/specs/`. Format includes: `nav` (URL + wait conditions), `intercept` (URL pattern + method), `extract` (jsonpath + field map), `sink` (table + upsert key + `store_raw: true`), `schedule` (cron). Adding a target = adding a file. Custom interactions (clicks, scrolls) declared as `pre_actions`.

Rejected: a class hierarchy per target. With ~30 targets between V1 and V2, the boilerplate-to-logic ratio would be terrible.

### Scheduler: APScheduler in-process over Celery / RQ
APScheduler suffices for single-machine + ~30 cron jobs. Celery adds a worker process, broker semantics, and result-backend complexity that buys nothing for a single user. Reconsider only if the scrape volume grows past one machine's tolerance (not a V1+V2 concern).

### Database: MySQL 8 (utf8mb4) + Redis 7
MySQL was specified in source PDF3 (with concrete schema). We keep it as it preserves continuity for the user's existing mental model and because their schema mostly survives. Postgres + JSONB would be marginally nicer for `raw_json` workloads but the gain doesn't justify the migration cost. Redis serves four roles: cookie/token store, APScheduler job state, WebSocket pub-sub fan-out, rate-limit counters.

### Frontend: React 18 + Vite + TS + Ant Design Pro
Ant Design Pro is explicitly designed for B-end Chinese admin dashboards — table density, filter ergonomics, China-locale defaults, mature ECharts integration. Vue 3 + Naive UI is a viable alternative but the React ecosystem has thicker offerings for chart-heavy SPAs. **Recharts is explicitly rejected** — it tanks on dataset sizes the merchant will see.

### LLM gateway: direct REST + thin Python wrapper over LangChain
LangChain abstractions invert control, change semantics across minor versions, and complicate debugging. We need three things only: provider routing (DeepSeek default, Kimi for long-context), per-call accounting to `ai_generation`, and PII scrubbing (customer phone / address / nickname / ID) before prompt assembly. A 200-line wrapper delivers all of these.

### Browser channel: installed Chrome over bundled Chromium
Bytedance risk engines score real Chrome significantly better than headless Chromium. We require Chrome installed on the user's machine and pass `channel="chrome"` to Playwright.

### Process model: single FastAPI process, multi-coroutine
One uvicorn worker hosts REST + WebSocket + APScheduler + AI workers + scraper sessions. Lower deployment complexity. The CPU cost is negligible (browser does the heavy work); concurrency limits live in code, not in process count.

### Concurrency cap: at most one merchant-domain scrape at a time
Two concurrent scrapes from the same account against `fxg.jinritemai.com` is the highest-leverage anomaly the risk engine looks for. The scheduler queues merchant tasks through a single asyncio lock per (account, domain) tuple.

### Time windows: 9 cron slots from PDF2, hard 00:00–06:00 block
Cron schedule: `00:10`, `01:00`, `07:30`, `10:00`, `12:00`, `15:00`, `18:00`, `21:30`, `02:00`. The `01:00` and `02:00` windows touch only local DB (archive, backup); no `fxg.*` traffic between midnight and 06:30 — strongest single anti-detection lever.

### Auth recovery: visible-window manual flow over headless retry
When the scraper detects a redirect to `/login/common`, it (a) marks the session dead, (b) publishes `{"reason": "session_expired"}` to `/ws/auth-required`, (c) opens a visible Chromium window to the login page. The frontend prompts the user to complete login (+ any OTP) by hand. Scraper resumes when it next observes a non-login URL. No automated re-login.

### Native platform AI: coexist with differentiation, ingest where free
- 评价管理 already has `shop_comment_gpt_reply`, `shop_comment_summary`, `shop_comment_ask`. We **do not** offer single-comment GPT replies.
- We **do** offer (a) cross-product negative-comment clustering, (b) longitudinal pain-point trends, (c) shop-level comprehensive synthesis across orders + comments + aftersale + member data.
- Where platform AI outputs are exposed by an endpoint we already scrape (`/product/tcomment/commentIndexWarning`, etc.), we ingest them into our DB and surface them — free signal.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 抖店 风控 封禁商家账号 | Real Chrome + stealth + human pacing 3–10s + no 0–6am + single concurrency + persistent profile (don't clear cookies). All four rules enforced in `merchant-scraper` spec, not optional. |
| `a_bogus` 算法升级 → scraper 失效 | We never decode it. Interceptor pattern means the page always computes a valid signature before we read the response — algorithm changes are transparent to us. |
| 会话过期或风控验证频繁打断 | `/ws/auth-required` channel + visible-window flow makes re-auth a 30-second human action. Detection via both URL redirect AND `/ecomauth/loginv1/session_check` heartbeat. |
| 平台 UI 改版 → JSON shape 变化 | `raw_json` column on every scraped table preserves full upstream payload. Field mapping in YAML can be re-derived without re-scraping. |
| LLM 输出泄露客户 PII (手机/地址) | LLM gateway runs a PII-scrub pass before prompt assembly: customer nick, full address, phone, order_sn are replaced with placeholders. `ai_generation` never stores raw prompts containing customer data. |
| 单机磁盘填满 (1 年后 ~5 GB) | Monthly partitions on time-series tables (`compass_*`, `member_dashboard_*`, `aftersale_counts`); 1-year retention enforced by a nightly archive job. |
| 平台 AI 与我方 AI 重叠导致用户混淆 | UI labelling: 我方 AI 输出标注"由 dystoretools 分析"，仅在差异化能力上呈现（聚类/趋势/综合），不做单评论回复。 |
| Compass endpoints permission gates | Some `/compass_api/*` paths check `permission` / `gray_hit`. Spec requires the scraper to probe `permission_v2` before scraping a target and skip-with-log when unauthorized. |
| 千川/云图 V3 升级遇到二次登录 | Out of scope for this change. V3 will likely need a separate persistent-context dir per domain — design accommodates by namespacing user-data-dir paths. |

## Migration Plan

This is greenfield; "migration" is "initial bring-up":

1. **Day 1**: scaffold backend + frontend monorepo, install Docker, install Chrome, run `docker compose up`.
2. **Day 1**: alembic upgrade to head — creates all 30+ tables empty.
3. **Day 1**: user clicks "首次登录" in the frontend → visible Chromium opens to login page → user logs in (+ OTP) → session stored in `~/.dystore/playwright/doudian/`.
4. **Day 2–N**: scheduler runs windows; data flows in; dashboard populates incrementally.
5. **Rollback**: `docker compose down -v` removes everything; `~/.dystore/playwright/` may be kept (preserves login) or deleted (forces fresh login).

There is no production-vs-staging split. The user's machine *is* production.

## Open Questions

- **Compass permission gate behavior** — we don't yet know which `/compass_api/*` paths the user's shop level is gated out of. Resolve in V2 implementation by inspecting `permission_v2` per target.
- **Pagination tolerance** — at what page depth does `/api/order/searchlist` trigger additional risk checks? Empirical-tune during early production runs; default to backfill in small chunks (3 pages × 10 items × 10s gap).
- **Exact retention boundary for high-velocity tables** — `comment_tag_stat` may grow faster than 1y/manageable if the shop has many SKUs; revisit at the 6-month mark.
- **Whether to surface platform native AI outputs in our UI** — e.g., we can show `commentIndexWarning` text from the platform alongside our own analysis. Decide during dashboard polish; default is "yes, with platform-source attribution".
- **Mac vs Windows install** — Playwright + installed Chrome is well-supported on both, but the user's primary machine is Windows. We document Windows-first; Mac is best-effort.
