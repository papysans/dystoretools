"""qianchuan official API tables

Revision ID: 0005_qianchuan
Revises: 0004_local_auth

Create Date: 2026-05-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_qianchuan"
down_revision = "0004_local_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qianchuan_token",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("access_token_enc", sa.Text(), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(), nullable=True),
        sa.Column("scope_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "qianchuan_advertiser",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("advertiser_id", sa.String(length=64), nullable=False),
        sa.Column("advertiser_name", sa.String(length=255), nullable=True),
        sa.Column("token_id", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["token_id"], ["qianchuan_token.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advertiser_id"),
    )
    op.create_index("ix_qianchuan_advertiser_scraped_at", "qianchuan_advertiser", ["scraped_at"])
    op.create_table(
        "qianchuan_report",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("advertiser_id", sa.String(length=64), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("object_id", sa.String(length=64), nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("show_cnt", sa.BigInteger(), nullable=True),
        sa.Column("click_cnt", sa.BigInteger(), nullable=True),
        sa.Column("convert_cnt", sa.BigInteger(), nullable=True),
        sa.Column("convert_cost", sa.Float(), nullable=True),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("pay_order_amount", sa.Float(), nullable=True),
        sa.Column("roi", sa.Float(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advertiser_id", "stat_date", "level", "object_id", name="uq_qc_report"),
    )
    op.create_index("ix_qc_report_adv_date", "qianchuan_report", ["advertiser_id", "stat_date"])
    op.create_index("ix_qianchuan_report_scraped_at", "qianchuan_report", ["scraped_at"])


def downgrade() -> None:
    op.drop_table("qianchuan_report")
    op.drop_table("qianchuan_advertiser")
    op.drop_table("qianchuan_token")
