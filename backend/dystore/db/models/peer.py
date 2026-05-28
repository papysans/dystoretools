from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, Float, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class PeerShop(Base, ScrapedAtMixin):
    __tablename__ = "peer_shop"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    shop_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    shop_name: Mapped[str | None] = mapped_column(String(255))
    follower_count: Mapped[int | None] = mapped_column(Integer)


class PeerGoods(Base, ScrapedAtMixin):
    __tablename__ = "peer_goods"
    __table_args__ = (Index("ix_peer_goods_shop", "peer_shop_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    peer_shop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    peer_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    hot_sale: Mapped[int | None] = mapped_column(Integer)


class PeerLivestream(Base, ScrapedAtMixin):
    __tablename__ = "peer_livestream"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    peer_shop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    room_id: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    gmv: Mapped[float | None] = mapped_column(Float)
