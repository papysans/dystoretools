import hashlib
from datetime import datetime

from dystore.db.models import AiGeneration
from dystore.db.session import SessionLocal


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


async def record_success(
    *,
    kind: str,
    prompt: str,
    output_text: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost: float = 0.0,
    parent_id: int | None = None,
) -> int:
    async with SessionLocal() as s:
        row = AiGeneration(
            parent_id=parent_id,
            kind=kind,
            input_hash=hash_prompt(prompt),
            output_text=output_text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            created_at=datetime.utcnow(),
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row.id


async def record_failure(*, kind: str, prompt: str, model: str, error_msg: str) -> int:
    async with SessionLocal() as s:
        row = AiGeneration(
            kind=kind,
            input_hash=hash_prompt(prompt),
            output_text=None,
            model=model,
            tokens_in=0,
            tokens_out=0,
            cost=0.0,
            error_msg=error_msg[:1024],
            created_at=datetime.utcnow(),
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row.id
