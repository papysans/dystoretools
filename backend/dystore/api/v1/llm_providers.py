from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.session import get_session
from dystore.llm.registry import service
from dystore.llm.registry.schemas import ModelCreate, ModelUpdate, ProviderCreate, ProviderUpdate

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


@router.get("/providers")
async def list_providers(session: AsyncSession = Depends(get_session)) -> dict:
    providers = await service.list_providers(session)
    return {"items": [p.model_dump() for p in providers]}


@router.post("/providers")
async def create_provider(req: ProviderCreate, session: AsyncSession = Depends(get_session)) -> dict:
    provider = await service.create_provider(session, req)
    return provider.model_dump()


@router.patch("/providers/{provider_id}")
async def update_provider(provider_id: int, req: ProviderUpdate, session: AsyncSession = Depends(get_session)) -> dict:
    provider = await service.update_provider(session, provider_id, req)
    if provider is None:
        raise HTTPException(404, detail="provider not found")
    return provider.model_dump()


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        ok = await service.delete_provider(session, provider_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    if not ok:
        raise HTTPException(404, detail="provider not found")
    return {"deleted": provider_id}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: int, model_name: str | None = None, session: AsyncSession = Depends(get_session)) -> dict:
    return await service.test_provider(session, provider_id, model_name=model_name)


@router.get("/providers/{provider_id}/models:discover")
async def discover_models(provider_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    return await service.discover_models(session, provider_id)


@router.get("/models")
async def list_models(
    provider_id: int | None = None,
    chat_capable: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict:
    models = await service.list_models(session, provider_id=provider_id, chat_capable=chat_capable)
    return {"items": [m.model_dump() for m in models]}


@router.post("/models")
async def create_model(req: ModelCreate, session: AsyncSession = Depends(get_session)) -> dict:
    model = await service.create_model(session, req)
    return model.model_dump()


@router.patch("/models/{model_id}")
async def update_model(model_id: int, req: ModelUpdate, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        model = await service.update_model(session, model_id, req)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    if model is None:
        raise HTTPException(404, detail="model not found")
    return model.model_dump()


@router.delete("/models/{model_id}")
async def delete_model(model_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        ok = await service.delete_model(session, model_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    if not ok:
        raise HTTPException(404, detail="model not found")
    return {"deleted": model_id}
