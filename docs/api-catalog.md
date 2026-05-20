# dystoretools — Doudian Merchant Backend API Catalog

> Empirical catalogue captured 2026-05-18 from a logged-in recon session against `fxg.jinritemai.com`.
> Each endpoint listed here was observed firing on a real page load. Treat URLs as *confirmed-then*, not as *forever stable*.
> **Signing**: every call carries the cluster of `appid` / `__token` / `_bid` / `_lid` / `aid` / `msToken` / `a_bogus` / `verifyFp` / `fp` query params. See [`scraping-patterns.md`](scraping-patterns.md) §1.

---

## Conventions

- **Base host** (omitted from rows below): `https://fxg.jinritemai.com`
- **Endpoint path** is shown literally; only the *meaningful* query/body parameters are listed (sign/token params are implicit).
- **`_bid`** column = the `biz id` query parameter passed by that page; useful for filtering which page surfaced the request.
- **Priority** column for the scraper roadmap:
  - **P0** = required for V1 (orders / goods / inventory / comments / aftersale)
  - **P1** = required for V2 (peer monitoring excluded — comes from PublicScraper)
  - **P2** = nice-to-have, defer
  - **P3** = informational, probably never scraped

---

## 1 · Merchant homepage navigation (the menu)

Source: 57 anchor links extracted from `/ffa/mshop/homepage/index?from=buyin`. The full menu URL list is preserved as `docs/menu-map.md` (see §A below). Useful to know upfront so we don't go fishing for routes during implementation.

---

## 2 · Orders  (`_bid = ffa_order` · page `/ffa/morder/order/list`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | GET | `/api/order/searchlist` | `page`, `pageSize`, `tab` (`all`/`unpaid`/`unshipped`/…), `order_by=create_time`, `order=desc` | Paginated order list — the primary scrape target |
| **P0** | GET | `/api/order/tabcnt` | `tabcnt_version=v1`, `tab=all` | Counts per order tab (待付款/待发货/…) |
| P1 | POST | `/api/order/searchConfig` | — | Field config for the list page |
| P1 | POST | `/api/order/searchConfig?action=link_fields` | — | Sub-field/link config |
| P2 | GET | `/api/order/getNotice` | `position=order_list_banner` | Banner notices |
| P2 | GET | `/api/order/operateReasonConfig` | `operate_type=apply_real_tel` / `postpone_virtual` | Operate dropdown reasons |
| P2 | GET | `/api/order/orderConfig` | `config_scene=order_tool_card` | Tool-card config |
| P2 | GET | `/api/order/getOmsConfig` | `config_key=shop_order_manager_tag_config` | OMS tag config |
| P3 | GET | `/api/order/query_shop_id_gray` | — | Gray-release shop ID query |
| P3 | GET | `/order/torder/front_interface_gray_shop` | — | Front-end gray-release |
| P3 | GET | `/shopuser/store/get_pick_up_store_list` | — | Pick-up store list |

---

## 3 · Products  (`_bid = ffa_goods` · page `/ffa/g/list`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | GET | `/product/tproduct/list` | `page`, `pageSize=20`, `tab=onSale`, `business_type`, `is_online`, `check_status`, `order_field=audit_time`, `sort=desc`, `group_id`, `comment_percent`, … | Paginated product list — primary scrape target |
| **P0** | GET | `/product/tproduct/aggsProductCount` | `tab=onSale` | Counts per product tab |
| P1 | GET | `/product/tproduct/getProductGroupList` | `pageSize=100` | Product groups |
| P1 | GET | `/product/tproduct/categoryOptionsN` | `cid=0` | Category options tree |
| P1 | GET | `/product/tproduct/listTractionItems` | `tab=onSale` | Highlighted/traction items |
| P1 | GET | `/product/tproduct/rectifyInfo` | `need_first_check=true` | Rectification info (products needing fixes) |
| P2 | GET | `/product/tproduct/getShopShipDelayRule` | — | Shop ship-delay rule |
| P2 | GET | `/product/tproduct/queryExcitation` | `excitation_codes=new_publish_product` | Publishing incentives |
| P2 | GET | `/product/tproduct/popup_content` | `scene=product_list`, `pid` | Popup content |
| P2 | GET | `/product/tproduct/isInAllowlist` | `list_name=<big csv of feature flags>` | Feature-flag read; useful to know what flags are on |
| P2 | GET | `/product/tproduct/listBanner` | — | List page banner |
| P2 | GET | `/product/prettify/getGrayStatus` | `gray_key=component_show` | Gray-release component visibility |
| P2 | GET | `/shopuser/tshopuser/listAftersaleStrategy` | `page`, `size=1000` | After-sale strategy list (used by product page filter) |

