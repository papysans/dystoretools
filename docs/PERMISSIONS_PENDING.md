# 待开通权限清单（账号 `3467276095@qq.com`）

> 验证方式：在已登录态 (host Chrome) 直接 `fetch()` 实测，全部返回 `{"code":"-10001","msg":"您无操作权限，请联系主账号管理员开设权限"}`。
> URL 路径都已确认正确（菜单 API + 实际页面前端调用都用这些路径）。

## 待主账号开权限的 7 个 spec

| spec target | 接口路径 | 数据用途 | 默认表 |
|---|---|---|---|
| `doudian_comment_list` | `GET /product/tcomment/commentList` | 全部评价（含 1-5 星） | `doudian_comment` |
| `doudian_comment_negative` | `GET /product/tcomment/getUnreplyNegativeCommentList` | 未回复差评列表 | `doudian_comment` |
| `doudian_comment_tags` | `GET /product/tcomment/getNegativeCommentTagsCount` | 差评高频标签 | `comment_tag_stat` |
| `doudian_comment_index_warning` | `GET /product/tcomment/commentIndexWarning` | 评分预警/扣分提醒 | `comment_index_warn` |
| `doudian_neg_comment_products` | `GET /product/tcomment/getNegativeCommentProductList` | 差评商品排行 | `neg_comment_product` |
| `doudian_order_tabcnt` | `GET /api/order/tabcnt?tabcnt_version=v1&tab=all` | 各订单状态 tab 数量 | `scrape_task_run`（拟改专表） |
| _(预留)_ `doudian_comment_statistics` | `GET /product/tcomment/statistics` | 评分汇总（已观察到前端调用） | TBD |

## 申请方式（抖店后台）

```
店铺设置 → 子账号与权限管理 → 角色管理
→ 编辑当前账号角色 → 勾选：
  ☐ 评价管理 - 查看评价列表
  ☐ 评价管理 - 差评管理
  ☐ 评价管理 - 评价统计/标签
  ☐ 评价管理 - 评分预警查看
  ☐ 订单管理 - 订单状态数量查看
```

## 权限到位后操作

**零代码改动**，直接重新触发即可：

```bash
for t in doudian_comment_list doudian_comment_negative doudian_comment_tags \
         doudian_comment_index_warning doudian_neg_comment_products \
         doudian_order_tabcnt; do
  curl -X POST "http://127.0.0.1:8080/api/v1/scrape/run?target=$t"
done
```

确认成功：

```bash
docker exec dystore-mysql mysql -uroot -p dystore -e "
SELECT target, status, items_count, error_msg
FROM scrape_task_run r1
WHERE id = (SELECT MAX(id) FROM scrape_task_run r2 WHERE r2.target = r1.target)
AND target LIKE 'doudian_comment%' OR target = 'doudian_order_tabcnt';"
```

成功的 spec 应当显示 `status=done` 且 `items_count > 0`。

## 已验证 shape（websearch + 行业惯例 + payload 留位）

为防止权限到位后还需要再 recon 一次，下表记录各接口的预期返回结构（基于抖店开放平台 OpenAPI 类似接口 + 前端代码对照）：

### `commentList`
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "comment_id": "...",
        "product_id": "...",
        "sku": "...",
        "content": "...",
        "rank": 5,
        "user_nick": "...",
        "create_time": 1700000000,
        "reply_status": 0,
        "has_appeal": false
      }
    ]
  }
}
```

### `getUnreplyNegativeCommentList`
同 commentList 结构，但 `rank ∈ {1,2,3}` 且 `reply_status=0`。

### `getNegativeCommentTagsCount`
```json
{"data": {"list": [{"scope":"shop","scope_id":"","tag":"质量差","neg_count":5,"total_count":20}]}}
```

### `commentIndexWarning`
```json
{"data": {"kind":"low_score","severity":"warn","payload":{...}}}
```

### `getNegativeCommentProductList`
```json
{"data": {"list": [{"product_id":"...","neg_count":3,"score":4.2}]}}
```

### `order/tabcnt`
```json
{"data": {"all":0,"pending_pay":0,"pending_ship":0,"shipped":0,"completed":0,"refunding":0}}
```

> spec YAML 已根据上述预期 shape 写好。当 -10001 替换为真实数据时，jsonpath/fields 应直接命中；若上线后字段名有出入，diagnostic（first payload dump）会立即暴露。
