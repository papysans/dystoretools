from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from dystore.core.logging import get_logger

log = get_logger(__name__)

LOCAL_AUTH_TABLES = {"local_user", "local_session"}

LOCAL_AUTH_DDL = {
    "local_user": """
    CREATE TABLE local_user (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL,
        password_hash VARCHAR(256) NOT NULL,
        display_name VARCHAR(128) NULL,
        role VARCHAR(32) NOT NULL DEFAULT 'operator',
        permissions TEXT NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        last_login_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY ix_local_user_username (username),
        KEY ix_local_user_enabled (enabled)
    )
    """,
    "local_session": """
    CREATE TABLE local_session (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        token VARCHAR(128) NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY ix_local_session_token (token),
        KEY ix_local_session_user (user_id),
        KEY ix_local_session_expires (expires_at)
    )
    """,
}


async def ensure_local_auth_tables(engine: AsyncEngine) -> None:
    try:
        async with engine.begin() as conn:
            existing = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
            missing = [name for name in ("local_user", "local_session") if name not in existing]
            if not missing:
                log.info("local_auth.tables_ready", tables=sorted(LOCAL_AUTH_TABLES))
                return

            log.info("local_auth.tables_missing", missing=missing)
            for table_name in missing:
                await conn.execute(text(LOCAL_AUTH_DDL[table_name]))
    except SQLAlchemyError:
        log.exception("local_auth.inspect_failed")
        raise

    log.info("local_auth.tables_created", created=missing)
