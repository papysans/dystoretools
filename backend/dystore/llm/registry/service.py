from __future__ import annotations

import time

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import ChatConversation, LlmModel, LlmProvider
from dystore.llm.registry.crypto import decrypt_secret, encrypt_secret, fingerprint_secret
from dystore.llm.registry.schemas import (
    ModelCreate,
    ModelRead,
    ModelUpdate,
    ProviderCreate,
    ProviderRead,
    ProviderUpdate,
)

_NON_CHAT_MODEL_MARKERS = (
    "embedding",
    "embed",
    "rerank",
    "moderation",
    "audio",
    "tts",
    "whisper",
    "image",
)


def provider_to_read(row: LlmProvider, *, model_count: int = 0) -> ProviderRead:
    return ProviderRead(
        id=row.id,
        name=row.name,
        adapter_kind=row.adapter_kind,
        base_url=row.base_url,
        enabled=row.enabled,
        key_set=bool(row.api_key_encrypted),
        key_fingerprint=row.api_key_fingerprint,
        default_headers=row.default_headers_json,
        model_count=model_count,
    )


def model_to_read(row: LlmModel) -> ModelRead:
    return ModelRead(
        id=row.id,
        provider_id=row.provider_id,
        model_name=row.model_name,
        display_name=row.display_name,
        context_window=row.context_window,
        capabilities=list(row.capabilities_json or []),
        enabled=row.enabled,
        is_default_for_chat=row.is_default_for_chat,
    )


async def list_providers(session: AsyncSession) -> list[ProviderRead]:
    counts = (
        await session.execute(select(LlmModel.provider_id, func.count(LlmModel.id)).group_by(LlmModel.provider_id))
    ).all()
    count_by_provider = {provider_id: count for provider_id, count in counts}
    rows = (await session.execute(select(LlmProvider).order_by(LlmProvider.id))).scalars().all()
    return [provider_to_read(row, model_count=count_by_provider.get(row.id, 0)) for row in rows]


async def get_provider(session: AsyncSession, provider_id: int) -> LlmProvider | None:
    return (await session.execute(select(LlmProvider).where(LlmProvider.id == provider_id))).scalar_one_or_none()


