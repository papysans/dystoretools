"""custom agents and schedules

Revision ID: 20260527_0003
Revises: 20260520_0002
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa

revision = "20260527_0003"
down_revision = "20260520_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("user_agent"):
        op.create_table(
            "user_agent",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("provider_id", sa.BigInteger(), nullable=True),
            sa.Column("model_name", sa.String(length=128), nullable=True),
            sa.Column("tools_json", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_agent_enabled", "user_agent", ["enabled"])
        op.create_index("ix_user_agent_updated", "user_agent", ["updated_at"])

    if not _has_table("agent_schedule"):
        op.create_table(
            "agent_schedule",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("agent_id", sa.BigInteger(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("cron", sa.String(length=64), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default="Asia/Shanghai", nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("last_run_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("next_run_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_agent_schedule_agent", "agent_schedule", ["agent_id"])
        op.create_index("ix_agent_schedule_enabled", "agent_schedule", ["enabled"])
        op.create_index("ix_agent_schedule_next_run", "agent_schedule", ["next_run_at"])

    if not _has_table("agent_run"):
        op.create_table(
            "agent_run",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("agent_id", sa.BigInteger(), nullable=False),
            sa.Column("schedule_id", sa.BigInteger(), nullable=True),
            sa.Column("conversation_id", sa.BigInteger(), nullable=True),
            sa.Column("trigger_kind", sa.String(length=32), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
            sa.Column("result_text", sa.Text(), nullable=True),
            sa.Column("error_msg", sa.String(length=2048), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_agent_run_agent_created", "agent_run", ["agent_id", "created_at"])
        op.create_index("ix_agent_run_schedule_created", "agent_run", ["schedule_id", "created_at"])
        op.create_index("ix_agent_run_status", "agent_run", ["status"])


def downgrade() -> None:
    if _has_table("agent_run"):
        op.drop_index("ix_agent_run_status", table_name="agent_run")
        op.drop_index("ix_agent_run_schedule_created", table_name="agent_run")
        op.drop_index("ix_agent_run_agent_created", table_name="agent_run")
        op.drop_table("agent_run")
    if _has_table("agent_schedule"):
        op.drop_index("ix_agent_schedule_next_run", table_name="agent_schedule")
        op.drop_index("ix_agent_schedule_enabled", table_name="agent_schedule")
        op.drop_index("ix_agent_schedule_agent", table_name="agent_schedule")
        op.drop_table("agent_schedule")
    if _has_table("user_agent"):
        op.drop_index("ix_user_agent_updated", table_name="user_agent")
        op.drop_index("ix_user_agent_enabled", table_name="user_agent")
        op.drop_table("user_agent")


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)
