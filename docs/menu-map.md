# dystoretools — Merchant Backend Menu Map

> All 57 navigable modules surfaced from the merchant homepage (`/ffa/mshop/homepage/index?from=buyin`) on 2026-05-18.
> Grouped by domain for easier prioritization. The `Tier` column maps to the V1/V2/V3 scoping decision; **bold rows are confirmed-probed** (see [`api-catalog.md`](api-catalog.md)).

| Tier | Domain | Module (Chinese) | URL |
|:-:|--------|------------------|-----|
| **V1** | 商品 | **商品管理** | `/ffa/g/list` |
| **V1** | 商品 | **库存管理** | `/ffa/g/stock-manage/list` |
| V1 | 商品 | 商品创建 | `/ffa/g/create` |
| V1 | 商品 | 商品诊断 | `/ffa/g/diagnose` |
| V2 | 商品 | 渠道品管理 | `/ffa/g/channel-goods/list` |
| V2 | 商品 | 商品工具 | `/ffa/menu_tools/goods_tools` |
| V2 | 商品 | 商品素材 | `/ffa/creative/material-production` |
| V3 | 商品 | 源头好货 | `/ffa/distribution-selected/?from=ddpc.menu` |
| V3 | 商品 | 竞拍管理 | `/ffa/industry-auction/?from=ddpc.menu` |
| **V1** | 订单 | **订单管理** | `/ffa/morder/order/list` |
| V1 | 订单 | 卡券管理 (O2O) | `/ffa/morder/o2o/poi-verify` |
| V1 | 订单 | 订单报备 | `/ffa/govern-order-report/order_entry` |
| **V1** | 售后 | **售后工作台** | `/ffa/merchant-aftersale-workbench/aftersale/list` |
| **V1** | 售后 | **评价管理** | `/ffa/maftersale/comment` |
| V1 | 售后 | 售后小助手 | `/ffa/maftersale/aftersale/assistant/multi-assist` |
| V1 | 售后 | 售后挽单助手 | `/ffa/maftersale/aftersale/redeem/assistant` |
| V2 | 售后 | 消费者权益 | `/ffa/maftersale/privileges` |
| V2 | 售后 | 小额打款 | `/ffa/maftersale/aftersale/part-pay` |
| **V2** | 数据 | **搜索运营 (罗盘)** | `/ffa/mcompass/search` |
| V2 | 数据 | 店铺诊断 | `/ffa/growth-gov-shop/shop-risk?no_tab=1` |
| V1 | 数据 | 商家体验分 | `/ffa/eco/experience-score?source=fxg-menu` |
| **V2** | 用户 | **用户运营** | `/ffa/mvip/consumer` |
| V2 | 用户 | 用户触达 | `/ffa/mvip/operation/plan` |
| V2 | 用户 | 会员运营 | `/ffa/mvip/member` |
| V2 | 用户 | 会员权益 | `/ffa/mvip/rights` |
| V2 | 内容 | 短视频运营 | `/ffa/content-tool/short-video` |
| V3 | 内容 | AI智能成片 | `/ffa/content-tool/ai-generate-video?from=doudian.caidan` |
| V2 | 内容 | 直播管理 | `/ffa/content-tool/shop-live` |
| V2 | 内容 | 图文运营 | `/ffa/content-tool/image-text-operation` |
| V2 | 内容 | 推荐卡运营 | `/ffa/recommend-card/home` |
| V2 | 营销 | 营销工具 | `/ffa/marketing/home` |
| V2 | 营销 | 优惠券 | `/ffa/marketing/coupon/home` |
| V2 | 营销 | 单品直降 | `/ffa/marketing/tools/limitsales` |
| V2 | 营销 | 营销管理 | `/ffa/marketing/discount-query` |
| V2 | 营销 | 优价推手 | `/ffa/priceTool/optimizePrice` |
| V2 | 营销 | 活动广场 | `/ffa/merchant/campaign-square` |
| V2 | 营销 | 超值购报名 | `/ffa/merchant/super-sale` |
| V2 | 营销 | 秒杀报名 | `/ffa/merchant/sec-kill` |
| V3 | 广告 | 千川推广 | `/ffa/ad/promotion-v2?utm_source=qianchuan-origin-entrance&utm_medium=doudian-pc&utm_campaign=tuiguangtab` |
| V2 | 物流 | 发货中心 | `/ffa/morder/logistics/ewaybill-delivery` |
| V2 | 物流 | 物流工具 | `/ffa/morder/logistics/freight-list` |
| V2 | 物流 | 电子面单 | `/ffa/logistics-project/eBill/landing` |
| V2 | 物流 | 物流服务 | `/ffa/logistics-project/logistics-service/main` |
| V2 | 物流 | 物流诊断 | `/ffa/logistics-project/diagnosis/index` |
| V2 | 物流 | 快递拦截管理 | `/ffa/logistics/logistics/interceptModule` |
| V2 | 服务 | 服务工单 | `/ffa/task-order/service` |
| V3 | 服务 | 托管管理 | `/ffa/smart-hosting/home` |
| V2 | 店铺 | 店铺管理 | `/ffa/grs-new/qualification/common-tools` |
| V3 | 店铺 | 店铺装修 | `/ffa/shop/decorate/selection/list` |
| V2 | 店铺 | 抖音账号管理 | `/ffa/w/bind/list` |
| V3 | 店铺 | 子账号授权 | `/ffa/w/subaccount/apply` |
| V1 | 治理 | 违规管理 | `/ffa/govern-guarantee/regulation` |
| V1 | 治理 | 店铺保障 | `/ffa/govern-guarantee/overview` |
| V1 | 治理 | 申诉中心 | `/ffa/govern-guarantee/appeal` |
| V3 | 治理 | 申请关店 | `/ffa/gov/closeV2` |
| V2 | 商城 | 商城运营 | `/ffa/growth-common/growth-shelf` |
| V2 | 商城 | 商家权益 | `/ffa/growth-merchant/rights?source=fxg-menu` |
