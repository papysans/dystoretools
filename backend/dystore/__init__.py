import sys

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

__version__ = "0.1.0"
