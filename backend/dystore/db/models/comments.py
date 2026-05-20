from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class DoudianComment(Base, ScrapedAtMixin):
    __tablename__ = "doudian_comment"
    __table_args__ = (
        Index("ix_comment_goods", "goods_id"),
        Index("ix_comment_rating", "rating"),
        Index("ix_comment_sentiment", "sentiment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str | None] = mapped_column(String(64))
    comment_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    user_nick: Mapped[str | None] = mapped_column(String(128))
    created_at_src: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    reply_status: Mapped[str | None] = mapped_column(String(32))
    has_appeal: Mapped[bool | None] = mapped_column(Boolean)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
    # AI-annotated columns
    sentiment: Mapped[str | None] = mapped_column(String(16))
    pain_points_json: Mapped[dict | None] = mapped_column(JSON)


class CommentTagStat(Base, ScrapedAtMixin):
    """Time-series; partition by month on scraped_at."""

    __tablename__ = "comment_tag_stat"
    __table_args__ = (
        Index("ix_tag_stat_scope_tag", "scope", "tag"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)   # shop | goods
    scope_id: Mapped[str | None] = mapped_column(String(64))
    tag: Mapped[str] = mapped_column(String(128), nullable=False)
    neg_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)


class CommentIndexWarn(Base, ScrapedAtMixin):
    __tablename__ = "comment_index_warn"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)


class NegCommentProduct(Base, ScrapedAtMixin):
    __tablename__ = "neg_comment_product"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[str] = mapped_column(String(64), nullable=False)
    neg_count: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float | None]
