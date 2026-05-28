"""ai chat console

Revision ID: 20260520_0002
Revises: 20260518_0001
Create Date: 2026-05-20

"""
import base64
import hashlib
import os

from alembic import op
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import sqlalchemy as sa

revision = "20260520_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("llm_provider"):
        op.create_table(
            "llm_provider",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("adapter_kind", sa.String(length=32), nullable=False),
            sa.Column("base_url", sa.String(length=512), nullable=False),
            sa.Column("api_key_encrypted", sa.Text(), nullable=True),
            sa.Column("api_key_fingerprint", sa.String(length=32), nullable=True),
            sa.Column("default_headers_json", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", name="uq_llm_provider_name"),
        )
        op.create_index("ix_llm_provider_adapter", "llm_provider", ["adapter_kind"])
        op.create_index("ix_llm_provider_enabled", "llm_provider", ["enabled"])

    if not _has_table("llm_model"):
        op.create_table(
            "llm_model",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("provider_id", sa.BigInteger(), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=True),
            sa.Column("context_window", sa.BigInteger(), nullable=True),
            sa.Column("capabilities_json", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("is_default_for_chat", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider_id", "model_name", name="uq_llm_model_provider_name"),
        )
        op.create_index("ix_llm_model_default_chat", "llm_model", ["is_default_for_chat"])
        op.create_index("ix_llm_model_enabled", "llm_model", ["enabled"])
        op.create_index("ix_llm_model_provider", "llm_model", ["provider_id"])

    if not _has_table("chat_conversation"):
        op.create_table(
            "chat_conversation",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("provider_id", sa.BigInteger(), nullable=True),
            sa.Column("model_name", sa.String(length=128), nullable=True),
            sa.Column("last_message_preview", sa.String(length=255), nullable=True),
            sa.Column("total_tokens_in", sa.Integer(), server_default="0", nullable=False),
            sa.Column("total_tokens_out", sa.Integer(), server_default="0", nullable=False),
            sa.Column("total_cost_cny", sa.Float(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.Column("archived_at", sa.DateTime(timezone=False), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_chat_conversation_archived", "chat_conversation", ["archived_at"])
        op.create_index("ix_chat_conversation_model", "chat_conversation", ["provider_id", "model_name"])
        op.create_index("ix_chat_conversation_updated", "chat_conversation", ["updated_at"])

    if not _has_table("chat_message"):
        op.create_table(
            "chat_message",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("conversation_id", sa.BigInteger(), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("provider_id", sa.BigInteger(), nullable=True),
            sa.Column("model_name", sa.String(length=128), nullable=True),
            sa.Column("ai_generation_id", sa.BigInteger(), nullable=True),
            sa.Column("tool_call_id", sa.String(length=128), nullable=True),
            sa.Column("source_tool_call_id", sa.String(length=128), nullable=True),
            sa.Column("tool_name", sa.String(length=128), nullable=True),
            sa.Column("tool_calls_json", sa.JSON(), nullable=True),
            sa.Column("tool_results_json", sa.JSON(), nullable=True),
            sa.Column("render_spec_json", sa.JSON(), nullable=True),
            sa.Column("source_sql", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="ok", nullable=False),
            sa.Column("error_msg", sa.String(length=2048), nullable=True),
            sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
            sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
            sa.Column("cost_cny", sa.Float(), server_default="0", nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_chat_message_ai_generation", "chat_message", ["ai_generation_id"])
        op.create_index("ix_chat_message_conversation_created", "chat_message", ["conversation_id", "created_at"])
        op.create_index("ix_chat_message_created", "chat_message", ["created_at"])
        op.create_index("ix_chat_message_kind", "chat_message", ["kind"])
        op.create_index("ix_chat_message_role", "chat_message", ["role"])
        op.create_index("ix_chat_message_source_tool", "chat_message", ["source_tool_call_id"])

    if not _has_column("ai_generation", "provider_id"):
        op.add_column("ai_generation", sa.Column("provider_id", sa.BigInteger(), nullable=True))
    if not _has_column("ai_generation", "tool_calls_json"):
        op.add_column("ai_generation", sa.Column("tool_calls_json", sa.JSON(), nullable=True))

    _seed_provider_presets()


def downgrade() -> None:
    op.drop_column("ai_generation", "tool_calls_json")
    op.drop_column("ai_generation", "provider_id")

    op.drop_index("ix_chat_message_source_tool", table_name="chat_message")
    op.drop_index("ix_chat_message_role", table_name="chat_message")
    op.drop_index("ix_chat_message_kind", table_name="chat_message")
    op.drop_index("ix_chat_message_created", table_name="chat_message")
    op.drop_index("ix_chat_message_conversation_created", table_name="chat_message")
    op.drop_index("ix_chat_message_ai_generation", table_name="chat_message")
    op.drop_table("chat_message")

    op.drop_index("ix_chat_conversation_updated", table_name="chat_conversation")
    op.drop_index("ix_chat_conversation_model", table_name="chat_conversation")
    op.drop_index("ix_chat_conversation_archived", table_name="chat_conversation")
    op.drop_table("chat_conversation")

    op.drop_index("ix_llm_model_provider", table_name="llm_model")
    op.drop_index("ix_llm_model_enabled", table_name="llm_model")
    op.drop_index("ix_llm_model_default_chat", table_name="llm_model")
    op.drop_table("llm_model")

    op.drop_index("ix_llm_provider_enabled", table_name="llm_provider")
    op.drop_index("ix_llm_provider_adapter", table_name="llm_provider")
    op.drop_table("llm_provider")


def _seed_provider_presets() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM llm_provider")).scalar_one() > 0:
        return

    provider = sa.table(
        "llm_provider",
        sa.column("id", sa.BigInteger),
        sa.column("name", sa.String),
        sa.column("adapter_kind", sa.String),
        sa.column("base_url", sa.String),
        sa.column("api_key_encrypted", sa.Text),
        sa.column("api_key_fingerprint", sa.String),
        sa.column("enabled", sa.Boolean),
    )
    model = sa.table(
        "llm_model",
        sa.column("provider_id", sa.BigInteger),
        sa.column("model_name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("context_window", sa.BigInteger),
        sa.column("capabilities_json", sa.JSON),
        sa.column("enabled", sa.Boolean),
        sa.column("is_default_for_chat", sa.Boolean),
    )

    op.bulk_insert(
        provider,
        [
            {
                "id": 1,
                "name": "DeepSeek",
                "adapter_kind": "openai_compat",
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
                "api_key_encrypted": _encrypt_env_secret("DEEPSEEK_API_KEY"),
                "api_key_fingerprint": _fingerprint_env_secret("DEEPSEEK_API_KEY"),
                "enabled": True,
            },
            {
                "id": 2,
                "name": "Kimi",
                "adapter_kind": "openai_compat",
                "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1").rstrip("/"),
                "api_key_encrypted": _encrypt_env_secret("KIMI_API_KEY"),
                "api_key_fingerprint": _fingerprint_env_secret("KIMI_API_KEY"),
                "enabled": True,
            },
            {
                "id": 3,
                "name": "OpenAI",
                "adapter_kind": "openai_compat",
                "base_url": "https://api.openai.com/v1",
                "api_key_encrypted": None,
                "api_key_fingerprint": None,
                "enabled": False,
            },
            {
                "id": 4,
                "name": "Anthropic",
                "adapter_kind": "anthropic",
                "base_url": "https://api.anthropic.com",
                "api_key_encrypted": None,
                "api_key_fingerprint": None,
                "enabled": False,
            },
        ],
    )
    capabilities = ["chat", "streaming", "function_calling"]
    op.bulk_insert(
        model,
        [
            {
                "provider_id": 1,
                "model_name": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
                "display_name": "DeepSeek V4 Pro",
                "context_window": 1_000_000,
                "capabilities_json": capabilities,
                "enabled": True,
                "is_default_for_chat": True,
            },
            {
                "provider_id": 1,
                "model_name": "deepseek-chat",
                "display_name": "DeepSeek Chat",
                "context_window": 128_000,
                "capabilities_json": capabilities,
                "enabled": True,
                "is_default_for_chat": False,
            },
            {
                "provider_id": 2,
                "model_name": os.getenv("KIMI_MODEL", "moonshot-v1-128k"),
                "display_name": "Kimi 128K",
                "context_window": 128_000,
                "capabilities_json": capabilities,
                "enabled": True,
                "is_default_for_chat": False,
            },
            {
                "provider_id": 3,
                "model_name": "gpt-4.1",
                "display_name": "GPT-4.1",
                "context_window": 1_000_000,
                "capabilities_json": capabilities,
                "enabled": False,
                "is_default_for_chat": False,
            },
            {
                "provider_id": 4,
                "model_name": "claude-sonnet-4-5",
                "display_name": "Claude Sonnet 4.5",
                "context_window": 200_000,
                "capabilities_json": capabilities,
                "enabled": False,
                "is_default_for_chat": False,
            },
        ],
    )


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col["name"] == column for col in sa.inspect(op.get_bind()).get_columns(table))


def _encrypt_env_secret(name: str) -> str | None:
    secret = os.getenv(name)
    master_key = os.getenv("CHAT_MASTER_ENCRYPTION_KEY")
    if not secret or not master_key:
        return None
    raw_key = base64.b64decode(master_key, validate=True)
    nonce = os.urandom(12)
    ciphertext = AESGCM(raw_key).encrypt(nonce, secret.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _fingerprint_env_secret(name: str) -> str | None:
    secret = os.getenv(name)
    if not secret or not os.getenv("CHAT_MASTER_ENCRYPTION_KEY"):
        return None
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]
