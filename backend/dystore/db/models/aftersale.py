from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class DoudianAftersale(Base, ScrapedAtMixin):
    __tablename__ = "doudian_aftersale"
    __table_args__ = (
        Index("ix_aftersale_order_sn", "order_sn"),
        Index("ix_aftersale_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aftersale_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    order_sn: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(String(512))
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[int | None] = mapped_column(SmallInteger)
    sub_status: Mapped[int | None] = mapped_column(SmallInteger)
    created_at_src: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class AftersaleCounts(Base, ScrapedAtMixin):
    """Time-series table — one row per (dim, scraped_at). Partition by month on scraped_at."""

    __tablename__ = "aftersale_counts"
    __table_args__ = (Index("ix_aftersale_counts_dim", "dim"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dim: Mapped[str] = mapped_column(String(64), nullable=False)
    count: Mapped[int] = mapped_column(default=0)
