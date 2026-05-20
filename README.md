# dystoretools

Single-user, single-machine desktop tool for 抖店 (Douyin merchant) operators. Scrapes the merchant's own backend via Playwright (no official API needed) → MySQL → React dashboard with AI-driven comment analysis and content generation.

## Quickstart

```bash
git clone <repo-url>
cd dystoretools
cp .env.example .env       # set MYSQL_PASSWORD + DEEPSEEK_API_KEY
make up                    # docker compose up
make migrate               # alembic upgrade head
open http://127.0.0.1:5173
```

When the dashboard pops the "需要登录抖店" modal, click **去浏览器完成登录** — a visible Chrome window opens for one-time login.

Full operator guide: [`docs/operator-guide.md`](docs/operator-guide.md). Troubleshooting: [`docs/runbook.md`](docs/runbook.md).

## Architecture

```
React + AntD Pro  ──HTTPS/WS──▶  FastAPI  ──┬──▶  Playwright (logged-in Chrome)  ──▶  fxg.jinritemai.com
                                            ├──▶  APScheduler (9 daily windows)
                                            ├──▶  LLM gateway (DeepSeek V4 Pro)
                                            └──▶  MySQL + Redis
```

- **Scraping**: response-interceptor pattern (no signing reverse-engineering — we never call `httpx` against `fxg.jinritemai.com`).
- **Storage**: MySQL 8 (utf8mb4) with monthly partitions on time-series tables; Redis for cookies, WS pub-sub, rate limits.
- **AI**: DeepSeek V4 Pro primary (1M context), Kimi as resilience fallback.
- **Realtime**: WebSocket channels `/ws/{auth-required,tasks,alerts,dashboard}`.

## Project layout

```
.
├── AGENT.md                  # AI-agent orientation (read first)
├── README.md                 # you are here
├── docs/
│   ├── requirements.md       # consolidated product scope
│   ├── api-catalog.md        # ~70 confirmed endpoints from recon
│   ├── menu-map.md           # 57-module 抖店 menu inventory
│   ├── scraping-patterns.md  # signing-constraint + interceptor design
│   ├── operator-guide.md
│   └── runbook.md
├── backend/                  # Python 3.12 · FastAPI · SQLAlchemy 2.0 async · Playwright
│   └── dystore/{auth,scraper,scheduler,llm,analysis,content,alerts,api,ws,db,cache,core}/
├── web/                      # React 18 · Vite · TypeScript · Ant Design Pro · ECharts
│   └── src/{layouts,pages,hooks,stores,api}/
├── openspec/                 # OpenSpec change proposals (bootstrap-merchant-platform)
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Constraints

This codebase has 7 hard constraints — see [`AGENT.md`](AGENT.md) §4. The most important:

1. **No official 抖店 Open API.** Application requires a business license we don't have.
2. **No httpx replay of `fxg.jinritemai.com/api/*`.** Per-request `a_bogus` signature makes that infeasible. Drive a real browser.
3. **No OpenClaw / AI gateway abstraction layer.** The source PDFs propose one; we explicitly do not.
4. **Single tenant. Single user. No RBAC.**

## License

Internal / single-user.
