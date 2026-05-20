> **Parallelism notation**
>
> - Sections marked `[parallel]` contain independent task lanes (A/B/C/...) that touch disjoint files. Dispatch one subagent per lane.
> - Sections marked `[serial]` must complete in order; the first task is the critical-path entry point.
> - Subagent boundary = one lane. Don't split a lane across agents — the lane's tasks share a single file or tightly-coupled files.

## 1. Foundation `[serial]`

- [x] 1.1 Create `web/src/api/enums.ts` exporting `AFTERSALE_TYPE: Record<number,string>` and `AFTERSALE_STATUS: Record<number,string>` with the verified values (type: 0=退款, 1=退货, 3=换货; status: 6=待审核, 7=进行中, 11=已完成, 27=已关闭). File header comments: "single source of truth, mirrored in backend api/v1/aftersale.py".
- [x] 1.2 Create `backend/dystore/api/v1/_enums.py` with the same two dicts (Python). One-line header pointer to `web/src/api/enums.ts`.

## 2. Backend routes `[parallel]` — 4 lanes, one subagent each

> Each lane writes one file under `backend/dystore/api/v1/`. Use `orders.py` as the template. Do NOT touch `api/v1/__init__.py` here — that's section 3.

### Lane A — Goods
- [x] 2.A.1 Create `backend/dystore/api/v1/goods.py` with `GET /api/v1/goods` (params: `page`, `page_size`, `tab`, `check_status`). Read `doudian_goods` ordered by `scraped_at DESC`, return `{total, items}` with fields `goods_id, title, price, stock, tab, check_status, scraped_at`.
- [x] 2.A.2 Add `GET /api/v1/goods/stats` returning `{total, sum_stock, low_count}` (low = stock < 5).
- [x] 2.A.3 Write `backend/tests/api/test_goods.py` with at least: list returns 24, filter by `tab=售卖中` returns subset, pagination beyond last page returns empty.

### Lane B — Stock
- [x] 2.B.1 Create `backend/dystore/api/v1/stock.py` with `GET /api/v1/stock` joining `doudian_stock` with `doudian_goods.title`, returning fields `goods_id, title, on_hand, available, locked, level, scraped_at` where `level` is derived in Python (`out` if on_hand<=0, `low` if <5, `over` if >200, else `normal`).
- [x] 2.B.2 Add `?include=skus` param: when present, also read `raw_json` from `doudian_stock` for each goods_id and extract `skus[*]` into an `skus` array on each item.
- [x] 2.B.3 Add `GET /api/v1/stock/levels` returning `{out: N, low: N, normal: N, over: N}` for KPI tiles.
- [x] 2.B.4 Write `backend/tests/api/test_stock.py` covering: list returns 20, level distribution is consistent, `?include=skus` returns sku arrays.

### Lane C — Aftersale
- [x] 2.C.1 Create `backend/dystore/api/v1/aftersale.py` with `GET /api/v1/aftersale` (params: `page`, `page_size`, `type`, `status`). Import enums from `_enums.py`. Return `{total, items}` with `aftersale_id, order_sn, type, type_label, status, status_label, refund_amount, deadline_at, scraped_at`.
- [x] 2.C.2 Add `GET /api/v1/aftersale/counts` returning `{scraped_at, dims: {dim_name: count}}` for the canonical 18 dims. Hardcode the 18-name tuple in the handler. Resolve `MAX(scraped_at)` first, then SELECT only canonical dims with that timestamp; fill missing dims with 0.
- [x] 2.C.3 Write `backend/tests/api/test_aftersale.py` covering: list returns 30, status filter works, counts response has exactly 18 keys.

### Lane D — Member
- [x] 2.D.1 Create `backend/dystore/api/v1/member.py` with `GET /api/v1/member/dashboard` returning `{agg: [...], daily: [...], hist: [...]}`.
- [x] 2.D.2 For `agg`: read latest `member_dashboard_agg`, extract `raw_json.data.data_head[*]` into `{index_name, index_display, value, unit, change_value, peer_excellent}`. Convert cents→yuan when `unit == "price"`.
- [x] 2.D.3 For `daily`: SELECT from `member_dashboard_day` ordered by `date ASC`, limit 30 most recent dates.
- [x] 2.D.4 For `hist`: SELECT from `member_dashboard_hist` where `scraped_at = MAX(scraped_at)`; de-duplicate.
- [x] 2.D.5 Write `backend/tests/api/test_member.py` covering: agg returns N>=1 KPI, daily returns 7 ascending dates, hist returns 8 unique buckets.

## 3. Wire routers `[serial]` — single-file edit

- [x] 3.1 In `backend/dystore/api/v1/__init__.py` (and/or `dystore/main.py`), include the 4 new routers (`goods`, `stock`, `aftersale`, `member`) following the existing `orders` registration pattern.
- [x] 3.2 Smoke each endpoint with `curl http://127.0.0.1:8080/api/v1/{goods,stock,aftersale,aftersale/counts,member/dashboard}` from the host and verify expected row counts (24, 20, 30, 18, ≥1).

## 4. Frontend pages `[parallel]` — 4 lanes, one subagent each