---

## 4 · Inventory  (`_bid = ffa_goods` · page `/ffa/g/stock-manage/list`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | POST | `/stock/manage/list` | body: filter / pagination | Stock list — primary scrape target |
| **P0** | POST | `/stock/manage/sku_stock_diagnose` | body | **SKU-level stock diagnosis** (low / over / dead stock signals) |
| P1 | GET | `/stock/index/warehouse_list` | — | Warehouse list |
| P2 | POST | `/stock/manage/spot_top_banner` | — | Top banner on stock page |
| P3 | GET | `/stock/manage/drawer_gray` | `shop_id=<shop_id>` | Drawer gray-release (also exposes `shop_id`) |
| P3 | GET | `/stock/index/edit_black` | — | Edit blacklist |

---

## 5 · Comments  (`_bid = ffa_aftersale` · page `/ffa/maftersale/comment`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | GET | `/product/tcomment/commentList` | `rank=0` (all) / `1` (negative) / `2` (mid) / `3` (positive), `page`, `pageSize=20`, `content_search`, `reply_search`, `appeal_search`, `bad_comment_class_tag_key`, `status_filter`, `count_ecology_score_filter` | **All-comments list** — primary AI input |
| **P0** | GET | `/product/tcomment/getUnreplyNegativeCommentList` | `page=1`, `page_size=10`, `rank=1` | Unreplied negative comments (high priority feed) |
| **P0** | GET | `/product/tcomment/getUnreplyNegativeCommentCount` | — | Count of unreplied negative comments |
| **P0** | GET | `/product/tcomment/statistics` | — | Overall comment statistics |
| **P0** | GET | `/product/tcomment/commentIndexWarning` | — | Comment-index warning (suggests platform-driven thresholds) |
| **P0** | GET | `/product/tcomment/allCommentTagAggStat` | `reply_search=1` | Tag aggregation across all comments (drives differential analysis) |
| **P0** | GET | `/product/tcomment/getNegativeCommentTagsCount` | — | Per-tag count for negative comments |
| **P0** | GET | `/product/tcomment/getNegativeCommentProductList` | — | Products ranked by negative-comment volume |
| P1 | POST | `/api/business/incubation/comment/get_product_comment_list` | body | Per-product comment detail batch |
| P1 | GET | `/product/tcomment/commentCRM` | — | Comment CRM data |
| P1 | GET | `/product/tcomment/checkOpenGptReply` | — | Whether the shop has enabled GPT-reply (native AI reply feature) |
| P1 | POST | `/api/business/incubation/comment/get_comment_hosting_enable_status` | body | Comment hosting (auto-reply托管) status |
| P1 | POST | `/api/business/incubation/comment/get_comment_shop_new_tag_status` | body | Comment-shop new-tag status |
| P2 | GET | `/product/tcomment/getCommentGiftDetail` | — | Comment-gift detail |
| P2 | GET | `/product/tcomment/getCommentGiftProductList` | — | Comment-gift product list |
| P2 | GET | `/product/tcomment/isInAllowList` | `list_name=<csv>` | Comment feature flags |

