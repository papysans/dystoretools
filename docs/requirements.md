# dystoretools — Consolidated Requirements (V1 + V2)

> **Status**: draft awaiting user review before being formalised into an OpenSpec `proposal.md`.
> **Scope**: combined V1+V2 (per user directive "V1, V2 同时做"). V3 items are listed but explicitly deferred.

---

## 1 · Source materials

| File | Pages | Topic |
|------|------:|-------|
| `和豆包的对话_0516.pdf` | 5 | Overall architecture, integrations, hardware, 7-day deployment plan |
| `和豆包的对话_05161.pdf` | 5 | Plugin install steps, data routing, 6 functional capabilities, AI feed pipeline |
| `和豆包的对话_05162.pdf` | 4 | **24-hour automation timeline** (9 scheduled task windows) |
| `和豆包的对话_05163.pdf` | 6 | **MySQL schema** (5 tables), DB connection config |
| `和豆包的对话_05164.pdf` | 3 | Deployment flow, AI inference layer, final summary |

These PDFs are dialog exports between the customer and the *豆包* AI. They are advisory, not authoritative: this document is.

---

## 2 · What we are NOT building (explicit non-goals)

| Removed | Why |
|---------|-----|
| **OpenClaw orchestration framework** | User directive. We build the FastAPI service directly. |
| **Official 抖店 Open API integration** | Requires business-license qualification the user does not have. |
| **巨量千川 API integration** | Same qualification constraint. May appear via backend scraping in V3 if needed. |
| **巨量云图 API integration** | Same. |
| **RAG / vector database / embeddings** | User deferred to V3. |
| **Smart customer service (auto-reply 飞鸽 IM)** | IM real-time scrape is too risky for an external automation; replaced with "AI drafts reply, user pastes". |
| **Multi-tenancy / RBAC / multiple merchant accounts** | Single user, single machine. |
| **Cloud SaaS hosting / Kubernetes** | Single-machine Docker Compose only. |
| **Compliance gates and TOS-violation warnings** | User accepts the operational risk explicitly. |

---

## 3 · Confirmed user constraints (clarification round)

| # | Decision | Value |
|---|----------|-------|
| 1 | MVP scope | **V1 + V2 combined** |
| 2 | Tenancy | Single tenant |
| 3 | Deployment | Single machine (Docker Compose) |
| 4 | User roles | Single user, no RBAC |
| 5 | Credentials path | **Playwright session** (user is a merchant; logs in with email/password; OTP if challenged) |
| 6 | Data source breadth | **抖店 only** (V1+V2); peer monitoring via public scraping (V2) |
| 7 | Data retention | Not specified → default 1 year, archive thereafter |
| 8 | AI cost cap | None (do not throttle in V1+V2) |
| 9 | RAG | **Deferred to V3** |
| 10 | Dashboard freshness | **WebSocket realtime** |

---

## 4 · Functional inventory (V1 + V2)

Each row is a candidate user-facing capability. The `Feasibility` column reflects what is achievable *given the constraints in §2*; rows marked ❌ are removed from scope.

### 4.1 · Merchant-side (uses logged-in session)

All "Endpoint" cells below are **confirmed live** in a 2026-05-18 recon session — full inventory in [`api-catalog.md`](api-catalog.md).

