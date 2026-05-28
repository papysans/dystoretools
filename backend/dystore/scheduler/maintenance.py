"""Local-only maintenance tasks: archive + backup. No outbound HTTP."""
from datetime import datetime, timedelta

from sqlalchemy import text

from dystore.core.logging import get_logger
from dystore.db.session import SessionLocal

log = get_logger(__name__)

PARTITIONED_TABLES = (
    "compass_core_data",
    "compass_core_trend",
    "member_dashboard_day",
    "member_dashboard_hist",
    "aftersale_counts",
    "comment_tag_stat",
)


async def drop_old_partitions(retention_days: int = 365) -> dict[str, int]:
    """V1 retention: DELETE rows older than retention_days.

    Partitioning is deferred (see migrations/...0001_initial_schema.py). Once tables
    have composite PKs and `PARTITION BY RANGE (TO_DAYS(scraped_at))`, this can switch
    to `ALTER TABLE … DROP PARTITION` for O(1) deletion.

    Returns a {table: rows_deleted} map. Safe to re-run.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted: dict[str, int] = {}
    async with SessionLocal() as session:
        for table in PARTITIONED_TABLES:
            r = await session.execute(
                text(f"DELETE FROM {table} WHERE scraped_at < :c"),
                {"c": cutoff},
            )
            deleted[table] = r.rowcount or 0
        await session.commit()
    log.info("maintenance.retention_deleted", deleted=deleted)
    return deleted