async def create_provider(session: AsyncSession, req: ProviderCreate) -> ProviderRead:
    encrypted = encrypt_secret(req.api_key) if req.api_key else None
    row = LlmProvider(
        name=req.name,
        adapter_kind=req.adapter_kind,
        base_url=req.base_url.rstrip("/"),
        api_key_encrypted=encrypted,
        api_key_fingerprint=fingerprint_secret(req.api_key),
        default_headers_json=req.default_headers,
        enabled=req.enabled,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return provider_to_read(row)


async def update_provider(session: AsyncSession, provider_id: int, req: ProviderUpdate) -> ProviderRead | None:
    row = await get_provider(session, provider_id)
    if row is None:
        return None
    if req.name is not None:
        row.name = req.name
    if req.adapter_kind is not None:
        row.adapter_kind = req.adapter_kind
    if req.base_url is not None:
        row.base_url = req.base_url.rstrip("/")
    if req.default_headers is not None:
        row.default_headers_json = req.default_headers
    if req.enabled is not None:
        row.enabled = req.enabled
    if req.api_key is not None and req.api_key != "":
        row.api_key_encrypted = encrypt_secret(req.api_key)
        row.api_key_fingerprint = fingerprint_secret(req.api_key)
    await session.commit()
    await session.refresh(row)
    return provider_to_read(row)


async def delete_provider(session: AsyncSession, provider_id: int) -> bool:
    row = await get_provider(session, provider_id)
    if row is None:
        return False
    model_count = (
        await session.execute(select(func.count(LlmModel.id)).where(LlmModel.provider_id == provider_id))
    ).scalar_one()
    conversation_count = (
        await session.execute(select(func.count(ChatConversation.id)).where(ChatConversation.provider_id == provider_id))
    ).scalar_one()
    if model_count or conversation_count:
        raise ValueError("cannot delete provider while models or conversations reference it")
    await session.delete(row)
    await session.commit()
    return True


async def list_models(session: AsyncSession, provider_id: int | None = None, *, chat_capable: bool = False) -> list[ModelRead]:
    q = select(LlmModel).order_by(LlmModel.provider_id, LlmModel.model_name)
    if provider_id is not None:
        q = q.where(LlmModel.provider_id == provider_id)
    if chat_capable:
        q = q.where(LlmModel.enabled.is_(True))
    rows = (await session.execute(q)).scalars().all()
    if chat_capable:
        rows = [row for row in rows if "chat" in (row.capabilities_json or [])]
    return [model_to_read(row) for row in rows]


async def get_model(session: AsyncSession, model_id: int) -> LlmModel | None:
    return (await session.execute(select(LlmModel).where(LlmModel.id == model_id))).scalar_one_or_none()


async def create_model(session: AsyncSession, req: ModelCreate) -> ModelRead:
    if req.is_default_for_chat:
        await _clear_default_chat(session)
    row = LlmModel(
        provider_id=req.provider_id,
        model_name=req.model_name,
        display_name=req.display_name,
        context_window=req.context_window,
        capabilities_json=req.capabilities,
        enabled=req.enabled,
        is_default_for_chat=req.is_default_for_chat,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return model_to_read(row)


async def update_model(session: AsyncSession, model_id: int, req: ModelUpdate) -> ModelRead | None:
    row = await get_model(session, model_id)
    if row is None:
        return None
    if req.is_default_for_chat:
        if req.enabled is False:
            raise ValueError("default chat model must be enabled")
        await _clear_default_chat(session)
        row.is_default_for_chat = True
        row.enabled = True
    elif req.is_default_for_chat is False:
        row.is_default_for_chat = False
    if req.model_name is not None:
        row.model_name = req.model_name
    if req.display_name is not None:
        row.display_name = req.display_name
    if req.context_window is not None:
        row.context_window = req.context_window
    if req.capabilities is not None:
        row.capabilities_json = req.capabilities
    if req.enabled is not None:
        if row.is_default_for_chat and not req.enabled:
            raise ValueError("cannot disable the default chat model")
        row.enabled = req.enabled
    await session.commit()
    await session.refresh(row)
    return model_to_read(row)


async def delete_model(session: AsyncSession, model_id: int) -> bool:
    row = await get_model(session, model_id)
    if row is None:
        return False
    if row.is_default_for_chat:
        raise ValueError("cannot delete the default chat model")
    await session.delete(row)
    await session.commit()
    return True


async def test_provider(session: AsyncSession, provider_id: int, model_name: str | None = None) -> dict:
    provider = await get_provider(session, provider_id)
    if provider is None:
        return {"ok": False, "error": "provider_not_found"}
    model = model_name or await _first_model_name(session, provider_id)
    if not model:
        return {"ok": False, "error": "model_not_configured"}
    started = time.perf_counter()
    try:
        if provider.adapter_kind == "openai_compat":
            result = await _test_openai_compat(provider, model)
        elif provider.adapter_kind == "anthropic":
            result = await _test_anthropic(provider, model)
        else:
            return {"ok": False, "error": "unsupported_adapter"}
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "status_code": exc.response.status_code, "error": exc.response.text[:300]}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    return {"ok": True, "model": model, "latency_ms": int((time.perf_counter() - started) * 1000), **result}


async def discover_models(session: AsyncSession, provider_id: int) -> dict:
    provider = await get_provider(session, provider_id)
    if provider is None:
        return {"ok": False, "error": "provider_not_found"}
    try:
        model_ids = await _discover_model_ids(provider)
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "status_code": exc.response.status_code, "error": exc.response.text[:300]}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    return {"ok": True, "models": [{"id": model_id} for model_id in model_ids], "total": len(model_ids)}


