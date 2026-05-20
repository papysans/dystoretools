from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base


class ScrapeTaskRun(Base):
    __tablename__ = "scrape_task_run"
    __table_args__ = (
        Index("ix_scrape_task_target", "target"),
        Index("ix_scrape_task_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    subsystem: Mapped[str] = mapped_column(String(16), nullable=False)  # merchant | public | maintenance
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str | None] = mapped_column(String(2048))


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        Index("ix_alert_kind", "kind"),
        Index("ix_alert_severity", "severity"),
        Index("ix_alert_acked", "acked_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class SessionEvent(Base):
    __tablename__ = "session_event"
    __table_args__ = (Index("ix_session_event_kind", "kind"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
