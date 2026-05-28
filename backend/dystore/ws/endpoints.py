"""WebSocket endpoints: bridge Redis pub-sub to connected clients."""
import asyncio
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dystore.core.logging import get_logger
from dystore.ws.broker import subscribe

log = get_logger(__name__)

router = APIRouter()


async def _bridge(channel: str, ws: WebSocket) -> None:
    await ws.accept()
    try:
        async for msg in subscribe(channel):
            await ws.send_json(msg)
    except WebSocketDisconnect:
        log.info("ws.disconnect", channel=channel)
    except Exception as e:
        log.warning("ws.error", channel=channel, error=str(e))
    finally:
        with suppress(Exception):
            await ws.close()


@router.websocket("/ws/auth-required")
async def ws_auth_required(ws: WebSocket) -> None:
    await _bridge("auth-required", ws)


@router.websocket("/ws/tasks")
async def ws_tasks(ws: WebSocket) -> None:
    await _bridge("tasks", ws)


@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket) -> None:
    await _bridge("alerts", ws)


@router.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    await _bridge("dashboard", ws)
