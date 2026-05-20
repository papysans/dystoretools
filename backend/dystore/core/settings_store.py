"""Runtime settings — DB-backed overrides for selected .env values.

Looks up `AppSetting` rows first; falls back to env-derived `Settings`.
Caches per-process for 30 seconds to avoid hitting the DB on every LLM call.
"""
from __future__ import annotations

import time
from collections.abc import Iterable

from sqlalchemy import select

from dystore.core.config import get_settings
from dystore.db.models import AppSetting
from dystore.db.session import SessionLocal

# Settings that may be overridden via UI. Other Settings fields stay env-only.
OVERRIDABLE_KEYS = (
    "deepseek_api_key",
    "deepseek_base_url",
    "deepseek_model",
    "kimi_api_key",
    "kimi_base_url",
    "kimi_model",
    "merchant_browser_mode",
    "merchant_cdp_url",
    "public_scraper_backend",
    "huitu_api_key",
    "chanmama_api_key",
    "peer_shop_ids",
)

SECRET_KEYS = ("deepseek_api_key", "kimi_api_key", "huitu_api_key", "chanmama_api_key")

_cache: dict[str, str | None] = {}
_cache_at: float = 0.0
_TTL = 30.0


def invalidate_cache() -> None:
    global _cache_at
    _cache_at = 0.0


async def _load_into_cache() -> None:
    global _cache, _cache_at
    async with SessionLocal() as s:
        rows = (await s.execute(select(AppSetting).where(AppSetting.key.in_(OVERRIDABLE_KEYS)))).scalars().all()
    _cache = {r.key: r.value for r in rows}
    _cache_at = time.time()


async def get(key: str) -> str | None:
    """Returns the effective value: DB override → env value."""
    if key not in OVERRIDABLE_KEYS:
        raise KeyError(f"not an overridable setting: {key}")
    if time.time() - _cache_at > _TTL:
        await _load_into_cache()
    if key in _cache and _cache[key]:
        return _cache[key]
    return getattr(get_settings(), key, None)


async def get_all(*, mask_secrets: bool = True) -> dict[str, dict]:
    """Return every overridable key with effective value + source label."""
    if time.time() - _cache_at > _TTL:
        await _load_into_cache()
    env_settings = get_settings()
    out: dict[str, dict] = {}
    for k in OVERRIDABLE_KEYS:
        db_val = _cache.get(k)
        env_val = getattr(env_settings, k, None)
        effective = db_val if db_val else env_val
        is_secret = k in SECRET_KEYS
        display: str | None
        if is_secret and effective and mask_secrets:
            display = _mask(effective)
        else:
            display = effective
        out[k] = {
            "value": display,
            "kind": "secret" if is_secret else "string",
            "source": "db" if db_val else ("env" if env_val else "none"),
            "has_value": bool(effective),
        }
    return out


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


async def set_many(values: Iterable[tuple[str, str | None]]) -> None:
    """Upsert (key, value) pairs. Passing value=None or empty string deletes the override."""
    async with SessionLocal() as s:
        for key, value in values:
            if key not in OVERRIDABLE_KEYS:
                raise KeyError(f"not an overridable setting: {key}")
            row = (await s.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
            if value is None or value == "":
                if row:
                    await s.delete(row)
            else:
                kind = "secret" if key in SECRET_KEYS else "string"
                if row is None:
                    s.add(AppSetting(key=key, value=value, kind=kind))
                else:
                    row.value = value
                    row.kind = kind
        await s.commit()
    invalidate_cache()
