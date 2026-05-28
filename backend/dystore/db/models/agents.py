from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base


class UserAgent(Base):
    __tablename__ = "user_agent"
    __table_args__ = (
        Index("ix_user_agent_enabled", "enabled"),
        Index("ix_user_agent_updated", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger)
    model_name: Mapped[str | None] = mapped_column(String(128))
    tools_json: Mapped[list | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentSchedule(Base):
    __tablename__ = "agent_schedule"
    __table_args__ = (
        Index("ix_agent_schedule_agent", "agent_id"),
        Index("ix_agent_schedule_enabled", "enabled"),
        Index("ix_agent_schedule_next_run", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    cron: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai", server_default="Asia/Shanghai")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentRun(Base):
    __tablename__ = "agent_run"
    __table_args__ = (
        Index("ix_agent_run_agent_created", "agent_id", "created_at"),
        Index("ix_agent_run_schedule_created", "schedule_id", "created_at"),
        Index("ix_agent_run_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schedule_id: Mapped[int | None] = mapped_column(BigInteger)
    conversation_id: Mapped[int | None] = mapped_column(BigInteger)
    trigger_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", server_default="queued")
    result_text: Mapped[str | None] = mapped_column(Text)
    error_msg: Mapped[str | None] = mapped_column(String(2048))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
