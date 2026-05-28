from functools import lru_cache

import redis.asyncio as redis

from dystore.core.config import get_settings

NS_COOKIES = "cookies"
NS_TASKS = "tasks"
NS_RATELIMIT = "ratelimit"
NS_WS = "ws"


def key(namespace: str, *parts: str) -> str:
    return ":".join((namespace, *parts))


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