> **AI integration note**: the platform already ships its own GPT-reply, hosting (托管), summary, and ask-AI tabs (`shop_comment_gpt_reply`, `shop_product_comment_aggregation`, `shop_comment_summary`, `shop_comment_ask`). We can either coexist (treat platform AI as a competitor and offer differentiation: deeper clustering / cross-product / longitudinal trends) or read the platform's outputs for free. Decide during V1 design.

---

## 6 · Aftersale  (`_bid = ffa_aftersale` · page `/ffa/merchant-aftersale-workbench/aftersale/list`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | POST | `/after_sale/pc/list` | body: filter / pagination | After-sale order list — primary target |
| **P0** | GET | `/shopuser/aftersale/counts` | `fields=` 18 dims CSV | **18-dimensional counts** (待审核退款/待审核换货/超时即将到期/紧急/仲裁待协商/待举证/…) |
| P1 | GET | `/v1/aftersale/get_msg_box` | `msg_box_scene=1` | Message box |
| P1 | GET | `/shopuser/aftersale/getAfterSaleListShowConfig` | `shop_hit_gray_info=<json>` | List display config |
| P2 | GET | `/v1/aftersale/grayHit` | `scene=detail_v3_opt_pigeon` / `proof_video` / `secid` / `proof_upload` / `list_v1` | Gray-release hit check |
| P2 | POST | `/aftersale/get_guide` | — | Operation guide |

### 18 aftersale dimensions (the `fields` list)
```
all_audit_reg_spill, approaching_deadline_audit, urge_audit, presale_all_audit,
refund_audit, return_audit, exchange_audit, resend_audit, repair_audit,
wait_for_receive_and_delivery, return_for_receive, exchange_for_receive,
wait_user_delivery, wait_user_sign, exchange_wait_user_sign,
arbitrate_pending_negotiation, arbitrate_pending_evidence, arbitrate_pending
```
These map cleanly to alert categories in our `/ws/alerts` channel.

---

## 7 · Compass (商业罗盘 — 搜索运营)  (`_bid = fxg_admin` / `ecom_supply_search_fxg` · page `/ffa/mcompass/search`)

