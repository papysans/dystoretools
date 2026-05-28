from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str
    adapter_kind: str = Field(pattern="^(openai_compat|anthropic)$")
    base_url: str
    api_key: str | None = None
    default_headers: dict[str, str] | None = None
    enabled: bool = True


class ProviderUpdate(BaseModel):
    name: str | None = None
    adapter_kind: str | None = Field(default=None, pattern="^(openai_compat|anthropic)$")
    base_url: str | None = None
    api_key: str | None = None
    default_headers: dict[str, str] | None = None
    enabled: bool | None = None


class ModelCreate(BaseModel):
    provider_id: int
    model_name: str
    display_name: str | None = None
    context_window: int | None = None
    capabilities: list[str] = Field(default_factory=lambda: ["chat", "streaming"])
    enabled: bool = True
    is_default_for_chat: bool = False


class ModelUpdate(BaseModel):
    model_name: str | None = None
    display_name: str | None = None
    context_window: int | None = None
    capabilities: list[str] | None = None
    enabled: bool | None = None
    is_default_for_chat: bool | None = None


class ProviderRead(BaseModel):
    id: int
    name: str
    adapter_kind: str
    base_url: str
    enabled: bool
    key_set: bool
    key_fingerprint: str | None
    default_headers: dict | None
    model_count: int = 0


class ModelRead(BaseModel):
    id: int
    provider_id: int
    model_name: str
    display_name: str | None
    context_window: int | None
    capabilities: list[str]
    enabled: bool
    is_default_for_chat: bool
