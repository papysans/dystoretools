# AGENT.md — dystoretools

> Single-source-of-truth orientation file for any AI agent (Claude, Codex, Cursor, Gemini, etc.) working on this codebase.
> Read this first. Read [`docs/requirements.md`](docs/requirements.md) and [`docs/scraping-patterns.md`](docs/scraping-patterns.md) second.

---

## 1 · What this is

A **single-user, single-machine desktop tool** for a 抖店 (Douyin merchant) backend operator. It:

- Scrapes the merchant's own backend at `https://fxg.jinritemai.com/` using **Playwright with the merchant's logged-in browser session** (no official API)
- Persists orders / products / inventory / comments / IM into a local **MySQL** database
- Exposes a **React + Ant Design Pro** dashboard backed by **FastAPI**, with real-time updates over **WebSocket**
- Calls cloud LLMs (DeepSeek primary, Kimi backup) for comment analysis, content generation (titles / details / livestream scripts), and operational suggestions
- Runs 9 scheduled task windows daily mirroring the merchant operations rhythm captured in the source PDFs

It is **not** a SaaS, not multi-tenant, not a marketplace product. One person, one machine, their own shop.

---

## 2 · Status

**Greenfield · specification phase.** No application code exists yet.

| Asset | Location | Purpose |
|-------|----------|---------|
| Source customer materials | `*.pdf` in repo root | 5 dialog exports from 豆包 capturing original intent. **All references to OpenClaw must be ignored.** |
| Consolidated requirements | [`docs/requirements.md`](docs/requirements.md) | The authoritative product scope after reconciliation |
| Scraper engineering notes | [`docs/scraping-patterns.md`](docs/scraping-patterns.md) | Empirical findings from a live recon session against fxg.jinritemai.com |
| OpenSpec workspace | `openspec/` | Will hold formal `proposal.md` / `design.md` / `tasks.md` / `specs/` after V1 spec is approved |
| Playwright recon artefacts | `.playwright-mcp/` , `homepage.png`, `login-page.png`, `homepage-snapshot.yml` | Read-only evidence from the recon session; do not depend on these at runtime |

---

## 3 · Tech stack (locked)

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend framework | **FastAPI** 0.115+ on **Uvicorn** | Single async process |
| Backend language | **Python 3.12** | |
| ORM | **SQLAlchemy 2.0** async | No raw SQL outside Alembic migrations |
| Scraper | **Playwright (async)** with persistent context | Response-interceptor pattern, **not** direct API replay |
| Anti-detection | `playwright-stealth` · randomized UA · cookie jar in Redis | |
| Scheduler | **APScheduler** in-process | Celery / RQ deferred until needed |
| Relational DB | **MySQL 8** | UTF-8 (utf8mb4) |
| Cache / queue / pub-sub | **Redis 7** | |
| LLM gateway | Thin Python wrapper around **DeepSeek** + **Kimi** REST APIs | No LangChain, no LlamaIndex |
| Vector store | **None** in V1+V2 (RAG explicitly deferred to V3) | |
| Frontend framework | **React 18** + **Vite** + **TypeScript** | |
| Frontend UI kit | **Ant Design Pro** | B-end admin scaffolding |
| Charts | **ECharts** (or AntV G2Plot for some surfaces) | |
| Realtime | **FastAPI WebSocket** | Channels: `/ws/dashboard`, `/ws/tasks`, `/ws/alerts`, `/ws/auth-required` |
| Packaging | **Docker Compose**: `mysql`, `redis`, `api`, `web` | No Kubernetes |
| Secrets | `.env` file (gitignored) | No secret manager in V1+V2 |

---

## 4 · Hard constraints — read before writing code

1. **No official 抖店 Open API.** Application requires business-license qualification we don't have. All merchant-side data must come from Playwright-driven session scraping.
2. **No OpenClaw, no AI gateway abstraction layer.** The source PDFs describe an OpenClaw-mediated architecture; that is the *rejected* approach. Build the FastAPI service directly.
3. **No direct HTTP replay of fxg.jinritemai.com endpoints.** Every request requires a per-request `a_bogus` signature produced by obfuscated bytedance JavaScript. Direct `httpx.post(...)` returns 403. See `docs/scraping-patterns.md` §3.
4. **No multi-tenant code paths.** No tenant_id columns, no RBAC, no per-account session pools. One account, one machine.
5. **No RAG, no vector DB, no embeddings.** Deferred to V3.
6. **No auto-reply IM bot.** The PDFs propose automating 飞鸽 (merchant IM) replies — that is `Out of scope`. AI generates reply *drafts*; the human pastes them.
7. **No compliance gating.** The user has accepted the operational risk of scraping their own merchant backend. Do not insert `if not user.has_consent(...)` checks.