| Capability | Endpoint(s) | Feasibility | Notes |
|------------|-------------|:-----------:|-------|
| 订单列表 + tab 计数 | `/api/order/searchlist` · `/api/order/tabcnt` | ✅ | V1 P0 |
| 商品列表 + 类目 + 分组 | `/product/tproduct/list` · `…/categoryOptionsN` · `…/getProductGroupList` | ✅ | V1 P0 |
| 库存列表 + SKU 诊断 | `/stock/manage/list` · `/stock/manage/sku_stock_diagnose` | ✅ | V1 P0 — `sku_stock_diagnose` 直接给低库/呆滞库信号 |
| 评论列表（按 rank 分） | `/product/tcomment/commentList` (rank=0/1/2/3) | ✅ | V1 P0 |
| 差评未回复列表 + 计数 | `/product/tcomment/getUnreplyNegativeCommentList` + `…Count` | ✅ | V1 P0 |
| 评论统计 + tag 聚合 + 预警 | `/product/tcomment/statistics` · `…/allCommentTagAggStat` · `…/commentIndexWarning` · `…/getNegativeCommentTagsCount` · `…/getNegativeCommentProductList` | ✅ | V1 P0 — 平台原生差评 tag 已聚合，我们做 **跨商品差评聚类 + 痛点时序** 作差异化 |
| 售后单列表 | `/after_sale/pc/list` (POST) | ✅ | V1 P0 |
| 售后 18 维度计数 | `/shopuser/aftersale/counts?fields=<18-csv>` | ✅ | V1 P0 — 18 维度直接映射 `/ws/alerts` 子类型 |
| 飞鸽 IM 未读 | `/api/scale_shop/doudian_im/shop/user/unread_count` | ✅ | V1 P0 — display only |
| 店铺/会员看板（聚合 / 日 / 直方图） | `/api/member/dashboard/v2/get_shop_dashboard_aggregate_data` · `…_daily_data` · `…_histogram_data` | ✅ | V1 P0 — 这套接口直接喂主看板，不用我们重算 |
| 受众画像 | `/api/marketing/user_profile/get_audience_feature` | ✅ | V1 P0 — `userType=2` 会员、`referenceUserType=0` 整体 |
| 会员销售活动列表 | `/api/member/dashboard/get_shop_member_sales_activity_list` | ✅ | V1 P1 |
| 搜索运营核心数据 + 趋势 | `/compass_api/.../search_analysis/core_data` · `…/core_data_trend_v2` | ✅ | V2 P0 — 罗盘原生输出，直接喂搜索流量看板 |
| 搜索运营诊断 + 优化建议 | `/compass_api/.../search_diagnosis/*` 共 5 接口 | ✅ | V2 P1 — 罗盘已经给优化建议，AI 在此基础上再做"个性化解读 + 行动卡片" |
| 行业词排名 | `/compass_api/.../industry_words/doudian_rank_v3` | ✅ | V2 P1 — 选品/趋势挖掘 |
| 店播视频列表 + 数据 | `/compass_api/.../after_watch/shop_video_list` · `…/video_cnt_v2` | ✅ | V2 P1 — 自家视频数据，不依赖抖音公开页 |
| 店铺排名 | `/compass_api/.../shop_rank/search_v2` | ✅ | V2 P1 |
| 商家体验分 | `/ffa/eco/experience-score` | ✅ | V1 P1 — 单数字 KPI tile |
| 商品诊断 | `/ffa/g/diagnose` | ✅ | V1 P1 — 商品健康分 |
| 违规 / 申诉 / 店铺保障 | `/ffa/govern-guarantee/*` 3 接口 | ✅ | V1 P1 — 风险/违规预警 |
| 营销工具 / 优惠券 / 活动 | `/ffa/marketing/*` 多接口 | ✅ | V2 P1 — 营销效果分析 |
| 物流相关 6 模块 | `/ffa/morder/logistics/*` · `/ffa/logistics-project/*` | ✅ | V2 P2 — 物流时效/异常监控 |
| 短视频 / 直播 / 图文运营 | `/ffa/content-tool/*` 4 模块 | ✅ | V2 P1 — 内容数据 + AI 创作辅助 |
| 卡券管理 (O2O) | `/ffa/morder/o2o/poi-verify` | ✅ | V1 P2（若有 O2O 业务） |
| **千川 ROI / 计划分析** | qianchuan.jinritemai.com | ⚠️ **V3** | Separate login, higher anti-bot strictness |
| **云图人群 / 标签** | yuntu.oceanengine.com | ⚠️ **V3** | Same |
| **托管管理 (官方智能托管)** | `/ffa/smart-hosting/home` | ⚠️ **V3** | 与官方 AI 托管功能重叠，需先决定共存策略 |
| **飞鸽 IM 自动回复** | im.jinritemai.com | ❌ | Removed — too risky |
| **店铺装修** | `/ffa/shop/decorate/...` | ❌ | Out of scope — 不是数据/分析能力 |