async def sync_discovered_models(session: AsyncSession, provider_id: int) -> dict:
    provider = await get_provider(session, provider_id)
    if provider is None:
        return {"ok": False, "error": "provider_not_found"}
    try:
        model_ids = await _discover_model_ids(provider)
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "status_code": exc.response.status_code, "error": exc.response.text[:300]}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}

    rows = (
        await session.execute(select(LlmModel).where(LlmModel.provider_id == provider_id))
    ).scalars().all()
    by_name = {row.model_name: row for row in rows}
    created: list[LlmModel] = []

    for model_id in model_ids:
        if model_id in by_name:
            continue
        capabilities = _default_capabilities_for_model(model_id)
        row = LlmModel(
            provider_id=provider_id,
            model_name=model_id,
            display_name=model_id,
            context_window=None,
            capabilities_json=capabilities,
            enabled="chat" in capabilities,
            is_default_for_chat=False,
        )
        session.add(row)
        by_name[model_id] = row
        created.append(row)

    if created:
        await session.commit()
        for row in created:
            await session.refresh(row)

    synced_rows = [by_name[model_id] for model_id in model_ids if model_id in by_name]
    return {
        "ok": True,
        "total": len(model_ids),
        "created": len(created),
        "existing": len(model_ids) - len(created),
        "models": [model_to_read(row).model_dump() for row in synced_rows],
    }


async def _discover_model_ids(provider: LlmProvider) -> list[str]:
    if provider.adapter_kind == "openai_compat":
        return await _discover_openai_compat_model_ids(provider)
    if provider.adapter_kind == "anthropic":
        return await _discover_anthropic_model_ids(provider)
    raise ValueError("discovery_unsupported")


async def _discover_openai_compat_model_ids(provider: LlmProvider) -> list[str]:
    api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else ""
    headers = {"Content-Type": "application/json", **(provider.default_headers_json or {})}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{provider.base_url.rstrip('/')}/models", headers=headers)
        resp.raise_for_status()
    return _extract_model_ids(resp.json())


async def _discover_anthropic_model_ids(provider: LlmProvider) -> list[str]:
    api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else ""
    headers = {
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        **(provider.default_headers_json or {}),
    }
    if api_key:
        headers["x-api-key"] = api_key
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{provider.base_url.rstrip('/')}/v1/models", headers=headers)
        resp.raise_for_status()
    return _extract_model_ids(resp.json())


def _extract_model_ids(payload: dict) -> list[str]:
    data = payload.get("data")
    items = data if isinstance(data, list) else payload.get("models", [])
    seen: set[str] = set()
    model_ids: list[str] = []
    for item in items:
        if isinstance(item, str):
            model_id = item
        elif isinstance(item, dict):
            model_id = item.get("id") or item.get("name")
        else:
            continue
        if not isinstance(model_id, str) or not model_id or model_id in seen:
            continue
        seen.add(model_id)
        model_ids.append(model_id)
    return model_ids


def _default_capabilities_for_model(model_id: str) -> list[str]:
    lowered = model_id.lower()
    if any(marker in lowered for marker in _NON_CHAT_MODEL_MARKERS):
        return []
    return ["chat", "streaming", "function_calling"]


async def _clear_default_chat(session: AsyncSession) -> None:
    await session.execute(update(LlmModel).values(is_default_for_chat=False))


async def _first_model_name(session: AsyncSession, provider_id: int) -> str | None:
    row = (
        await session.execute(
            select(LlmModel).where(LlmModel.provider_id == provider_id, LlmModel.enabled.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    return row.model_name if row else None


async def _test_openai_compat(provider: LlmProvider, model: str) -> dict:
    api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else ""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **(provider.default_headers_json or {})}
    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1, "stream": False}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{provider.base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    return {"upstream": "openai_compat"}


async def _test_anthropic(provider: LlmProvider, model: str) -> dict:
    api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else ""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        **(provider.default_headers_json or {}),
    }
    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{provider.base_url.rstrip('/')}/v1/messages", headers=headers, json=payload)
        resp.raise_for_status()
    return {"upstream": "anthropic"}
