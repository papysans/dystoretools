"""巨量千川官方 API 数据模型.

- QianchuanToken: 单次 OAuth 授权产出的 access/refresh token（AES-GCM 加密存储）。
- QianchuanAdvertiser: 该授权下可访问的千川广告账户清单。
- QianchuanReport: 按天的投放报表（消耗/转化/ROI），时序表，按月分区 on scraped_at。
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base, CreatedAtMixin, ScrapedAtMixin


class QianchuanToken(Base, CreatedAtMixin):
    __tablename__ = "qianchuan_token"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 授权用户 uid（回调返回，标识一次授权主体）
    uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    scope_json: Mapped[list | None] = mapped_column(JSON)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class QianchuanAdvertiser(Base, ScrapedAtMixin):
    __tablename__ = "qianchuan_advertiser"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    advertiser_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    advertiser_name: Mapped[str | None] = mapped_column(String(255))
    token_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("qianchuan_token.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON)


class QianchuanReport(Base, ScrapedAtMixin):
    """时序；partition by month on scraped_at。唯一键防重复入库。"""

    __tablename__ = "qianchuan_report"
    __table_args__ = (
        UniqueConstraint("advertiser_id", "stat_date", "level", "object_id", name="uq_qc_report"),
        Index("ix_qc_report_adv_date", "advertiser_id", "stat_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    advertiser_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    # advertiser | campaign | ad
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="advertiser")
    # campaign_id / ad_id；账户级为空串
    object_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    cost: Mapped[float | None] = mapped_column(Float)
    show_cnt: Mapped[int | None] = mapped_column(BigInteger)
    click_cnt: Mapped[int | None] = mapped_column(BigInteger)
    convert_cnt: Mapped[int | None] = mapped_column(BigInteger)
    convert_cost: Mapped[float | None] = mapped_column(Float)
    ctr: Mapped[float | None] = mapped_column(Float)
    pay_order_amount: Mapped[float | None] = mapped_column(Float)
    roi: Mapped[float | None] = mapped_column(Float)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
