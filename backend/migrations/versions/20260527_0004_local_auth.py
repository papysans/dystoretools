"""local users and permissions

Revision ID: 20260527_0004
Revises: 20260527_0003
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa

revision = "20260527_0004"
down_revision = "20260527_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("local_user"):
        op.create_table(
            "local_user",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("password_hash", sa.String(length=256), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=True),
            sa.Column("role", sa.String(length=32), server_default="operator", nullable=False),
            sa.Column("permissions", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_local_user_username", "local_user", ["username"], unique=True)
        op.create_index("ix_local_user_enabled", "local_user", ["enabled"])

    if not _has_table("local_session"):
        op.create_table(
            "local_session",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("token", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_local_session_token", "local_session", ["token"], unique=True)
        op.create_index("ix_local_session_user", "local_session", ["user_id"])
        op.create_index("ix_local_session_expires", "local_session", ["expires_at"])


def downgrade() -> None:
    if _has_table("local_session"):
        op.drop_index("ix_local_session_expires", table_name="local_session")
        op.drop_index("ix_local_session_user", table_name="local_session")
        op.drop_index("ix_local_session_token", table_name="local_session")
        op.drop_table("local_session")
    if _has_table("local_user"):
        op.drop_index("ix_local_user_enabled", table_name="local_user")
        op.drop_index("ix_local_user_username", table_name="local_user")
        op.drop_table("local_user")


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)