**完整菜单 57 个模块映射见 [`menu-map.md`](menu-map.md)。**

### 4.2 · Public / peer-side (anonymous scraping, V2)

| Capability | Source | Feasibility | Notes |
|------------|--------|:-----------:|-------|
| 同行店铺监控（价格 / 上新） | 抖音公开店铺页 | ✅ | Configurable peer list |
| 同行直播节奏 | 抖音直播公开页 | ✅ | |
| 抖音视频/直播带货热榜 | 抖音公开页 | ✅ | |
| 第三方数据兜底（灰豚 / 蝉妈妈 API） | external | ✅ | Behind a `DataSource` abstraction; OFF by default |

### 4.3 · AI-driven (no scraping; consumes stored data + LLM)

| Capability | Inputs | Outputs |
|------------|--------|---------|
| 评论差评预警 | 商品评论表 | WS alert + 中心列表 |
| 评论痛点聚类 | 商品评论表 | 报告（按商品/SKU 维度） |
| 标题生成 | 商品标题 + 类目 | N 个候选标题 |
| 详情页文案 | 商品属性 + 卖点 | 详情段落 |
| 短视频脚本 | 商品 + 目标人群 | 30/60/90s 脚本 |
| 直播话术 | 商品 + 时段 + 主题 | 开场 / 讲品 / 互动 / 促单话术 |
| 评论 / 咨询回复草稿 | 单条评论或咨询 | 草稿（用户复制粘贴） |
| 选品 / 投放建议 | 自己店数据 + 公开榜单 | 建议清单 |
| 销量异动预警 | 自己店订单时序 | WS alert |
| 同行异动预警 | 同行店铺时序 | WS alert |

---

