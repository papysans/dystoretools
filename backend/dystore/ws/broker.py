"""Redis pub-sub backed WebSocket broadcaster.

Channels: auth-required, tasks, alerts, dashboard.
"""
import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import suppress

from dystore.cache.redis import get_redis
from dystore.core.logging import get_logger

log = get_logger(__name__)

CHANNELS = ("auth-required", "tasks", "alerts", "dashboard")


def _channel_key(name: str) -> str:
    return f"ws:{name}"


async def publish(channel: str, payload: dict) -> None:
    assert channel in CHANNELS, f"unknown channel {channel}"
    r = get_redis()
    await r.publish(_channel_key(channel), json.dumps(payload, ensure_ascii=False))


async def subscribe(channel: str) -> AsyncIterator[dict]:
    assert channel in CHANNELS, f"unknown channel {channel}"
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel_key(channel))
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                log.warning("ws.bad_payload", channel=channel, raw=data)
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(_channel_key(channel))
            await pubsub.close()
