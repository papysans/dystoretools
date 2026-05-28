import base64
import os

import pytest

from dystore.llm.registry import service as registry_service
from dystore.llm.registry.crypto import decrypt_secret, encrypt_secret, fingerprint_secret, mask_secret
from dystore.llm.registry.schemas import ModelCreate, ModelUpdate, ProviderCreate
from dystore.llm.registry.service import (
    create_model,
    create_provider,
    list_models,
    list_providers,
    update_model,
)


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


@pytest.mark.asyncio
async def test_sync_discovered_models_upserts_live_provider_models(session, monkeypatch) -> None:
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("CHAT_MASTER_ENCRYPTION_KEY", key)
    from dystore.core.config import get_settings

    get_settings.cache_clear()
    provider = await create_provider(
        session,
        ProviderCreate(
            name="Live Provider",
            adapter_kind="openai_compat",
            base_url="https://example.com/v1",
            api_key="sk-secret-value",
        ),
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"id": "deepseek-chat"},
                    {"id": "deepseek-chat"},
                    {"id": "text-embedding-3-small"},
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict) -> FakeResponse:
            assert url == "https://example.com/v1/models"
            assert headers["Authorization"] == "Bearer sk-secret-value"
            return FakeResponse()

    monkeypatch.setattr(registry_service.httpx, "AsyncClient", FakeAsyncClient)

    first_sync = await registry_service.sync_discovered_models(session, provider.id)
    assert first_sync["ok"] is True
    assert first_sync["total"] == 2
    assert first_sync["created"] == 2

    models = await list_models(session, provider_id=provider.id)
    by_name = {model.model_name: model for model in models}
    assert by_name["deepseek-chat"].enabled
    assert by_name["deepseek-chat"].capabilities == ["chat", "streaming", "function_calling"]
    assert not by_name["text-embedding-3-small"].enabled
    assert by_name["text-embedding-3-small"].capabilities == []

    second_sync = await registry_service.sync_discovered_models(session, provider.id)
    assert second_sync["ok"] is True
    assert second_sync["created"] == 0
    assert second_sync["existing"] == 2
