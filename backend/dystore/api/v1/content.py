from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.content.generator import TemplateMissing, generate
from dystore.db.models import AiGeneration
from dystore.db.session import SessionLocal, get_session
from dystore.llm.accounting import hash_prompt

router = APIRouter(prefix="/api/v1/content", tags=["content"])


class GenerateRequest(BaseModel):
    kind: str
    goods_id: str
    extra_context: str = ""
    comment_payload: dict | None = None  # for kind=comment_reply: {rating: int, content: str}


class SaveEditRequest(BaseModel):
    output_text: str


@router.post("/generate")
async def generate_endpoint(req: GenerateRequest) -> dict:
    try:
        result = await generate(  # type: ignore[arg-type]
            req.kind,
            req.goods_id,
            extra_context=req.extra_context,
            comment_payload=req.comment_payload,
        )
    except TemplateMissing as e:
        raise HTTPException(400, detail=f"unknown content kind: {e}")
    except LookupError as e:
        raise HTTPException(404, detail=str(e))
    return {
        "ai_generation_id": result["ai_generation_id"],
        "kind": req.kind,
        "output_text": result["text"],
        "model": result["model"],
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
    }


@router.post("/{generation_id}/save-edit")
async def save_edit(generation_id: int, req: SaveEditRequest) -> dict:
    async with SessionLocal() as s:
        parent = (await s.execute(select(AiGeneration).where(AiGeneration.id == generation_id))).scalar_one_or_none()
        if parent is None:
            raise HTTPException(404, detail="generation not found")
        edited = AiGeneration(
            parent_id=parent.id,
            kind=parent.kind,
            input_hash=hash_prompt(req.output_text),  # edited text — re-hash for traceability
            output_text=req.output_text,
            model=parent.model,
            tokens_in=0,
            tokens_out=0,
            cost=0.0,
            created_at=datetime.utcnow(),
        )
        s.add(edited)
        await s.commit()
        await s.refresh(edited)
        return {"id": edited.id, "parent_id": parent.id, "kind": parent.kind}


@router.get("")
async def list_generations(
    kind: str | None = None,
    limit: int = Query(50, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    q = select(AiGeneration).order_by(desc(AiGeneration.id)).limit(limit)
    if kind:
        q = q.where(AiGeneration.kind == kind)
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "parent_id": r.parent_id,
            "kind": r.kind,
            "output_text": r.output_text,
            "model": r.model,
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
            "cost": r.cost,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
