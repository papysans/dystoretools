"""URLs to ignore in the response interceptor (telemetry, CDN, monitoring)."""
TELEMETRY_HOST_FRAGMENTS = (
    "mon.zijieapi.com",
    "lf3-config.bytetcc.com",
    "lf3-fe.ecombdstatic.com",
    "lf-ecom-gr-sourcecdn.bytegecko.com",
    "lf3-static.bytednsdoc.com",
    "monitor_browser",
    "/static/",
    ".js",
    ".css",
    ".woff",
    ".png",
    ".jpg",
    ".svg",
)


def is_telemetry(url: str) -> bool:
    return any(frag in url for frag in TELEMETRY_HOST_FRAGMENTS)