---

## 5 · Domain quick reference

**Origin domains**
- Merchant backend: `https://fxg.jinritemai.com/`
- Login: `https://fxg.jinritemai.com/login/common`
- IM (飞鸽): `https://im.jinritemai.com/` (V2)
- Long-gateway: `https://lgw.jinritemai.com/api/v2/agw/...`

**Confirmed endpoints (from recon — base `https://fxg.jinritemai.com`)**

The full empirical catalogue (~70 endpoints across 7 modules) lives in [`docs/api-catalog.md`](docs/api-catalog.md). The merchant backend's full 57-module menu lives in [`docs/menu-map.md`](docs/menu-map.md). Headline P0 endpoints:

| Capability | Endpoint | Method |
|------------|----------|--------|
| Order list | `/api/order/searchlist` | GET |
| Product list | `/product/tproduct/list` | GET |
| Stock list + SKU diagnose | `/stock/manage/list` · `/stock/manage/sku_stock_diagnose` | POST |
| Comments (all + negative) | `/product/tcomment/commentList` · `…/getUnreplyNegativeCommentList` | GET |
| Aftersale list + 18-dim counts | `/after_sale/pc/list` · `/shopuser/aftersale/counts` | POST · GET |
| Member dashboard (agg / daily / hist) | `/api/member/dashboard/v2/get_shop_dashboard_*` | POST |
| Compass search core + trend | `/compass_api/.../search_analysis/core_data` · `…/core_data_trend_v2` | GET |
| IM unread | `/api/scale_shop/doudian_im/shop/user/unread_count` | GET |
| Session heartbeat | `/ecomauth/loginv1/session_check` | GET |

**Shop identity discovered during recon**: `shop_id = 29867003`, application `aid = 4272` (stable per app). Stored in `.env` only.

**Required request parameters on every call** (see `docs/scraping-patterns.md` for handling strategy)
- `appid` (static: `1`)
- `__token` (stable per login session)
- `_bid` (page biz id, e.g. `ffa_order`, `ffa_menu`)
- `aid` (application id, e.g. `4272`)
- `_lid` (unique per request — log id)
- `msToken` (refreshing opaque token)
- `a_bogus` (per-request bytedance signature)
- `verifyFp` and `fp` (browser fingerprint, stable per session)

---

## 6 · Coding conventions (apply once implementation lands)

- **One language per layer.** Backend = Python. Frontend = TypeScript. No mixed-language services, no Node-in-Python or Python-in-Node bridges.
- **Comments**: write none by default. Only add a one-line WHY comment when the code embeds a non-obvious constraint, workaround, or invariant. Never write what the code does — names should do that.
- **Async everywhere.** No `requests.get(...)`, no `time.sleep(...)` in handlers. Use `httpx.AsyncClient`, `asyncio.sleep`.
- **No premature abstractions.** Three similar lines is fine. Don't introduce a base class until the second concrete subclass exists.
- **Scraper targets are declarative YAML** (see `docs/scraping-patterns.md` §5), not bespoke Python classes per page.
- **All credentials and tokens live in `.env`** plus Redis (encrypted at rest by file-system permissions, not application-level crypto in V1).
- **Migrations only via Alembic.** No `Base.metadata.create_all()` in production paths.
- **Frontend state**: React Query for server cache + Zustand for local UI state. No Redux unless we hit a wall.

---

## 7 · Commands

```bash
# (to be defined when scaffold lands)
# Local dev:        docker compose up
# Run scraper once: python -m dystore.scraper.run --target=order_list
# Frontend dev:     pnpm --filter web dev
# Tests:            pytest -q     (backend)
#                   pnpm --filter web test  (frontend)
```

This section is intentionally a stub. Update it the moment the scaffold lands.

---

## 8 · When you are about to do something risky

The user has explicitly authorized:
- Scraping the merchant backend with their session
- Storing their merchant credentials locally
- Bypassing the official API path

The user has **not** authorized:
- Pushing code to any remote
- Running anything against third-party shops without an explicit follow-up directive
- Calling LLMs with PII in the prompt without scrubbing customer names / phone numbers / addresses first

When in doubt: ask in chat, do not act.
