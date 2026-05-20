from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class MarketingCoupon(Base, ScrapedAtMixin):
    __tablename__ = "marketing_coupon"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    coupon_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    used: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class MarketingActivity(Base, ScrapedAtMixin):
    __tablename__ = "marketing_activity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class LogisticsEvent(Base, ScrapedAtMixin):
    __tablename__ = "logistics_event"
    __table_args__ = (Index("ix_logistics_order_sn", "order_sn"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_sn: Mapped[str | None] = mapped_column(String(64))
    waybill_no: Mapped[str | None] = mapped_column(String(64))
    event: Mapped[str | None] = mapped_column(String(64))
    location: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