> Each lane fully rewrites one file under `web/src/pages/`. Use `Orders.tsx` as the structural template (PageContainer → KPI grid → ProTable). All lanes consume `web/src/api/enums.ts` from section 1.

### Lane A — Goods.tsx
- [x] 4.A.1 Rewrite `web/src/pages/Goods.tsx` to call `getJSON<{total,items}>("/goods", {page,page_size,tab,check_status})` and render a ProTable with columns 商品 (title, ellipsis copyable) / 价格 (¥) / 库存 (right-aligned, tabular) / 状态 (tab + check_status badges) / 抓取时间.
- [x] 4.A.2 Add KPI row at top: 商品总数 / 在售数 / 低库存数 (from `/goods/stats`).
- [x] 4.A.3 Add `tab` filter (Select with options "售卖中", "已下架") and `check_status` filter.

### Lane B — Stock.tsx
- [x] 4.B.1 Rewrite `web/src/pages/Stock.tsx`. Fetch `/stock/levels` for KPI tiles (4 colour-coded tiles matching existing legend: 低库存 orange, 缺货 red, 超量 blue, 呆滞 grey). Fetch `/stock?page=0&page_size=50` for the table.
- [x] 4.B.2 Table columns: 商品 / 在仓 / 可用 / 锁定 / 等级 (tagged by level). Click row → toggle SKU detail expansion using `/stock?include=skus&goods_id=...`.
- [x] 4.B.3 Verify all 4 legend colours match the page's previous static legend in the same order.

### Lane C — Aftersale.tsx
- [x] 4.C.1 Rewrite `web/src/pages/Aftersale.tsx`. Fetch `/aftersale/counts` for the 18 KPI grid (replace current 8). Each tile shows `index_display` (zh) + count + colour band by category (refund/return/exchange = info; deadline/arbitrate = critical; user-action = warning).
- [x] 4.C.2 Below the grid, fetch `/aftersale?page=0&page_size=20` and render ProTable with columns 售后号 / 订单号 / 类型 (type_label) / 状态 (status_label, tag colour) / 退款金额 / 截止时间.
- [x] 4.C.3 Add `status` filter Select; populate options from `AFTERSALE_STATUS` import.

### Lane D — Member.tsx
- [x] 4.D.1 Rewrite `web/src/pages/Member.tsx`. Fetch `/member/dashboard`. Render 4 KPI tiles using the top 4 entries from `agg` (preserve `index_display` for label, format value by `unit`: price→¥, ratio→%, number→thousands sep). Show `change_value` as small ▲/▼ badge.
- [x] 4.D.2 Render `daily` as ECharts line chart (x: date, y: value). Title from `metric`.
- [x] 4.D.3 Render `hist` as ECharts bar chart (x: bucket, y: value). Title "购买次数分布".

## 5. Spec-layer bug fixes `[parallel]` — 3 lanes

### Lane A — member_hist date
- [x] 5.A.1 Edit `backend/dystore/scraper/specs/doudian_member_hist.yaml`: add `static_fields: { date: today_local }` (or equivalent — check `transforms` syntax in `spec_loader.py`) so each row gets the scrape-day date.
- [x] 5.A.2 Verify with one manual scrape that new rows have non-NULL `date`.

### Lane B — sku_diagnose boolean
- [x] 5.B.1 Edit `backend/dystore/scraper/specs/doudian_sku_diagnose.yaml`: remove `to_str` from `diagnose_type` and `severity` transforms. Map `is_alarming` → `diagnose_type: "alarming"|"normal"` (text) via a new transform, or pass through as boolean column.
- [x] 5.B.2 If transform doesn't exist, add it in `backend/dystore/scraper/engine.py` (look for the transform registry).
- [x] 5.B.3 Verify with one manual scrape that rows distinguish alarming vs normal.

### Lane C — member_agg indices_json
- [x] 5.C.1 In the writer code for `member_dashboard_agg` (search `engine.py` / sink writer), after writing `raw_json`, also write `indices_json = [item['index_name'] for item in raw_json['data']['data_head']]`.
- [x] 5.C.2 One-shot SQL to backfill the 2 existing rows: `UPDATE member_dashboard_agg SET indices_json = JSON_EXTRACT(raw_json, '$.data.data_head[*].index_name') WHERE indices_json IS NULL;`. Save under `backups/backfill-2026-05-20-indices.sql`.

## 6. Verification `[serial]`

- [x] 6.1 Browser-test each of `/goods`, `/stock`, `/aftersale`, `/member` at `http://127.0.0.1:5173` — confirm real data renders, no "—" placeholders remain when data exists, no console errors.
- [x] 6.2 Run `cd backend && pytest -q backend/tests/api/test_{goods,stock,aftersale,member}.py` — all green.
- [x] 6.3 Run `cd backend && ruff check . && mypy dystore` and `cd web && pnpm typecheck && pnpm lint` — no new errors introduced.
- [x] 6.4 Update `README.md` if it lists "broken pages" or similar; otherwise no docs change needed.
- [x] 6.5 Run `openspec validate complete-dashboard-read-paths --strict` to ensure all artifacts pass schema check before archive.
