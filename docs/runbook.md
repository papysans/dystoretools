# Runbook — dystoretools

> When something is wrong, start here. Each section: symptom → diagnosis → action.

---

## Scraper appears stuck

**Symptom**: 任务 page shows no new runs in the last hour, or runs stay `running` forever.

**Diagnosis**:
```bash
docker compose logs api --tail=200 | grep scheduler
docker compose logs api --tail=200 | grep scraper
docker compose exec api python -m dystore.admin status
```

Common causes:
1. **Admin pause was set** — output above shows `paused`. Resume with `python -m dystore.admin resume`.
2. **Session expired silently** — look for `session_expired` events. Open the dashboard; if the modal is up, complete login.
3. **Chrome not installed on the host machine** — the `Dockerfile` uses the Playwright base image so this should not happen *inside the container*, but if you switched to local dev, install Chrome.
4. **MySQL connection lost** — `make logs` shows `mysql` container restart loops; recover with `docker compose restart mysql`, then `api`.

---

## Alerts not arriving

**Symptom**: 告警 page is empty even though you can see negative comments / pending aftersales in the data.

**Diagnosis**:
- The dispatcher runs after each scrape window. If scrapes are not completing (see above), alerts won't fire.
- Inspect the `alert` table directly:
  ```bash
  docker compose exec mysql mysql -u dystore -p${MYSQL_PASSWORD} dystore -e "SELECT kind, severity, dispatched_at FROM alert ORDER BY id DESC LIMIT 20;"
  ```

If the table has rows but the page is empty, the issue is in the WebSocket pipe:
- Reload the page (the React Query cache also re-fetches).
- Check the browser console for WS errors.

---

## Frontend can't connect

**Symptom**: Dashboard shows "Network Error" or pages don't load.

**Diagnosis**:
1. Verify `api` container is up: `docker compose ps`.
2. Verify nginx is proxying: open <http://127.0.0.1:5173/api/v1/system/health>; should return `{"status":"ok"}`.
3. If running `pnpm dev` directly (no nginx), confirm `VITE_API_TARGET` in `.env` points to `http://127.0.0.1:8080`.

---

## Account flagged for risk

**Symptom**: Login page now requires more verification than before (face scan / phone call / `请稍后再试`); or you see a banner inside 抖店 backend warning about suspicious activity.

**Immediate action**:
1. **Pause scrapers**: `docker compose exec api python -m dystore.admin pause`.
2. **Manually log in via your normal browser** (not via dystoretools) and do nothing automated for 24–48 hours.
3. **Reduce frequency**: edit a few critical scrape spec YAML files and double the cron interval before resuming. Example: change `"10 0,7,10,12,15,18,21 * * *"` → `"10 0,7,12,18,21 * * *"`.
4. When resuming, set `python -m dystore.admin resume` and watch logs for the first hour.

**Long-term**: if flagging recurs, switch the most aggressive targets to the third-party data backend:
```bash
# In .env
PUBLIC_SCRAPER_BACKEND=huitu      # requires HUITU_API_KEY
```

---

## Database disk filling up

**Symptom**: Docker reports `mysql` volume is near full.

**Diagnosis**:
```bash
docker exec dystore-mysql du -sh /var/lib/mysql
docker compose exec mysql mysql -u dystore -p${MYSQL_PASSWORD} dystore -e "
SELECT TABLE_NAME, ROUND(DATA_LENGTH/1024/1024,1) AS mb
FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dystore'
ORDER BY DATA_LENGTH DESC LIMIT 20;"
```

**Action**: the 01:00 maintenance window drops partitions older than 12 months. If it hasn't run recently:
```bash
docker compose exec api python -c "import asyncio; from dystore.scheduler.maintenance import drop_old_partitions; print(asyncio.run(drop_old_partitions()))"
```

---

## LLM bills spiking

**Symptom**: `ai_generation.cost` summed over a day exceeds expectations.

**Diagnosis**:
```sql
SELECT kind, COUNT(*), SUM(tokens_in + tokens_out) AS tokens
FROM ai_generation
WHERE created_at >= NOW() - INTERVAL 1 DAY
GROUP BY kind ORDER BY tokens DESC;
```

**Likely culprits**:
- The comment AI worker is reprocessing the same comments (check `sentiment IS NULL` count — should be 0 most of the time).
- Someone is invoking content generation in a loop from the UI.

**Mitigation**: switch to `deepseek-v4-flash` (cheaper) in `.env`:
```
DEEPSEEK_MODEL=deepseek-v4-flash
```
Restart the api container.

---

## "I need to start over"

```bash
docker compose down -v        # destroys MySQL + Redis + Playwright volumes!
rm -rf .dystore/              # local Playwright dirs if any
make up
make migrate
```

You'll need to log in again from scratch. Source PDFs and `openspec/` are untouched.
