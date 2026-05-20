## Context

`bootstrap-merchant-platform` (the greenfield change) shipped the scraper, the orders/comments/alerts/tasks/settings/compass routes, and 13 sidebar pages. Live verification on 2026-05-20 revealed 4 of those pages are not actually wired:

- `Goods.tsx` calls `/scrape/runs?target=doudian_product` — wrong endpoint, shows task history not products
- `Stock.tsx`, `Aftersale.tsx`, `Member.tsx` — pure static JSX with hardcoded "—" placeholders, zero API calls

Meanwhile MySQL has 24 goods, 20 stock rows, 30 aftersale orders + 179 aftersale-counts snapshots, and 2/7/16 member-dashboard rows (agg/day/hist). The scraper YAML specs are correct and verified against live recon; the data is landing. Only the read path is missing.

The codebase already establishes the pattern via `api/v1/orders.py` + `Orders.tsx`: a FastAPI router returning `{total, items}`, a React Query `useQuery` for stats and a ProTable for paginated lists. Following that pattern keeps the new code mechanical and review-cheap.

## Goals / Non-Goals

**Goals:**
- Make the 4 broken pages display the data the scraper has already persisted, with the same UX language (KPI tiles + filterable paginated tables + charts where appropriate) as the working pages.
- Establish a shared enum module on the frontend so type/status integer ↔ Chinese label mapping is not re-derived in every component.
- Fix 3 spec-layer landing bugs that surfaced during recon (member_hist missing date, sku_diagnose boolean stringified, member_agg.indices_json unfilled), so that as scrapes continue to land, the new read paths see clean data.

**Non-Goals:**
- No new scrape YAML targets. No re-recon against fxg.jinritemai.com. All endpoint shapes are already known via existing YAML specs + raw_json samples in MySQL.
- No alembic migration. No table schema change. Spec-bug fixes are content-level (YAML edits + one-shot SQL backfill).
- No improvements to Compass / Peer / ContentWorkshop / Tasks / Alerts / Settings — those pages are working or are V2 scope.
- No AI/LLM work. (Comment sentiment is handled by the sibling change `wire-comment-ai-analysis`.)
- No pagination component changes; ProTable's existing pagination footer is sufficient.

## Decisions

### Decision 1: One capability `dashboard-read-paths`, not four
Each of the four pages could be its own capability. They're grouped into one because they share an architectural pattern (FastAPI router under `api/v1/` → MySQL table → ProTable on React) and reviewing one focused spec is faster than four near-identical specs.

**Alternative considered:** `goods-view`, `stock-view`, `aftersale-view`, `member-view` as four capabilities. Rejected: more ceremony, identical scenarios duplicated 4×, and the requirements are already partitioned by Requirement: heading within one spec.

### Decision 2: Latest-snapshot reads use `MAX(scraped_at)`, not partition pruning
`aftersale_counts` stores every scrape round, currently 179 rows containing ~10 snapshots × 60+ dims. The endpoint returns "current state", which means the most recent scrape only. Implementation: a single subquery `WHERE scraped_at = (SELECT MAX(scraped_at) FROM aftersale_counts)`.

**Alternative considered:** Reading just the last hour's rows. Rejected: assumes scrape cadence stability; will break silently if scheduler skips a window.

**Alternative considered:** Storing a `is_current` boolean per row, flipped on each scrape. Rejected: schema change, race conditions, the subquery is cheap given the small row count.

### Decision 3: 18 dims are hardcoded in the route handler, not in DB
The canonical 18 dimensions live in `docs/api-catalog.md`. The `aftersale_counts` table contains 60+ dims (the platform returns more than what the spec asks for). The endpoint declares the 18 in a Python constant and projects only those, returning 0 for any missing dim. This means future spec expansion (e.g., to 22 dims) is a single-line code change in the handler.

**Alternative considered:** Adding a `is_canonical` column to `aftersale_counts`. Rejected: schema change for a list that fits in a Python tuple.

