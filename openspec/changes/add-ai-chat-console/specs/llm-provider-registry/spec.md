## ADDED Requirements

### Requirement: Provider and model persistence
The system SHALL persist LLM providers and models in MySQL. Providers MUST include name, adapter_kind, base_url, encrypted api key, masked key fingerprint, default headers JSON, enabled flag, created_at, and updated_at. Models MUST include provider_id, model_name, display_name, context_window, capabilities JSON, enabled flag, and default-for-chat flag.

#### Scenario: Provider created
- **WHEN** the frontend posts a valid provider payload
- **THEN** the system creates a provider row with encrypted API key material and returns metadata without plaintext key

#### Scenario: Models listed
- **WHEN** the frontend requests models for a provider
- **THEN** the system returns enabled and disabled model rows with capability metadata but no provider secret

### Requirement: API key encryption
The system SHALL encrypt provider API keys at rest using AES-256-GCM with a 32-byte base64 master key from `CHAT_MASTER_ENCRYPTION_KEY`. The system MUST fail startup or provider write operations with a clear error if encryption is required but the master key is missing or invalid.

#### Scenario: Store API key
- **WHEN** a provider is created or updated with an API key
- **THEN** the plaintext key is encrypted before it is stored in MySQL

#### Scenario: Read provider
- **WHEN** the frontend fetches provider details
- **THEN** the response includes `key_set=true` and a masked fingerprint
- **AND** it does not include the plaintext or encrypted API key blob

#### Scenario: Missing master key
- **WHEN** the service attempts to encrypt or decrypt provider credentials without a valid master key
- **THEN** the operation fails with a configuration error and does not store plaintext

### Requirement: Provider CRUD API
The system SHALL expose FastAPI endpoints for provider CRUD under `/api/v1/llm/providers`. Create and update endpoints MUST accept API keys; list/detail endpoints MUST return only masked key metadata. Deleting a provider MUST be blocked while enabled models or existing chat conversations require it unless the provider is first disabled or migrated.

#### Scenario: List providers
- **WHEN** the frontend calls `GET /api/v1/llm/providers`
- **THEN** it receives provider metadata, model counts, enabled flags, and masked key status only

#### Scenario: Update provider without replacing key
- **WHEN** the frontend patches provider metadata with an empty or omitted API key field
- **THEN** the existing encrypted key remains unchanged

#### Scenario: Replace provider key
- **WHEN** the frontend patches a provider with a non-empty API key
- **THEN** the new key replaces the previous encrypted key and the masked fingerprint updates

### Requirement: Model CRUD API
The system SHALL expose FastAPI endpoints for creating, updating, enabling, disabling, and selecting LLM models. At most one enabled model MAY be marked `is_default_for_chat=true` at a time.

#### Scenario: Set chat default model
- **WHEN** the frontend marks a model as default for chat
- **THEN** the system clears `is_default_for_chat` from all other models and sets it on the selected model

#### Scenario: Disable default model
- **WHEN** the frontend disables the current default chat model
- **THEN** the system either rejects the operation or requires another enabled model to become the default in the same request

### Requirement: Built-in provider adapters
The system SHALL support `openai_compat` and `anthropic` adapter kinds in V1. The `openai_compat` adapter MUST support DeepSeek, Kimi, OpenAI, and custom OpenAI-compatible endpoints through configurable base URL, headers, and model names. The `anthropic` adapter MUST support Claude Messages API formatting.

#### Scenario: OpenAI-compatible provider call
- **WHEN** the gateway resolves an enabled model whose provider adapter is `openai_compat`
- **THEN** it sends requests using OpenAI-compatible chat-completions format

#### Scenario: Anthropic provider call
- **WHEN** the gateway resolves an enabled model whose provider adapter is `anthropic`
- **THEN** it sends requests using Anthropic Messages API format

### Requirement: Seed built-in providers
The system SHALL seed provider presets for DeepSeek, Kimi, OpenAI, and Anthropic. During migration or first startup, existing DeepSeek and Kimi API key/settings values MUST be imported into provider/model rows when present so current AI features keep working.

#### Scenario: Existing DeepSeek settings imported
- **WHEN** the migration/startup seeder finds an existing DeepSeek API key
- **THEN** it creates or updates a DeepSeek provider and default model row without requiring frontend re-entry

#### Scenario: Preset without key
- **WHEN** OpenAI or Anthropic has no configured key
- **THEN** the preset may exist disabled or keyless, and it is not selectable for chat until configured

### Requirement: Provider connection test
The system SHALL expose `POST /api/v1/llm/providers/{provider_id}/test` to validate provider credentials and model configuration by making a minimal upstream request. The response MUST include success/failure, latency, provider/model metadata, and sanitized error text.

#### Scenario: Test succeeds
- **WHEN** the provider credentials are valid
- **THEN** the endpoint returns success with latency and resolved model metadata

#### Scenario: Test fails
- **WHEN** upstream returns 401
- **THEN** the endpoint returns a sanitized failure response without logging or returning the API key

### Requirement: Upstream model discovery
The system SHALL expose `GET /api/v1/llm/providers/{provider_id}/models:discover` for adapters that can list upstream models. Discovered models MAY be imported into `llm_model` rows after user confirmation.

#### Scenario: Discover OpenAI-compatible models
- **WHEN** the provider supports `/v1/models`
- **THEN** the endpoint returns sanitized upstream model ids and metadata if available

#### Scenario: Discovery unsupported
- **WHEN** the adapter cannot list models
- **THEN** the endpoint returns an unsupported status without marking the provider unhealthy

### Requirement: Provider settings frontend
The frontend SHALL add a settings page for LLM providers and models. The page MUST allow adding, editing, enabling/disabling, testing, discovering models, and selecting the default chat model. API key fields MUST use "re-enter to update" semantics.

#### Scenario: Provider list page
- **WHEN** the user opens the provider settings page
- **THEN** the page displays each provider's name, adapter kind, base URL, enabled state, masked key status, and model list summary

#### Scenario: Edit provider key
- **WHEN** the user edits a provider without typing a new API key
- **THEN** the frontend sends no replacement key and the backend preserves the existing key
