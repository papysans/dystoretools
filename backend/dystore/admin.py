"""Kill switch CLI: pause / resume all scrapers immediately.

Usage:
    python -m dystore.admin pause
    python -m dystore.admin resume
    python -m dystore.admin status

Implemented as a Redis flag the scheduler checks at every window dispatch.
"""
import asyncio
import sys

from dystore.cache.redis import get_redis

KEY = "ws:admin:scraper_paused"


async def _set(value: bool) -> None:
    r = get_redis()
    if value:
        await r.set(KEY, "1")
    else:
        await r.delete(KEY)


async def is_paused() -> bool:
    r = get_redis()
    return (await r.get(KEY)) == "1"


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "pause":
        asyncio.run(_set(True))
        print("scrapers paused")
    elif cmd == "resume":
        asyncio.run(_set(False))
        print("scrapers resumed")
    elif cmd == "status":
        paused = asyncio.run(is_paused())
        print("paused" if paused else "running")
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
