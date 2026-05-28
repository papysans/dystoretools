"""initial schema

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


# Tables that need monthly RANGE partitions on scraped_at.
PARTITIONED_TABLES = [
    "compass_core_data",
    "compass_core_trend",
    "member_dashboard_day",
    "member_dashboard_hist",
    "aftersale_counts",
    "comment_tag_stat",
]


def _partition_clause() -> str:
    """Build a PARTITION BY RANGE clause covering the next 13 months from 2026-01."""
    parts = []
    for year, month in _months_iter(2026, 1, 13):
        next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)
        boundary = f"{next_year:04d}-{next_month:02d}-01"
        parts.append(f"PARTITION p{year:04d}{month:02d} VALUES LESS THAN (TO_DAYS('{boundary}'))")
    parts.append("PARTITION p_future VALUES LESS THAN MAXVALUE")
    return (
        "PARTITION BY RANGE (TO_DAYS(scraped_at)) (\n  "
        + ",\n  ".join(parts)
        + "\n)"
    )


def _months_iter(start_year: int, start_month: int, count: int):
    y, m = start_year, start_month
    for _ in range(count):
        yield y, m
        m += 1
        if m > 12:
            y += 1
            m = 1


def upgrade() -> None:
    # The full schema is created from SQLAlchemy metadata via `op.create_table` calls below.
    # To keep this revision focused on infrastructure, we use `Base.metadata.create_all`
    # against the bound connection — this is acceptable for the *initial* revision only.
    from dystore.db.models import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)

    # Partitioning deferred — MySQL requires PK to include all partition-key columns.
    # V1: retention enforced via DELETE WHERE scraped_at < cutoff (see scheduler/maintenance.py).
    # V2: switch to composite PK (id, scraped_at) and re-enable PARTITION BY RANGE for O(1) drop.


def downgrade() -> None:
    from dystore.db.models import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
