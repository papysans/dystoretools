from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base


class LlmProvider(Base):
    __tablename__ = "llm_provider"
    __table_args__ = (
        UniqueConstraint("name", name="uq_llm_provider_name"),
        Index("ix_llm_provider_enabled", "enabled"),
        Index("ix_llm_provider_adapter", "adapter_kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    adapter_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    api_key_fingerprint: Mapped[str | None] = mapped_column(String(32))
    default_headers_json: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class LlmModel(Base):
    __tablename__ = "llm_model"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_name", name="uq_llm_model_provider_name"),
        Index("ix_llm_model_provider", "provider_id"),
        Index("ix_llm_model_enabled", "enabled"),
        Index("ix_llm_model_default_chat", "is_default_for_chat"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    context_window: Mapped[int | None] = mapped_column(BigInteger)
    capabilities_json: Mapped[list | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_default_for_chat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )
