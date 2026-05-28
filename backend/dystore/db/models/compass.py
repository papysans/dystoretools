from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class CompassCoreData(Base, ScrapedAtMixin):
    """Time-series; partition by month on scraped_at."""

    __tablename__ = "compass_core_data"
    __table_args__ = (Index("ix_compass_core_scope", "scope"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    date_type: Mapped[str | None] = mapped_column(String(16))
    begin_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class CompassCoreTrend(Base, ScrapedAtMixin):
    """Time-series; partition by month on scraped_at."""

    __tablename__ = "compass_core_trend"
    __table_args__ = (Index("ix_compass_trend_index_date", "index_name", "date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    index_name: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)


class CompassDiagnose(Base, ScrapedAtMixin):
    __tablename__ = "compass_diagnose"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)


class CompassIndustryWord(Base, ScrapedAtMixin):
    __tablename__ = "compass_industry_word"
    __table_args__ = (
        Index("ix_industry_word_industry", "industry_id"),
        Index("ix_industry_word_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    industry_id: Mapped[str | None] = mapped_column(String(32))
    category_id: Mapped[str | None] = mapped_column(String(32))
    rank_type: Mapped[int | None] = mapped_column(Integer)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    value: Mapped[float | None] = mapped_column(Float)


class CompassShopRank(Base, ScrapedAtMixin):
    __tablename__ = "compass_shop_rank"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sort_field: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    value: Mapped[float | None] = mapped_column(Float)


class ShopVideo(Base, ScrapedAtMixin):
    __tablename__ = "shop_video"
    __table_args__ = (Index("ix_shop_video_publish", "publish_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    author_id: Mapped[str | None] = mapped_column(String(64))
    content_type: Mapped[int | None] = mapped_column(Integer)
    audit_status: Mapped[int | None] = mapped_column(Integer)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    duration: Mapped[int | None] = mapped_column(Integer)
    play_count: Mapped[int | None] = mapped_column(BigInteger)
    gmv: Mapped[float | None] = mapped_column(Float)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
