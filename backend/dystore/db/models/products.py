from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, Float, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class DoudianGoods(Base, ScrapedAtMixin):
    __tablename__ = "doudian_goods"
    __table_args__ = (
        Index("ix_doudian_goods_id", "goods_id"),
        Index("ix_doudian_goods_tab", "tab"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    stock: Mapped[int | None] = mapped_column(Integer)
    click_num: Mapped[int | None] = mapped_column(Integer)
    convert_rate: Mapped[float | None] = mapped_column(Float)
    category_id: Mapped[str | None] = mapped_column(String(64))
    group_id: Mapped[str | None] = mapped_column(String(64))
    tab: Mapped[str | None] = mapped_column(String(32))
    check_status: Mapped[int | None] = mapped_column(SmallInteger)
    business_type: Mapped[int | None] = mapped_column(SmallInteger)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class DoudianStock(Base, ScrapedAtMixin):
    __tablename__ = "doudian_stock"
    __table_args__ = (Index("ix_doudian_stock_goods_sku", "goods_id", "sku_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sku_id: Mapped[str | None] = mapped_column(String(64))
    warehouse_id: Mapped[str | None] = mapped_column(String(64))
    on_hand: Mapped[int | None] = mapped_column(Integer)
    available: Mapped[int | None] = mapped_column(Integer)
    locked: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class DoudianSkuDiagnose(Base, ScrapedAtMixin):
    __tablename__ = "doudian_sku_diagnose"
    __table_args__ = (Index("ix_sku_diagnose_goods", "goods_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sku_id: Mapped[str | None] = mapped_column(String(64))
    diagnose_type: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(16))
    msg_json: Mapped[dict | None] = mapped_column(JSON)


class GoodsDiagnose(Base, ScrapedAtMixin):
    __tablename__ = "goods_diagnose"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    issues_json: Mapped[dict | None] = mapped_column(JSON)
