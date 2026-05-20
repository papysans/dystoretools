from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, ScrapedAtMixin


class MemberDashboardAgg(Base, ScrapedAtMixin):
    __tablename__ = "member_dashboard_agg"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    indices_json: Mapped[dict | None] = mapped_column(JSON)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class MemberDashboardDay(Base, ScrapedAtMixin):
    """Time-series; partition by month on scraped_at."""

    __tablename__ = "member_dashboard_day"
    __table_args__ = (Index("ix_member_day_date_metric", "date", "metric"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)


class MemberDashboardHist(Base, ScrapedAtMixin):
    """Time-series; partition by month on scraped_at."""

    __tablename__ = "member_dashboard_hist"
    __table_args__ = (Index("ix_member_hist_date_dim", "date", "dim"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    dim: Mapped[str | None] = mapped_column(String(64))


class AudienceFeature(Base, ScrapedAtMixin):
    __tablename__ = "audience_feature"
    __table_args__ = (Index("ix_audience_user_type", "user_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_type: Mapped[int] = mapped_column(nullable=False)
    ref_user_type: Mapped[int | None]
    feature_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(String(255))
    weight: Mapped[float | None] = mapped_column(Float)


class MemberSalesActivity(Base, ScrapedAtMixin):
    __tablename__ = "member_sales_activity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    status: Mapped[str | None] = mapped_column(String(32))
    raw_json: Mapped[dict | None] = mapped_column(JSON)
