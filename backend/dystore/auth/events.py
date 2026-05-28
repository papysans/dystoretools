"""Session-event persistence + WS broadcast."""
from datetime import datetime

from dystore.core.logging import get_logger
from dystore.db.models import SessionEvent
from dystore.db.session import SessionLocal
from dystore.ws.broker import publish

log = get_logger(__name__)

KIND_LOGIN_SUCCEEDED = "login_succeeded"
KIND_RISK_VERIFICATION_REQUIRED = "risk_verification_required"
KIND_SESSION_EXPIRED = "session_expired"
KIND_SESSION_READY = "session_ready"
KIND_SESSION_REQUIRED = "session_required"


async def emit_session_event(kind: str, payload: dict | None = None) -> None:
    payload = payload or {}
    now = datetime.utcnow()
    async with SessionLocal() as s:
        s.add(SessionEvent(kind=kind, payload_json=payload, occurred_at=now))
        await s.commit()
    await publish("auth-required", {"kind": kind, "payload": payload, "occurred_at": now.isoformat()})
    log.info("auth.event", kind=kind, payload=payload)