## 5 · Architecture (target)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Frontend  (Vite + React 18 + TS + Ant Design Pro + ECharts)              │
│  Pages: 总览看板 · 订单 · 商品 · 评论 · 客户 · 文案工坊 · 同行 · 任务 · 告警 │
│  WS clients: dashboard · tasks · alerts · auth-required                   │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTP/WS  127.0.0.1:8080
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend  (FastAPI · Uvicorn · single process, multi-coroutine)           │
│  REST: /api/v1/*           WS: /ws/{dashboard,tasks,alerts,auth-required} │
└──┬──────────┬────────────┬─────────────┬─────────────┬───────────────────┘
   │          │            │             │             │
   ▼          ▼            ▼             ▼             ▼
┌──────┐ ┌────────┐ ┌───────────┐ ┌─────────────┐ ┌────────────────┐
│Sched │ │Analytics│ │ AI svc    │ │Merchant     │ │Public          │
│APSchd│ │ pandas │ │ DeepSeek/ │ │ Scraper     │ │ Scraper        │
│  9个 │ │  SQL    │ │ Kimi REST │ │ (logged-in) │ │ (anonymous)    │
└──┬───┘ └───┬────┘ └─────┬─────┘ └──────┬──────┘ └────────┬───────┘
   │         │            │              │ Playwright       │ Playwright
   │         │            │              │ persistent ctx   │ headless +
   │         │            │              │ ─ headed default │ stealth +
   │         │            │              │ ─ stealth        │ cookie pool
   │         │            │              ▼                  ▼
   │         │            │     fxg.jinritemai.com     抖音公开页 / 灰豚API
   ▼         ▼            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MySQL 8 (business tables)  ·  Redis 7 (sessions / tasks / pub-sub / WS) │
└──────────────────────────────────────────────────────────────────────────┘
                                 ▲
                       ┌─────────┴────────┐
                       │  Docker Compose  │
                       │  4 services      │
                       └──────────────────┘
```

Detailed scraping mechanics, sign-param handling, session-persistence and risk-verification flows are in [`docs/scraping-patterns.md`](scraping-patterns.md).

---

## 6 · Data model (initial)

Adapted from PDF3 with non-feasible tables dropped and new ones added for V1+V2.

```sql
-- ── 商品 / 订单 / 库存 / 售后 ───────────────────────────────────
doudian_order        (id, order_sn, goods_name, sale_num, order_amount, pay_time, status, raw_json, scraped_at)
doudian_goods        (id, goods_id, title, price, stock, click_num, convert_rate,
                      category_id, group_id, tab, check_status, business_type, raw_json, scraped_at)
doudian_stock        (id, goods_id, sku_id, warehouse_id, on_hand, available, locked, raw_json, scraped_at)
doudian_sku_diagnose (id, goods_id, sku_id, diagnose_type, severity, msg_json, scraped_at)  -- 来自 sku_stock_diagnose
doudian_aftersale    (id, aftersale_id, order_sn, type, reason, refund_amount, status,
                      sub_status, created_at, deadline_at, raw_json, scraped_at)
aftersale_counts     (id, dim, count, scraped_at)  -- 18 维度时序

-- ── 评论 ───────────────────────────────────────────────────────
doudian_comment      (id, goods_id, comment_id, sku, content, rating, user_nick, created_at, scraped_at,
                      reply_status, has_appeal, raw_json,
                      sentiment, pain_points_json)            -- last two filled by AI worker
comment_tag_stat     (id, scope, scope_id, tag, neg_count, total_count, scraped_at)  -- scope = shop|goods
comment_index_warn   (id, kind, severity, payload_json, scraped_at)
neg_comment_product  (id, goods_id, neg_count, score, scraped_at)

-- ── 会员 / 受众 ────────────────────────────────────────────────
member_dashboard_agg (id, date, indices_json, raw_json, scraped_at)
member_dashboard_day (id, date, metric, value, scraped_at)
member_dashboard_hist(id, date, bucket, value, dim, scraped_at)
audience_feature     (id, user_type, ref_user_type, feature_kind, feature_value, weight, scraped_at)
member_sales_activity(id, activity_id, name, start_at, end_at, status, raw_json, scraped_at)

-- ── 罗盘 (搜索运营 / 内容 / 排名) ──────────────────────────────
compass_core_data    (id, scope, date_type, begin_date, end_date, metric, value, raw_json, scraped_at)
compass_core_trend   (id, index_name, date, value, scraped_at)
compass_diagnose     (id, kind, payload_json, scraped_at)
compass_industry_word(id, industry_id, category_id, rank_type, word, rank, value, scraped_at)
compass_shop_rank    (id, sort_field, rank, value, scraped_at)
shop_video           (id, video_id, author_id, content_type, audit_status, publish_at,
                      duration, play_count, gmv, raw_json, scraped_at)

-- ── 治理 / 体验分 / 商品诊断 ───────────────────────────────────
experience_score     (id, date, score, sub_scores_json, scraped_at)
goods_diagnose       (id, goods_id, score, issues_json, scraped_at)
shop_violation       (id, violation_id, kind, severity, status, raw_json, created_at, scraped_at)

-- ── 营销 / 物流 / 内容运营 (V2) ────────────────────────────────
marketing_coupon     (id, coupon_id, name, kind, status, start_at, end_at, used, raw_json, scraped_at)
marketing_activity   (id, activity_id, name, kind, status, raw_json, scraped_at)
logistics_event      (id, order_sn, waybill_no, event, location, occurred_at, scraped_at)
content_video        (id, video_id, platform, kind, raw_json, scraped_at)         -- V2 内容运营
content_live         (id, room_id, start_at, end_at, gmv, raw_json, scraped_at)
content_imagetext    (id, item_id, kind, raw_json, scraped_at)

-- ── 公开 / 同行 (V2 · PublicScraper) ───────────────────────────
peer_shop            (id, shop_id, shop_name, follower_count, scraped_at)
peer_goods           (id, peer_shop_id, goods_id, title, peer_price, hot_sale, scraped_at)
peer_livestream      (id, peer_shop_id, room_id, start_time, end_time, gmv, scraped_at)

-- ── 系统横切 ───────────────────────────────────────────────────
ai_generation        (id, kind, input_hash, output_text, model, tokens_in, tokens_out, cost, created_at)
scrape_task_run      (id, target, started_at, finished_at, status, items_count, error_msg)
alert                (id, kind, severity, payload_json, dispatched_at, acked_at)
session_event        (id, kind, payload_json, occurred_at)  -- login / expiry / risk_verification / re-auth
```

`raw_json` columns store the full upstream JSON for re-parsing if upstream schema evolves. Aggregate tables (`compass_*`, `member_dashboard_*`, `aftersale_counts`) are time-series — partition by `scraped_at` month for cheap deletion at the 1-year retention boundary. **Dropped from PDF3**: `qianchuan_ad` and `yuntu_user` (V3, separate logins).

`raw_json` and `payload_json` are `JSON` columns preserving the full upstream response for re-parsing if schema evolves. `scraped_at` is non-null on every row that came from a scrape.

---

## 7 · Scheduled task windows

Lifted from PDF2 (24h timeline) and lightly normalized:

| Time | Tasks |
|------|-------|
| `00:10` | 上日全量回填：订单 / 商品 / 评论 / 售后 / 销量统计 / 异动检测 |
| `01:00` | 全量历史归档（>1 年数据移到归档分区） |
| `07:30` | 早间增量：订单 / 待处理售后 / 隔夜评论 / 库存预警 |
| `10:00` | 上午增量：订单 / 同行价格巡检 (V2) |
| `12:00` | 午间：评论分析批次 / 文案 AI 队列处理 |
| `15:00` | 下午增量 + 销量异动判定 |
| `18:00` | 黄金时段：订单 / 同行直播开播监控 (V2) |
| `21:30` | 晚间：订单 / 评论 / 当日 KPI 出报 |
| `02:00` | 深夜：仅 DB 备份与日志归档；**禁止访问商家后台** |

`00:00–06:00` window **does not run any merchant-backend scrape** — anomalously timed access is the strongest reason for risk-engine flagging.

---

## 8 · Realtime channels (WebSocket)

| Channel | Direction | Payload |
|---------|-----------|---------|
| `/ws/dashboard` | server → client | KPI deltas, new orders, new comments |
| `/ws/tasks` | server → client | scraper task lifecycle (queued / running / done / failed) |
| `/ws/alerts` | server → client | 销量下跌 / 差评 / 库存低 / 同行异动 |
| `/ws/auth-required` | server → client | session expired or risk verification surfaced → frontend opens visible browser window for user to handle |

All channels use a single Redis pub-sub backend for fan-out so multiple frontend tabs stay in sync.

---

## 9 · Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|:---------:|:------:|-----------|
| 抖店 风控触发账号封禁 | Medium | **High (business stop)** | (a) headed Chrome default; (b) human-like delays 3–10s; (c) no 0–6am access; (d) single-concurrency per domain; (e) `playwright-stealth` |
| `a_bogus` 签名算法变更 | Medium-High | Medium | Interceptor pattern decouples us from sig logic — the page always computes a fresh valid sig before we read the response |
| 会话过期 / 二次验证频繁 | High | Low–Med | Detection → WS push `/ws/auth-required` → user re-auths in a popped-up visible browser window |
| 公开页反爬升级 (V2) | Medium | Low | DataSource 抽象层 → 灰豚/蝉妈妈 API 兜底 |
| LLM 输出包含敏感字段（手机号 / 地址） | High | Medium | Scrub PII before prompting; never log raw prompts containing customer data |
| 单机磁盘填满 | Medium | Medium | 1-year retention + archive partition + Docker volume size alert |

---

## 10 · Out of scope (V3 candidates)

- 千川 backend scraping (qianchuan.jinritemai.com)
- 云图 backend scraping (yuntu.oceanengine.com)
- RAG over comments / scripts
- 飞鸽 IM auto-reply
- Mobile app
- Multi-merchant support
- Hosted SaaS
