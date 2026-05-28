import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.chat.agent import run_agent_turn
from dystore.chat.service import (
    conversation_to_dict,
    create_conversation,
    list_conversations,
    list_messages,
    message_to_dict,
)
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class CreateConversationRequest(BaseModel):
    title: str | None = None
    provider_id: int | None = None
    model_name: str | None = None


class SendMessageRequest(BaseModel):
    content: str
    provider_id: int | None = None
    model_name: str | None = None


@router.post("/conversations")
async def create(req: CreateConversationRequest, session: AsyncSession = Depends(get_session)) -> dict:
    row = await create_conversation(session, title=req.title, provider_id=req.provider_id, model_name=req.model_name)
    return conversation_to_dict(row)


@router.get("/conversations")
async def conversations(limit: int = Query(100, le=500), session: AsyncSession = Depends(get_session)) -> dict:
    rows = await list_conversations(session, limit=limit)
    return {"items": [conversation_to_dict(row) for row in rows]}


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    rows = await list_messages(session, conversation_id)
    return {"items": [message_to_dict(row) for row in rows]}


@router.post("/conversations/{conversation_id}/messages:stream")
async def stream_message(
    conversation_id: int,
    req: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    async def events():
        try:
            async for item in run_agent_turn(
                session,
                conversation_id=conversation_id,
                user_content=req.content,
                provider_id=req.provider_id,
                model_name=req.model_name,
            ):
                yield {"event": item["event"], "data": json.dumps(item["data"], ensure_ascii=False)}
        except Exception as exc:
            yield {
                "event": "error",
                "data": json.dumps({"error": type(exc).__name__, "message": str(exc)[:500]}, ensure_ascii=False),
            }

    return EventSourceResponse(events())
