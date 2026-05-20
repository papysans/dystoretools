## ADDED Requirements

### Requirement: Provider Routing Between DeepSeek and Kimi
The system SHALL expose a single async `LLM.complete(prompt: str, *, kind: str, max_tokens: int = 2048, prefer: str | None = None) -> str` interface. The default provider SHALL be DeepSeek; if `prefer="long_context"` or the assembled prompt exceeds 32 K tokens, the call SHALL route to Kimi. The system MUST NOT depend on LangChain, LlamaIndex, or any heavyweight framework.

#### Scenario: Short prompt routes to DeepSeek
- **WHEN** a caller invokes `LLM.complete` with a 4000-token prompt and no `prefer`
- **THEN** the system SHALL send the request to DeepSeek and SHALL NOT call Kimi

#### Scenario: Long prompt routes to Kimi
- **WHEN** a caller invokes `LLM.complete` with a 60000-token prompt
- **THEN** the system SHALL route to Kimi and SHALL log the routing decision on the resulting `ai_generation` row

### Requirement: Per-Call Accounting to ai_generation
Every LLM call SHALL produce one row in `ai_generation` with `kind`, `input_hash` (SHA-256 of the assembled prompt), `output_text`, `model`, `tokens_in`, `tokens_out`, `cost`, `created_at`. The system SHALL NOT skip accounting under any code path.

#### Scenario: Successful generation
- **WHEN** an LLM call returns a non-empty completion
- **THEN** the system SHALL persist the accounting row before returning the text to the caller

#### Scenario: Provider returns an error
- **WHEN** the LLM API call fails after retries
- **THEN** the system SHALL still write an `ai_generation` row with `output_text=NULL`, `tokens_out=0`, `cost=0`, and an `error_msg` field

### Requirement: PII Scrubbing Before Prompt Assembly
Before sending any prompt to an external LLM provider, the system SHALL replace customer-identifying values with stable placeholders: full mobile phone numbers, full street addresses, customer nicknames, and `order_sn` values. Replacements MUST use a deterministic mapping cached per-conversation so the LLM can reason about "customer A" vs "customer B" without seeing real identities.

#### Scenario: Comment contains a phone number
- **WHEN** a comment body `"我手机13900000001收不到验证码"` is sent to the LLM
- **THEN** the prompt actually sent SHALL contain `"我手机<PHONE_001>收不到验证码"`

#### Scenario: Comment lacks PII
- **WHEN** a comment body contains no detectable PII
- **THEN** the prompt sent SHALL be identical to the input

### Requirement: Bounded Retry with Exponential Backoff
The system SHALL retry transient LLM provider errors (HTTP 429, 5xx, network timeouts) up to 3 times with exponential backoff starting at 2 seconds. Non-transient errors (HTTP 400, 401, 403) SHALL NOT be retried.

#### Scenario: Provider returns 429 then succeeds
- **WHEN** the first call returns HTTP 429 and the second call succeeds
- **THEN** the caller SHALL receive the successful completion and accounting SHALL reflect only one billable call
