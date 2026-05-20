import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.auth.cookie_import import import_cookies
from dystore.auth.login_flow import open_login_window
from dystore.db.models import SessionEvent
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/open-login-window")
async def open_login_window_endpoint() -> dict[str, str]:
    """Fire-and-forget: launches the visible Chromium login flow (host only — needs display)."""
    asyncio.create_task(open_login_window())
    return {"status": "launching"}


class CookieImport(BaseModel):
    raw: str


@router.post("/import-cookies")
async def import_cookies_endpoint(req: CookieImport) -> dict:
    try:
        return await import_cookies(req.raw)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"{type(e).__name__}: {e}")


@router.get("/status")
async def auth_status(session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(select(SessionEvent).order_by(desc(SessionEvent.id)).limit(1))
    ).scalar_one_or_none()
    if row is None:
        return {"last_event": None, "session_ready": False}
    return {
        "last_event": {
            "kind": row.kind,
            "occurred_at": row.occurred_at.isoformat(),
            "payload": row.payload_json,
        },
        "session_ready": row.kind in ("session_ready", "login_succeeded"),
    }
