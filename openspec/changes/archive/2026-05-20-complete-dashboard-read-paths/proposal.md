## Why

End-to-end audit of the running system on 2026-05-20 found that 4 of 13 dashboard pages cannot display the data that the scraper has already persisted to MySQL:

| Page | DB rows present | Frontend currently shows |
|------|-----------------|--------------------------|
| 商品 (Goods) | 24 in `doudian_goods` | Scrape-task history (wrong endpoint) |
| 库存 (Stock) | 20 in `doudian_stock`, ~10 in `doudian_sku_diagnose` | Static `<Empty>` — zero API calls |
| 售后 (Aftersale) | 30 in `doudian_aftersale`, 179 in `aftersale_counts` | Static "—" placeholders — zero API calls |
| 用户 (Member) | 2 in `member_dashboard_agg`, 7 in `_day`, 16 in `_hist` | Static "—" placeholders — zero API calls |

`bootstrap-merchant-platform` shipped the scraper layer (33 YAML specs, all verified against live recon) and the orders/comments/alerts/tasks/settings/compass read paths, but the read paths above were never wired. Its remaining 10 tasks are explicitly deferred edge cases; these four broken pages are **gaps, not deferred work**. The merchant is currently blind to four operational surfaces despite the backend faithfully scraping them daily.

## What Changes

- Add 5 FastAPI read endpoints in `backend/dystore/api/v1/`:
  - `GET /api/v1/goods` — list goods with filters (tab, check_status), pagination, GMV stat
  - `GET /api/v1/stock` — list stock with low/out/dead flag, SKU expansion from `raw_json.skus[]`
  - `GET /api/v1/aftersale` — list after-sale orders with type/status enum mapping, pagination
  - `GET /api/v1/aftersale/counts` — latest snapshot of the canonical 18 dimensions (per `docs/api-catalog.md §6 lines 117-122`)
  - `GET /api/v1/member/dashboard` — aggregate KPIs (from `member_dashboard_agg.raw_json.data.data_head[*]`), daily series, histogram buckets
- Rewrite 4 frontend pages to consume real data:
  - `Goods.tsx` — replace scrape-runs table with goods list (title / price / stock / tab / check_status)
  - `Stock.tsx` — KPI tiles (low / out / over / dead) + table
  - `Aftersale.tsx` — fill out the 18-dim KPI grid (currently 8) + after-sale order list with status mapping
  - `Member.tsx` — KPI tiles fed from agg, daily-trend ECharts line, histogram bars
- Define aftersale type / status enum constants in one shared frontend module (`web/src/api/enums.ts`) — values verified from DB samples (type: 0=退款 / 1=退货 / 3=换货; status: 6=待审核 / 7=进行中 / 11=已完成 / 27=已关闭).
- Patch 3 spec-layer bugs surfaced during recon:
  - `doudian_member_hist.yaml` — write `date` (currently NULL)
  - `doudian_sku_diagnose.yaml` — stop `to_str(bool)` on `is_alarming`; let it stay boolean
  - `doudian_member_agg` writer — populate `indices_json` from `raw_json.data.data_head[*]`
- **Non-goal**: 同行 (Peer), 罗盘 (Compass), 文案工坊 (ContentWorkshop), or any V2 surface; all remain as-is.
- **Non-goal**: no scraper changes beyond the 3 spec patches above; no new YAML targets; no new tables; no migrations beyond optional column backfill (single-line `UPDATE`).

## Capabilities

### New Capabilities

- `dashboard-read-paths`: HTTP read endpoints under `/api/v1/{goods,stock,aftersale,member}` that project already-persisted scraper output into pagination + filter + aggregation shapes the React dashboard consumes. Includes the 18-dim aftersale-counts latest-snapshot rule and the SKU expansion rule for stock. Excludes any write paths and any scraper changes.

### Modified Capabilities

(none — this change consumes data the scraper already lands; spec-layer YAML patches are minor and stay inside the scraper subsystem's existing capability, captured as tasks rather than spec deltas)

## Impact

- **Code (backend)**: 4 new files under `backend/dystore/api/v1/` (goods.py, stock.py, aftersale.py, member.py); 1 line edit each in `api/v1/__init__.py` and `dystore/main.py` to mount routers. ~250 LOC.
- **Code (frontend)**: 4 full-file rewrites in `web/src/pages/` (Goods, Stock, Aftersale, Member); 1 new shared `web/src/api/enums.ts`. ~400 LOC.
- **Code (scraper bug-fixes)**: 2 YAML edits + 1 small ETL change in `engine.py` for `indices_json` backfill. ~20 LOC.
- **Storage**: No schema migration. Optional one-time `UPDATE` to backfill `member_dashboard_agg.indices_json` for the 2 existing rows.
- **Dependencies**: None added. ECharts is already in the lockfile.
- **Risk surface**: Pure read paths on existing tables. No scraper-quiet-hours rules touched. No LLM cost. No third-party calls.
- **Verifiability**: Each route can be smoked with a single `curl http://127.0.0.1:8080/api/v1/...` returning known row counts from the running DB (goods=24, stock=20, aftersale=30, aftersale_counts latest 18, member day=7).
