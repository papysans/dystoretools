"""Cookie import — accept exported cookies from the user's host browser and
persist them into the docker-resident Playwright persistent context.

This sidesteps the "no X server in container" problem: the user logs in once
on their host browser (where they can see the OTP / risk verification), then
exports cookies via any browser extension (EditThisCookie, Cookie-Editor, etc.)
and pastes the JSON here.

Accepted formats:
- "EditThisCookie" JSON array
- "Cookie-Editor" JSON array (similar shape)
- Generic Playwright `state.cookies` JSON array

Common fields across all formats:
- name, value, domain, path, expirationDate (or expires), httpOnly, secure, sameSite
"""
from __future__ import annotations

import json
from typing import Any

from dystore.auth.events import KIND_LOGIN_SUCCEEDED, KIND_SESSION_READY, emit_session_event
from dystore.auth.persistent_context import merchant_context
from dystore.core.logging import get_logger

log = get_logger(__name__)


def _normalise(c: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one cookie row from any common export shape to Playwright's expected schema."""
    name = c.get("name")
    value = c.get("value")
    domain = c.get("domain")
    if not (name and value and domain):
        return None
    path = c.get("path") or "/"
    expires = c.get("expirationDate") or c.get("expires")
    same_site_raw = (c.get("sameSite") or "Lax")
    same_site_map = {
        "no_restriction": "None",
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": "Lax",
        "None": "None",
        "Lax": "Lax",
        "Strict": "Strict",
    }
    same_site = same_site_map.get(str(same_site_raw), "Lax")
    out: dict[str, Any] = {
        "name": str(name),
        "value": str(value),
        "domain": str(domain),
        "path": str(path),
        "secure": bool(c.get("secure", False)),
        "httpOnly": bool(c.get("httpOnly", False)),
        "sameSite": same_site,
    }
    if expires:
        try:
            out["expires"] = float(expires)
        except (TypeError, ValueError):
            pass
    return out


def parse_cookies(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw)
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of cookie objects")
    out: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        normalised = _normalise(row)
        if normalised:
            out.append(normalised)
    return out


async def import_cookies(raw: str) -> dict:
    """Parse + apply cookies to the merchant context's persistent profile."""
    parsed = parse_cookies(raw)
    if not parsed:
        return {"imported": 0, "error": "no usable cookies in payload"}

    # Only import cookies for the jinritemai / bytedance domains we care about.
    allowed_domains = (".jinritemai.com", "jinritemai.com", ".bytedance.com", "bytedance.com", ".oceanengine.com")
    filtered = [c for c in parsed if any(c["domain"].endswith(d.lstrip(".")) for d in allowed_domains)]
    if not filtered:
        return {"imported": 0, "error": "no cookies match merchant domains (.jinritemai.com etc.)"}

    async with merchant_context(headless=True) as ctx:
        await ctx.add_cookies(filtered)  # persisted in user_data_dir on close
        log.info("auth.cookies_imported", count=len(filtered))

    await emit_session_event(KIND_LOGIN_SUCCEEDED, {"via": "cookie_import", "count": len(filtered)})
    await emit_session_event(KIND_SESSION_READY, {"via": "cookie_import"})
    return {"imported": len(filtered), "total_provided": len(parsed)}
