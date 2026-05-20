# Operator Guide — dystoretools

> Single-user, single-machine tool. This is your day-1 reference.

---

## First-time bring-up

1. **Install prerequisites** (one-off):
   - Docker Desktop (Windows / Mac)
   - Google Chrome (the real Chrome — Playwright will drive it via `channel="chrome"`)
2. **Clone and configure**:
   ```bash
   git clone <repo-url>
   cd dystoretools
   cp .env.example .env
   # Edit .env: set MYSQL_PASSWORD and DEEPSEEK_API_KEY (Kimi optional)
   ```
3. **Bring up the stack**:
   ```bash
   make up        # docker compose up -d
   make logs      # tail until "dystore.start" appears
   ```
4. **Run migrations**:
   ```bash
   make migrate
   ```
5. **Open the dashboard**: <http://127.0.0.1:5173>
6. **First login** — the dashboard will pop a modal "需要登录抖店". Click **去浏览器完成登录**.
   - A visible Chrome window opens at `https://fxg.jinritemai.com/login/common`.
   - Log in with your 抖店 email + password.
   - If the platform shows "安全验证", check your email for an OTP and enter it.
   - Once login completes, the modal closes automatically and scraping resumes.

The session is stored in the `playwright-data` Docker volume — you will not need to log in again for ~7–30 days.

---

## What happens daily

| Window | Purpose |
|--------|---------|
| 00:10 | Yesterday's full backfill + KPI roll-up |
| 01:00 | Local archive (no merchant traffic) |
| 02:00 | DB backup (no merchant traffic) |
| 07:30 | Morning increment (orders, aftersale, overnight comments, stock alerts) |
| 10:00 | Mid-morning increment |
| 12:00 | Noon: comment AI analysis batch + member dashboard ingest |
| 15:00 | Afternoon increment |
| 18:00 | Golden-hour: orders + Compass ingest |
| 21:30 | Evening: orders + comments + clustering + daily KPI report |

The 00:00–06:30 window is intentionally silent — bytedance's risk engine weights night-time automation heavily.

---

## When the modal pops

| Reason text | What to do |
|-------------|------------|
| `session_required` | Click the button; complete login in the popped browser |
| `risk_verification_required` | Same path — also enter the email OTP if asked |
| `session_expired` | Same — your previous session expired (typically after 7–30 days) |

If you ignore the modal, scrapers will pause; once you complete login they resume on the next scheduled window automatically.

---

## Emergency kill switch

If you suspect the risk engine is reacting to our traffic and want to halt all scrapers immediately:
```bash
docker compose exec api python -m dystore.admin pause
# inspect logs, fix issue, then:
docker compose exec api python -m dystore.admin resume
```

The pause flag is honoured by every cron window. Manual runs through the UI's 任务 page also respect it.

---

## Where things live

| Thing | Location |
|-------|----------|
| Logs | `docker compose logs -f api` |
| MySQL data | Docker volume `dystore_mysql-data` |
| Redis data | Docker volume `dystore_redis-data` |
| Playwright profile + cookies | Docker volume `dystore_playwright-data` → mounted at `/data/playwright/doudian` |
| DB backups | `./backups/` |
| Application code | `./backend/` and `./web/` |
| Customer requirements | `./docs/requirements.md` |
| Spec changes | `./openspec/changes/` |
| Source PDFs | `./*.pdf` (reference only) |

---

## Common surfaces

- **Comments page**: see auto-classified sentiment + pain-point tags after the 12:00 window runs.
- **罗盘 page**: line chart from Compass once 12:00/18:00 ingests run.
- **文案工坊**: choose a content kind, paste a goods_id (from the 商品 page), generate, edit, save.
- **任务 page**: live event stream + manual-run for any scrape target.
- **告警 page**: confirm an alert to de-emphasise it. Acknowledgements broadcast to all open tabs.
# AI chat console setup

The chat SQL sandbox uses a separate MySQL account. Set these values in `.env`:

```env
CHAT_MASTER_ENCRYPTION_KEY=<base64 32-byte key>
MYSQL_CHAT_READONLY_USER=chat_readonly
MYSQL_CHAT_READONLY_PASSWORD=<strong password>
```

Generate the encryption key with:

```powershell
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

Create or rotate the readonly MySQL user by editing `backend/scripts/create_chat_readonly_user.sql`, replacing `CHANGE_ME_STRONG_PASSWORD`, then running it as a MySQL administrator. The user is granted `SELECT` only on scraped business-data tables. It is not granted access to provider credentials, chat history, app settings, Alembic metadata, session events, or other control tables.

After migration, open `设置 -> 模型与 Provider` to add or edit DeepSeek, Kimi, OpenAI, Anthropic, or any OpenAI-compatible endpoint. Existing DeepSeek/Kimi settings remain usable as fallback, but new chat conversations use the provider/model registry and the selected default chat model.

The AI assistant page is available at `/chat`. It stores conversations in MySQL, streams assistant output over SSE, and executes SQL only through the readonly sandbox. SQL results are split into two channels: masked rows for the LLM and original rows for the local UI.
