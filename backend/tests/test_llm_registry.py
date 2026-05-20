import base64
import os

import pytest

from dystore.llm.registry.crypto import decrypt_secret, encrypt_secret, fingerprint_secret, mask_secret
from dystore.llm.registry.schemas import ModelCreate, ModelUpdate, ProviderCreate
from dystore.llm.registry.service import create_model, create_provider, list_providers, update_model


def test_encrypt_decrypt_secret(monkeypatch) -> None:
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("CHAT_MASTER_ENCRYPTION_KEY", key)
    from dystore.core.config import get_settings

    get_settings.cache_clear()
    encrypted = encrypt_secret("sk-test-secret")
    assert "sk-test-secret" not in encrypted
    assert decrypt_secret(encrypted) == "sk-test-secret"


def test_mask_and_fingerprint() -> None:
    assert mask_secret("sk-abcdef123456") == "sk-a***3456"
    assert fingerprint_secret("sk-abcdef123456") == fingerprint_secret("sk-abcdef123456")


@pytest.mark.asyncio
async def test_provider_read_never_returns_plaintext(session, monkeypatch) -> None:
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("CHAT_MASTER_ENCRYPTION_KEY", key)
    from dystore.core.config import get_settings

    get_settings.cache_clear()
    created = await create_provider(
        session,
        ProviderCreate(
            name="Test Provider",
            adapter_kind="openai_compat",
            base_url="https://example.com/v1",
            api_key="sk-secret-value",
        ),
    )
    assert created.key_set
    assert created.key_fingerprint
    assert "secret" not in created.model_dump_json()
    providers = await list_providers(session)
    assert providers[0].key_set
    assert "secret" not in providers[0].model_dump_json()


@pytest.mark.asyncio
async def test_only_one_default_chat_model(session, monkeypatch) -> None:
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("CHAT_MASTER_ENCRYPTION_KEY", key)
    from dystore.core.config import get_settings

    get_settings.cache_clear()
    provider = await create_provider(
        session,
        ProviderCreate(name="Default Test", adapter_kind="openai_compat", base_url="https://example.com/v1"),
    )
    first = await create_model(
        session,
        ModelCreate(provider_id=provider.id, model_name="first", is_default_for_chat=True),
    )
    second = await create_model(
        session,
        ModelCreate(provider_id=provider.id, model_name="second", is_default_for_chat=True),
    )
    first = await update_model(session, first.id, ModelUpdate())
    assert first is not None
    assert not first.is_default_for_chat
    assert second.is_default_for_chat
