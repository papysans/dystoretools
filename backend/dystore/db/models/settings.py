from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from dystore.db.base import Base


class AppSetting(Base):
    """Single-table KV store for user-editable runtime settings.

    Used to override .env values without restarting the container.
    Secrets are stored verbatim; the REST layer masks them on read.
    """

    __tablename__ = "app_setting"
    __table_args__ = (Index("ix_app_setting_kind", "kind"),)

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="string")  # string | secret | url | int | bool
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )
