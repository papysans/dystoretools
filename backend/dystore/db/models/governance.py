from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class ExperienceScore(Base, ScrapedAtMixin):
    __tablename__ = "experience_score"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float | None]
    sub_scores_json: Mapped[dict | None] = mapped_column(JSON)


class ShopViolation(Base, ScrapedAtMixin):
    __tablename__ = "shop_violation"
    __table_args__ = (Index("ix_violation_status", "status"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    violation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kind: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str | None] = mapped_column(String(32))
    created_at_src: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    raw_json: Mapped[dict | None] = mapped_column(JSON)
