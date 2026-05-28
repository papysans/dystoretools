from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversation"
    __table_args__ = (
        Index("ix_chat_conversation_updated", "updated_at"),
        Index("ix_chat_conversation_archived", "archived_at"),
        Index("ix_chat_conversation_model", "provider_id", "model_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="新对话")
    provider_id: Mapped[int | None] = mapped_column(BigInteger)
    model_name: Mapped[str | None] = mapped_column(String(128))
    last_message_preview: Mapped[str | None] = mapped_column(String(255))
    total_tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_cost_cny: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = (
        Index("ix_chat_message_conversation_created", "conversation_id", "created_at"),
        Index("ix_chat_message_kind", "kind"),
        Index("ix_chat_message_role", "role"),
        Index("ix_chat_message_source_tool", "source_tool_call_id"),
        Index("ix_chat_message_ai_generation", "ai_generation_id"),
        Index("ix_chat_message_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[int | None] = mapped_column(BigInteger)
    model_name: Mapped[str | None] = mapped_column(String(128))
    ai_generation_id: Mapped[int | None] = mapped_column(BigInteger)
    tool_call_id: Mapped[str | None] = mapped_column(String(128))
    source_tool_call_id: Mapped[str | None] = mapped_column(String(128))
    tool_name: Mapped[str | None] = mapped_column(String(128))
    tool_calls_json: Mapped[dict | list | None] = mapped_column(JSON)
    tool_results_json: Mapped[dict | list | None] = mapped_column(JSON)
    render_spec_json: Mapped[dict | None] = mapped_column(JSON)
    source_sql: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok", server_default="ok")
    error_msg: Mapped[str | None] = mapped_column(String(2048))
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost_cny: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
