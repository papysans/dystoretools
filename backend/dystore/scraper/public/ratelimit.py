"""Per-domain rate limiter using Redis token-bucket-ish counter."""
import asyncio
import time
from urllib.parse import urlparse

from dystore.cache.redis import NS_RATELIMIT, get_redis, key

DEFAULT_INTERVAL = 6.0  # seconds — at most one request per 6s per domain


async def wait_for_slot(url: str, *, interval: float = DEFAULT_INTERVAL) -> None:
    domain = urlparse(url).netloc
    r = get_redis()
    k = key(NS_RATELIMIT, "public", domain)
    while True:
        now = time.time()
        last = float(await r.get(k) or 0)
        delta = now - last
        if delta >= interval:
            await r.set(k, now, ex=int(interval * 4))
            return
        await asyncio.sleep(interval - delta + 0.05)