### Decision 4: SKU expansion via `?include=skus`, not always
Stock list is goods-aggregated by default (20 rows). SKU expansion blows that up to 100+ rows. The default endpoint returns the aggregate; SKU detail is opt-in to keep the list page snappy.

### Decision 5: Member KPI extraction is read-time, not write-time
The 2 existing `member_dashboard_agg` rows have `indices_json: NULL`. Rather than rewriting the entire scrape pipeline, the read endpoint extracts KPIs from `raw_json.data.data_head[*]` at query time. The spec-bug-fix task populates `indices_json` going forward and backfills the 2 existing rows, but the endpoint does not depend on it (graceful fallback).

### Decision 6: Frontend enum module is a single TS file, not generated
`web/src/api/enums.ts` exports `AFTERSALE_TYPE` and `AFTERSALE_STATUS` as `Record<number, string>`. No build-time codegen, no OpenAPI sync — that's deferred per the bootstrap-merchant-platform task 13.6. Backend will simply duplicate the same constants in `api/v1/aftersale.py` (a 5-line dict). The duplication is acceptable for two ~7-entry enums and tracked as a tech-debt note in the file header.

### Decision 7: Parallelism in tasks.md
Tasks are organized so that all 4 backend routes can be implemented by 4 independent subagents (no shared files except `api/v1/__init__.py`, which is a 4-line edit and can be merged in a post-step), and likewise all 4 frontend pages can be in 4 parallel subagents. The shared `enums.ts` is built up-front as a synchronization point.

## Risks / Trade-offs

- **[Risk] `raw_json.data.data_head[*]` schema drift in `member_dashboard_agg`** → Mitigation: read-time extraction returns `[]` if the path doesn't resolve; member page shows "—" rather than crashing.
- **[Risk] 18-dim list goes stale if platform renames a dim** → Mitigation: each missing dim becomes a `0` in the response, page still renders. Out-of-band: add a daily log line listing which dims were missing.
- **[Risk] Stock SKU expansion is expensive for goods with many SKUs** → Mitigation: only behind `?include=skus` flag; default endpoint stays aggregated.
- **[Trade-off] Duplicating type/status enums backend + frontend** → Accepted because (a) values are stable (verified ints from real DB), (b) only 2 dicts × 7 entries, (c) OpenAPI codegen is explicitly deferred per the parent change.
- **[Risk] `Goods.tsx` rewrite will lose the current "task history" view** → Acceptable: task history already lives on `/tasks`. The current Goods page shows it by mistake, not by design.

## Migration Plan

Pure additive change on the backend; pure UI rewrite on the frontend. No DB migration.

1. Land backend routes (4 independent files). Smoke each with `curl`.
2. Land frontend pages (4 independent files). Visually verify in browser at `http://127.0.0.1:5173`.
3. Apply the 3 spec-layer fixes. Trigger a one-shot scrape of `doudian_member_hist` to confirm `date` is populated. Run the `UPDATE` to backfill `indices_json` on the 2 existing `member_dashboard_agg` rows.
4. Rollback: revert the commits. Pages return to their previous broken state but no data is lost.

## Open Questions

- Should `Stock.tsx` show low-stock badges as colour-coded (orange/red/blue/grey) matching the legend already in the page? **Resolved**: yes, keep the existing legend, populate it.
- Should `Member.tsx`'s histogram chart include the `_peer_avg` / `_peer_exl` y-keys that the platform also returns? **Resolved**: no, V1 ships only `dis_order_cnt_pay_user_cnt`, matching what the spec already extracts. Peer comparison can be a V2 enhancement.
- Should `audience_feature` (受众画像) be in scope? **Resolved**: not in V1 of this change. The table exists but `doudian_audience_feature` YAML is scheduled and may not have run; defer to a follow-up. If `audience_feature` has rows at implementation time, the member endpoint MAY add a `profile` section as a stretch goal.
