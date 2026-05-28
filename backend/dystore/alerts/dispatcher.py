"""Alert dispatcher: persist + broadcast typed alerts."""
from datetime import datetime
from typing import Any

from dystore.core.logging import get_logger
from dystore.db.models import Alert
from dystore.db.session import SessionLocal
from dystore.ws.broker import publish

log = get_logger(__name__)

ALLOWED_KINDS = {
    "negative_comment_surge",
    "aftersale_deadline_approaching",
    "aftersale_urge",
    "aftersale_arbitrate_pending",
    "low_stock",
    "dead_stock",
    "sales_anomaly_drop",
    "sales_anomaly_spike",
    "shop_violation",
    "experience_score_drop",
    "compass_warning",
}

ALLOWED_SEVERITIES = {"info", "warn", "critical"}


async def fire(kind: str, severity: str, payload: dict[str, Any]) -> int:
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unknown alert kind: {kind}")
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"unknown severity: {severity}")
    now = datetime.utcnow()
    async with SessionLocal() as s:
        row = Alert(kind=kind, severity=severity, payload_json=payload, dispatched_at=now)
        s.add(row)
        await s.commit()
        await s.refresh(row)
    await publish("alerts", {"id": row.id, "kind": kind, "severity": severity, "payload": payload, "dispatched_at": now.isoformat()})
    log.info("alert.fired", kind=kind, severity=severity, payload=payload)
    return row.id
