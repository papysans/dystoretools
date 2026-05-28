from fastapi import APIRouter
from pydantic import BaseModel, Field

from dystore.core.settings_store import OVERRIDABLE_KEYS, get_all, set_many

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class UpdateRequest(BaseModel):
    values: dict[str, str | None] = Field(..., description="key→value map; empty string clears the override")


@router.get("")
async def list_settings() -> dict:
    """List all overridable settings with masked secrets and source label."""
    data = await get_all(mask_secrets=True)
    return {"keys": list(OVERRIDABLE_KEYS), "values": data}


@router.put("")
async def update_settings(req: UpdateRequest) -> dict:
    """Upsert one or more settings. Empty value clears the DB override (falls back to env)."""
    # Only persist values that have actually changed — i.e. don't echo back masked secrets as-is
    pairs = []
    for k, v in req.values.items():
        if k not in OVERRIDABLE_KEYS:
            continue
        if v is not None and "***" in v:
            # masked placeholder echoed back — skip, means user didn't edit it
            continue
        pairs.append((k, v))
    if pairs:
        await set_many(pairs)
    return {"updated": [k for k, _ in pairs]}