> Compass is the platform's first-party data analytics surface. It exposes a wide variety of analytical endpoints under `/compass_api/*`. These are the **gold seam** for the dashboard layer — for many dashboards we can avoid computing aggregates ourselves and just ingest Compass output.

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | GET | `/compass_api/shop/mall/dd_search/search_analysis/core_data` | `date_type`, `begin_date`, `end_date`, `activity_id`, `operate_type`, `content_type` | **Search core data** (pay_amt etc.) |
| **P0** | GET | `/compass_api/shop/mall/dd_search/search_analysis/core_data_trend_v2` | `index_name=pay_amt`, `trend_type`, `version=1`, plus date params | Time-series trend per index |
| P1 | GET | `/compass_api/shop/mall/dd_search/search_analysis/weekly_report_summary` | — | Weekly summary |
| P1 | GET | `/compass_api/shop/mall/dd_search/search_analysis/optimize_effect_agg` | `action_type=1..5` | Optimization effect aggregations (5 action types) |
| P1 | GET | `/compass_api/shop/mall/search_diagnosis/tab_num_v2` | date params | Diagnosis tab counts |
| P1 | GET | `/compass_api/shop/mall/search_diagnosis/optimize_list` | — | Diagnosis optimization list |
| P1 | GET | `/compass_api/shop/mall/search_diagnosis/product_label_list` | — | Product labels for diagnosis |
| P1 | GET | `/compass_api/shop/mall/search_diagnosis/batch_tool_card_v2` | `source_biz_type=3`, date params | Batch tool card |
| P1 | GET | `/compass_api/shop/mall/search_diagnosis/recommend_optimized_product_v2` | `tab_type=1`, `page_no=1`, `page_size=3`, `sort_type=1`, date params | **Recommended products to optimize** |
| P1 | GET | `/compass_api/shop/mall/shop_rank/search_v2` | `source_biz_type=3`, `sort_field=pay_amt` | Shop rank in category |
| P1 | GET | `/compass_api/shop/mall/search_analysis/industry_words/doudian_rank_v3` | `industry_id`, `category_id`, `total_cate_id`, `rank_type=5`, `page_no`, `page_size`, `sort_field`, `is_asc` | **Industry keyword ranking** (selection / trend mining input) |
| P1 | GET | `/compass_api/shop/mall/dd_search/after_watch/shop_video_list` | `video_date_info={…}`, `audit_status`, `content_type=-1`, `trailer_type`, `page_no`, `page_size`, `scene_type=1`, date params | **Shop video list with stats** |
| P1 | GET | `/compass_api/shop/mall/dd_search/after_watch/video_cnt_v2` | date params | Video count |
| P1 | GET | `/compass_api/shop/mall/dd_search/after_watch/default_tab` | — | Default tab |
| P1 | GET | `/compass_api/shop/mall/dd_search/after_watch/benefit` | — | Benefit/incentive info |
| P1 | GET | `/compass_api/shop/mall/dd_search/after_watch/permission_v2` | `item_type=1` / `2` | Permission per item type |
| P1 | GET | `/compass_api/shop/mall/dd_search/search_ad_module/card_list` | — | Search-ads card list |
| P1 | GET | `/compass_api/shop/mall/search_analysis/top_reach_task_card` | `source_biz_type=3` | Top reach task card |
| P1 | GET | `/compass_api/shop/common/assignment_list` | `scene=104000300` | Common assignment list |
| P2 | GET | `/compass_api/config_center/data_range_v2` | `data_type=mall_search_core_data` / `search_operation_diagnosis` / `doudian_search_after_watch`, `path` | Data range config (use to derive valid date windows before scraping) |
| P2 | GET | `/compass_api/config_center/page_metric` | `path` | Page metric config |
| P2 | GET | `/compass_api/config_center/category/cate_list` | `scene=4` / `5`, `level=4`, `default_cate_to_level=2` | Category list |
| P2 | GET | `/compass_api/config_center/pc/common_libra` | `token`, `uid_type=12`, `app_id=4499`, `device_id=0`, `path_list[]=feature-shop-workshop` | Common libra (feature toggles) |
| P2 | GET | `/compass_api/shop/mall/search_diagnosis/permission` | — | Diagnosis permission check |
| P2 | GET | `/compass_api/shop/mall/bind_channel_account` | — | Bound channel accounts |
| P3 | GET | `/compass_api/fe_dynamic/page/schema/v2` | `pageKey=<md5>`, `needReachContents=true` | Page schema (front-end dynamic rendering descriptor) |

---

## 8 · Member operations 用户运营  (`_bid = ffa_vip` · page `/ffa/mvip/consumer`)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | POST | `/api/member/dashboard/v2/get_shop_dashboard_aggregate_data` | body: date range, indices | Shop member aggregate metrics |
| **P0** | POST | `/api/member/dashboard/v2/get_shop_dashboard_daily_data` | body: date range, indices | Daily member metrics |
| **P0** | POST | `/api/member/dashboard/v2/get_shop_dashboard_histogram_data` | body | Histogram (distribution) data |
| **P0** | GET | `/api/marketing/user_profile/get_audience_feature` | `userType=2` (members?), `referenceUserType=0` | **Audience profile / demographics** |
| P1 | GET | `/api/member/dashboard/get_data_date_range` | `source=7` | Available date range for member data |
| P1 | GET | `/api/member/dashboard/get_shop_member_sales_activity_list` | — | Member sales activity list |
| P1 | GET | `/api/marketing/member/shop_info` | `attr_list=official_account` | Shop info (member context) |
| P2 | GET | `/api/marketing/member/shop/get_pop_msg` | — | Popup message |
| P2 | POST | `/api/marketing/member/get_top_banner` | — | Top banner |
| P2 | GET | `/ecomauth/loginv1/session_check` | `sec_user_id`, `sec_subject_uid`, `login_source=doudian_pc_web`, `bus_type=1` | **Session check** — useful as a heartbeat to detect session expiry |

---

