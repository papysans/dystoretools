from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class DoudianOrder(Base, ScrapedAtMixin):
    __tablename__ = "doudian_order"
    __table_args__ = (
        Index("ix_doudian_order_pay_time", "pay_time"),
        Index("ix_doudian_order_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_sn: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    goods_name: Mapped[str | None] = mapped_column(String(255))
    sale_num: Mapped[int | None] = mapped_column()
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pay_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    status: Mapped[int | None] = mapped_column(SmallInteger)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
