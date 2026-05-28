## MODIFIED Requirements

### Requirement: Provider Routing Between DeepSeek and Kimi
The system SHALL expose a single async LLM gateway interface that supports both legacy non-tool completions and chat-agent tool completions without LangChain, LlamaIndex, RAG, or heavyweight orchestration frameworks. The gateway SHALL resolve provider/model configuration from `llm-provider-registry` instead of hardcoded DeepSeek/Kimi routing. Callers MAY pass `provider_id` and `model_name`; otherwise the gateway MUST use the enabled model marked `is_default_for_chat`. Legacy `prefer="long_context"` calls MUST route to the best enabled long-context model by context_window/capability, falling back to the default chat model when no better model is configured.

#### Scenario: Default model routes through registry
- **WHEN** a caller invokes the gateway without provider/model overrides
- **THEN** the system SHALL load the provider/model marked `is_default_for_chat` from `llm_model`
- **AND** it SHALL send the request through that provider's adapter

#### Scenario: Explicit model selected
- **WHEN** the chat frontend sends a message with an enabled provider_id and model_name
- **THEN** the gateway SHALL use that exact provider/model pair if the model is chat-capable

#### Scenario: Legacy long-context preference
- **WHEN** an existing caller invokes `LLM.complete` with `prefer="long_context"`
- **THEN** the gateway SHALL choose the enabled chat-capable model with the largest context_window that satisfies the request, or the default chat model if none is larger

#### Scenario: Framework prohibition retained
- **WHEN** provider routing or tool calling is implemented
- **THEN** the system SHALL NOT introduce LangChain, LlamaIndex, vector stores, embeddings, or RAG dependencies

### Requirement: Per-Call Accounting to ai_generation
Every LLM call SHALL produce one row in `ai_generation` with `kind`, `input_hash` (SHA-256 of the assembled and scrubbed prompt/messages), `output_text` when text is returned, `model`, `provider_id`, `tokens_in`, `tokens_out`, `cost`, `created_at`, and `error_msg` when applicable. The system SHALL NOT skip accounting under any code path, including tool-call responses.

#### Scenario: Successful text generation
- **WHEN** an LLM call returns a non-empty text completion
- **THEN** the system SHALL persist the accounting row before returning the text to the caller

#### Scenario: Successful tool-call generation
- **WHEN** an LLM call returns one or more tool calls and no terminal text
- **THEN** the system SHALL persist an `ai_generation` row with provider/model usage and serialized tool-call metadata

#### Scenario: Provider returns an error
- **WHEN** the LLM API call fails after retries
- **THEN** the system SHALL still write an `ai_generation` row with `output_text=NULL`, `tokens_out=0`, `cost=0`, provider/model metadata where known, and an `error_msg` field

### Requirement: Configurable PII Scrubbing Before Prompt Assembly
Before sending legacy/batch prompts to an external LLM provider, the system SHALL replace customer-identifying values with stable placeholders or masked values by default. Chat-agent calls MAY opt out of this scrubber under the merchant-authorized raw analysis mode so the selected LLM can inspect exact SQL `ui_rows` returned by approved tools.

#### Scenario: Comment contains a phone number
- **WHEN** a comment body `"我手机13900000001收不到验证码"` is sent to the LLM
- **THEN** a default legacy/batch prompt actually sent SHALL contain a placeholder or masked value instead of the raw phone number

#### Scenario: SQL result contains PII column
- **WHEN** a tool result contains `receiver_phone` or `receiver_address`
- **THEN** the chat-agent request may include raw `ui_rows` because the local merchant operator authorized raw analysis

#### Scenario: Comment lacks PII
- **WHEN** a comment body contains no detectable PII
- **THEN** the prompt sent SHALL be identical to the input except for normal message formatting

### Requirement: Bounded Retry with Exponential Backoff
The system SHALL retry transient LLM provider errors (HTTP 429, 5xx, network timeouts) up to 3 times with exponential backoff starting at 2 seconds. Non-transient errors (HTTP 400, 401, 403) SHALL NOT be retried. Retry behavior MUST apply to all adapter kinds.

#### Scenario: Provider returns 429 then succeeds
- **WHEN** the first call returns HTTP 429 and the second call succeeds
- **THEN** the caller SHALL receive the successful completion and accounting SHALL reflect only the final successful billable response plus retry metadata in logs

#### Scenario: Provider returns 401
- **WHEN** the provider returns HTTP 401
- **THEN** the gateway SHALL NOT retry and SHALL return a sanitized authentication error

## ADDED Requirements

### Requirement: Function calling support
The gateway SHALL accept a provider-neutral list of tool schemas and return a structured result that distinguishes terminal assistant text from requested tool calls. Tool schema conversion MUST be adapter-specific while the chat agent consumes one neutral response shape.

#### Scenario: OpenAI-compatible tool call
- **WHEN** an OpenAI-compatible model returns a `tool_calls` response
- **THEN** the gateway returns a structured result containing tool call id, name, and parsed JSON arguments

#### Scenario: Anthropic tool call
- **WHEN** an Anthropic model returns a tool-use block
- **THEN** the gateway converts it to the same neutral tool-call result shape

#### Scenario: Terminal text response
- **WHEN** a provider returns assistant text with no tool calls
- **THEN** the gateway returns a structured result marked as terminal text

### Requirement: Streaming gateway support for chat
The gateway SHALL support streaming assistant text deltas for providers/adapters that expose streaming. For adapters or models that do not support streaming, the gateway MUST emulate a stream by returning the final text as a single delta event.

#### Scenario: Provider supports streaming
- **WHEN** the selected model supports streaming text
- **THEN** the chat service receives incremental text deltas suitable for SSE forwarding

#### Scenario: Provider lacks streaming
- **WHEN** the selected model does not support streaming
- **THEN** the chat service still completes the turn by emitting one final text delta followed by done

### Requirement: Capability-aware model selection
The gateway SHALL only use a model for chat-agent turns when its capabilities include required features such as `chat`, `streaming` when requested, and `function_calling` when tools are registered. Unsupported models MUST be hidden or rejected for chat use.

#### Scenario: Model lacks function calling
- **WHEN** the chat agent needs to advertise tools and the selected model lacks `function_calling`
- **THEN** the system rejects the selection with a clear error before sending the LLM request

#### Scenario: Non-chat model hidden
- **WHEN** the frontend requests chat-capable models
- **THEN** models without the `chat` capability are not included

### Requirement: Dynamic adapter resolution
The gateway SHALL resolve the correct adapter implementation from the selected provider's `adapter_kind`. Adapter failures MUST be reported with sanitized provider/model metadata and MUST NOT leak decrypted API keys.

#### Scenario: Adapter resolved
- **WHEN** the selected provider has `adapter_kind="openai_compat"`
- **THEN** the gateway uses the OpenAI-compatible adapter for request formatting and response parsing

#### Scenario: Unknown adapter kind
- **WHEN** a provider row contains an unsupported adapter kind
- **THEN** the gateway rejects the call with a configuration error before attempting an upstream request
