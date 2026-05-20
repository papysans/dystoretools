# Scraping Patterns — fxg.jinritemai.com

> Engineering reference for the **MerchantScraper** and **PublicScraper** subsystems.
> Findings below come from a live recon session on 2026-05-18 against the merchant backend; treat any specific endpoint URL as confirmed-as-of-then, not as forever-stable.

---

## 1 · The fundamental constraint

Every API call to `fxg.jinritemai.com/api/*` carries these query parameters:

```
appid=1
__token=<32-char hex, stable per login session>
_bid=<page biz id, e.g. ffa_order / ffa_menu>
aid=<numeric application id, e.g. 4272>
_lid=<numeric, monotonically increasing, unique per request>
msToken=<long opaque base64, refreshes every few minutes>
a_bogus=<long opaque base64, REGENERATED FOR EVERY REQUEST>
verifyFp=verify_<...>   (browser fingerprint)
fp=verify_<...>         (same value as verifyFp, both required)
```

`a_bogus` is a per-request **signature** produced by heavily obfuscated bytedance JavaScript running on the page. The algorithm consumes: the request URL, the request body, the fingerprint, the `msToken`, and timing. **Reversing it is possible but a moving target** — bytedance ships new sign versions roughly every quarter. Any in-Python re-implementation will rot.

**Therefore:** we do not implement the signing algorithm. We let the page compute it for us by triggering real user-like navigation in Playwright and **intercepting the response**.

---

## 2 · Authentication flow (observed 2026-05-18)

```
1. GET https://fxg.jinritemai.com/ffa/mshop/homepage/index?from=buyin
     └─→ 302 → /login/common?extra=...   (no session)

2. User picks 邮箱登录 tab (DOM toggle)

3. Form filled: email, password, agreement checkbox

4. POST submits. Possible outcomes:
     a. Direct success → 302 back to target_url
     b. RISK VERIFICATION surfaces inline:
          "系统判断当前操作存在风险，请进行安全验证"
        with an email-OTP input box.
        Triggered when:
          - new IP / new browser fingerprint
          - first login after long inactivity
          - too many failed attempts
        Flow:
          - User clicks 发送验证码
          - Email arrives at the registered address with a 6-char alphanumeric code
          - User pastes code → 验证 → success → 302 back

5. Session cookies set under .jinritemai.com:
     - SESSIONID-style server cookies
     - browser-side localStorage holds __token, verifyFp, fingerprint
     - msToken refreshed by an XHR every few minutes
```

Once authenticated, navigation to any `/ffa/*` page renders the React app and fires the relevant `/api/*` calls automatically.

---

## 3 · Why we don't replay requests with httpx

The illustrative anti-pattern:

```python
# DO NOT DO THIS
cookies = await playwright_context.cookies()
async with httpx.AsyncClient(cookies=cookies) as c:
    r = await c.get("https://fxg.jinritemai.com/api/order/searchlist", params={"page": 0, ...})
    # → 200 with {"code": ..., "msg": "签名校验失败"} or 403
```

Reason: cookies are sufficient for *authentication*, but `a_bogus` is an *integrity* signature checked separately on every request. Without it, the server returns an error envelope.

Even if you scrape `msToken` from the page, you still need to compute a fresh `a_bogus` per request — and the algorithm is JS-only.

---

## 4 · The interceptor pattern (do this instead)

```python
# Pseudocode — replace with real types in implementation
from playwright.async_api import async_playwright, Page, Response

async def scrape_order_list(page: Page) -> list[dict]:
    captured: list[dict] = []

    async def on_response(resp: Response) -> None:
        if "/api/order/searchlist" in resp.url and resp.request.method == "GET":
            try:
                captured.append(await resp.json())
            except Exception:
                pass  # non-JSON or aborted; ignore

    page.on("response", on_response)
    try:
        await page.goto("https://fxg.jinritemai.com/ffa/morder/order/list",
                        wait_until="networkidle")
        # Give the SPA time to dispatch its initial queries
        await page.wait_for_timeout(2500)
    finally:
        page.remove_listener("response", on_response)

    return captured
```

For paginated data, drive pagination through the UI (click "next page" or change a query string and re-navigate) so the page re-signs each request itself.

For pages where the data isn't auto-fetched, use `page.evaluate("() => window.someStore.fetch(...)")` to call the page's own client code — that code path internally computes `a_bogus`.

---

## 5 · Declarative scraper spec format

Each scrape target is described by a YAML file under `backend/dystore/scraper/specs/`. The runtime loads the spec, navigates, intercepts, parses, and upserts. No per-target Python class.

