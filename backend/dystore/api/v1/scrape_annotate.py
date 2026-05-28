from fastapi import APIRouter

from dystore.analysis.comment_worker import annotate_pending

router = APIRouter(prefix="/api/v1/scrape", tags=["scrape"])


@router.post("/annotate-now", summary="Trigger comment annotation backfill on demand")
async def annotate_now() -> dict:
    return await annotate_pending(batch_size=200)