## 9 · IM (飞鸽)  (`_bid = ffa_menu` · sampled from every page)

| Priority | Method | Path | Key params | Purpose |
|:-:|:--|:--|:--|:--|
| **P0** | GET | `/api/scale_shop/doudian_im/shop/user/unread_count` | — | Unread message count (display-only; no auto-reply) |

*Auto-reply via IM stays out of scope; see `requirements.md` §2.*

---

## 10 · Cross-cutting / platform-AI endpoints

These show on most pages and are platform-wide AI / helpdesk / tracking. Useful to know they exist (and to **filter out** when capturing scraper traffic), not as primary data sources.

| Priority | Path | Purpose |
|:-:|:--|:--|
| P2 | `/doudian/ai/get_ai_page_config` | Per-page AI feature config (drives the "doudian xiaoer" chat assistant) |
| P2 | `/doudian/ai/search_config` | AI search box config |
| P2 | `/doudian/ai/common_suggest` | AI common-suggestion list |
| P2 | `/doudian/ai/get_async_task` | Poll async AI task |
| P2 | `/byteshop/helpdesk/ai_switch_config` | AI on/off toggle config |
| P2 | `/byteshop/helpdesk/check_version` | Helpdesk version |
| P2 | `/byteshop/helpdesk/get_rec_content` | Recommended content (helpdesk) |
| P3 | `/main_frame/feed_back/all/get_feedback_info` | Feedback collection |
| P3 | `/b/m/api/home/redirect` | Home redirect / navigation tracking |
| P3 | `/b/a/api/v1/reach/list` | "Reach" content list (banners / nudges) |
| P3 | `/b/a/api/v1/reach/user_opt/collect` | Track user opt on reach content |
| P3 | `https://lgw.jinritemai.com/api/v2/agw/app-base/list` | Long-gateway app base |
| P3 | `https://lf3-config.bytetcc.com/obj/tcc-config-web/...` | TCC config (CDN) — feature-flag values |
| P3 | `https://mon.zijieapi.com/monitor_browser/collect/batch/` | Bytedance browser monitoring (HTTP 204 telemetry) |

> **Scraper hygiene**: do not retain or replay anything under `mon.zijieapi.com`. Those are pure telemetry sinks and noisy. Filter them out at the `page.on("response")` layer.

---

## 11 · Shop identity discovered

Surfaced incidentally from `/stock/manage/drawer_gray`:
- `shop_id = 29867003`
- (account email registered: redacted from this document; lives in `.env` only)

The `aid` query parameter is `4272` on most `/api/order/*` and `/api/business/incubation/comment/*` calls. Treat as a per-application constant — likely the merchant-backend app id.

---

## A · Full menu map (57 entries observed on homepage)

Saved separately as machine-readable input to scrape-target generation. See [`docs/menu-map.md`](menu-map.md).

---

## B · What we have NOT yet probed

These exist in the menu but were skipped during recon for risk-control reasons (no more than ~7 pages from one IP/session in a short window):

- 千川推广 (`/ffa/ad/promotion-v2`) — V3
- 直播管理 (`/ffa/content-tool/shop-live`) — V2 candidate
- 短视频运营 (`/ffa/content-tool/short-video`) — V2 candidate
- 图文运营 (`/ffa/content-tool/image-text-operation`) — V2 candidate
- 商品诊断 (`/ffa/g/diagnose`) — V1 candidate
- 营销工具 / 优惠券 (`/ffa/marketing/home`, `/ffa/marketing/coupon/home`) — V2 candidate
- 物流相关页面 — V2 candidate
- 商家体验分 (`/ffa/eco/experience-score`) — P1 — single number, easy to scrape, drives KPI tile
- 店铺装修 (`/ffa/shop/decorate/selection/list`) — P3
- 店铺诊断 (`/ffa/growth-gov-shop/shop-risk`) — P1

Probe in implementation phase using the same recipe: navigate → wait 2s → `page.on("response")` for `/api/`/`/compass_api/` paths → record.