```yaml
# specs/doudian_order.yml
target: doudian_order
subsystem: merchant            # merchant | public
nav:
  url: https://fxg.jinritemai.com/ffa/morder/order/list
  wait_until: networkidle
  settle_ms: 2500
schedule:
  cron: "10 0,7,10,12,15,18,21 * * *"   # see docs/requirements.md §7
intercept:
  - url_contains: /api/order/searchlist
    method: GET
extract:
  jsonpath: $.data.list[*]
  fields:
    order_sn:      $.order_sn
    goods_name:    $.product_name
    sale_num:      $.item_num
    order_amount:  $.pay_amount
    pay_time:      $.pay_time
    status:        $.status
sink:
  table: doudian_order
  upsert_key: order_sn
  store_raw: true                    # raw_json column receives full upstream object
```

Adding a new target = one YAML file. No new Python code unless the page needs custom interaction (in which case add a `pre_actions:` list of click/fill/select steps).

---

## 6 · Session persistence

We **never** re-login programmatically. Login is a one-time human action, performed in a visible (headed) Chromium window using a persistent context directory:

```python
ctx = await chromium.launch_persistent_context(
    user_data_dir=Path.home() / ".dystore/playwright/doudian",
    headless=False,                 # MerchantScraper: headed by default
    channel="chrome",               # use installed Chrome, not Playwright's bundled Chromium
    viewport={"width": 1440, "height": 900},
    locale="zh-CN",
    timezone_id="Asia/Shanghai",
    user_agent=None,                # let real Chrome decide
)
```

`user_data_dir` keeps cookies, localStorage, indexedDB, and service-worker state between runs. A typical 抖店 session is good for **7–30 days** before re-authentication is required.

**Session expiry detection.** Before every navigation, the scraper checks the post-navigation URL:

```python
await page.goto(target_url, wait_until="domcontentloaded")
if "/login/common" in page.url:
    await redis.publish("auth-required", {"reason": "session_expired"})
    raise SessionExpired()
```

The frontend's `/ws/auth-required` listener pops up the visible Chromium window so the user can complete login (and any risk verification) by hand. The scraper resumes automatically once it sees a non-login URL.

---

## 7 · Anti-detection essentials

1. **Use installed real Chrome (`channel="chrome"`)** — Playwright's bundled Chromium has different fingerprints that bytedance's risk engine sometimes scores worse.
2. **`playwright-stealth`** plugin to mask `navigator.webdriver`, plugin lists, WebGL vendor strings, etc.
3. **Human-like timing**: random delays 3–10 s between actions; random scroll before reading data; never zero-wait clicks.
4. **No 0–6 am access** to merchant backend (see requirements §7). The risk engine weights timing heavily.
5. **Single concurrency per domain.** Two parallel scrapes from the same account on the same domain is the highest-leverage anomaly signal.
6. **Don't clear cookies** between runs. Risk engine treats a "fresh browser" with valid login as more suspicious than a "stale browser" that has been around.
7. **Don't change viewport / locale / timezone** between runs. Stable fingerprint = lower risk score.
8. **PublicScraper** (V2) runs in headless mode with a cookie pool and proxy rotation — physically isolated from the merchant scraper. Never share cookies or IPs between the two.

---

## 8 · Observed endpoints catalogue

The full empirical catalogue lives in [`api-catalog.md`](api-catalog.md). It groups ~70 confirmed endpoints across 7 modules — orders, products, inventory, comments, aftersale, compass (search-ops analytics), member operations — with priority tiers (P0–P3) that map to the V1/V2/V3 phasing in [`requirements.md`](requirements.md) §4.

Likewise the homepage's full menu structure (57 modules across 商品 / 订单 / 售后 / 数据 / 用户 / 内容 / 营销 / 广告 / 物流 / 服务 / 店铺 / 治理 / 商城) is captured in [`menu-map.md`](menu-map.md).

The catalogue should be regenerated periodically from `scrape_task_run` logs once the scraper is in production — bytedance rotates these URLs slowly but persistently.

---

## 9 · Open questions for implementation phase

- Does the page ever expose data via WebSocket instead of XHR? (We saw none in recon, but worth a re-check on the IM page.)
- Does pagination beyond ~10 pages trigger additional risk checks? (Empirically test before turning on full-history backfill.)
- Are there RPC endpoints (`/rpc/<Service>/<Method>` style) that batch multiple data calls? (PDF1's `GetAllDict` hint suggests yes.)
- For 商品 / 评论 pages — confirm endpoint URLs in the same way we confirmed `/api/order/searchlist`.
- How long does `__token` remain valid for? (Observed stable for >30 minutes in the recon session; need to probe the actual TTL.)
