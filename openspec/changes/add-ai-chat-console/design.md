## Context

`bootstrap-merchant-platform` already gives the user a local FastAPI + MySQL + Redis + Ant Design Pro merchant console with scraped Douyin shop data, AI comment/content workers, and a thin DeepSeek/Kimi LLM gateway. That baseline is useful for predefined workflows, but the user still needs manual SQL or spreadsheet work for ad-hoc operational questions such as "上周物流类差评涨了多少?" or "对比上月这周搜索流量趋势怎么样?".

This change adds a standalone conversational analytics console. The important constraint is that the LLM is allowed to write SQL, so the safety boundary must be the backend SQL sandbox rather than the prompt. The second major change is that LLM provider configuration moves from hardcoded `.env` settings into a UI-managed provider registry, while retaining direct REST calls and the "no LangChain / no LlamaIndex / no RAG" rule.

The user accepted these product decisions before this design:

- The chat surface is an independent page, not a global floating assistant.
- Conversations persist permanently in MySQL, with archival mechanics aligned with existing time-series retention.
- The LLM may directly write SQL, but only through a readonly sandbox.
- Charts are in scope. The LLM/tool layer may return ECharts render specs for frontend rendering.
- PII uses a merchant-authorized raw analysis policy for chat: SQL results still include masked `llm_rows` and raw `ui_rows`, but the chat agent may pass raw `ui_rows` to the selected LLM so it can answer exact order/contact questions for the local merchant operator.
- Provider management must be configurable from the frontend and must support DeepSeek, Kimi, OpenAI, Anthropic, and custom providers.
- Dashboard-widget promotion from chat artifacts is intentionally a follow-up, but this change stores enough metadata to make it additive later.

## Goals / Non-Goals

**Goals:**

- Add `/chat` as a full Ant Design X conversational analytics page with streaming responses, conversation history, model selection, Markdown, tables, charts, and tool-call trace display.
- Add a backend chat service with persistent conversations, bounded agent loop, SSE streaming, sliding-window context, and durable message/tool-result records.
- Let the LLM query scraped merchant data through `run_readonly_sql`, guarded by a dedicated readonly MySQL account, SQL AST validation, table allow/deny rules, forced row limits, timeout, and explicit merchant-authorized raw result handling.
- Add a small tool registry with `run_readonly_sql`, `describe_schema`, `render_table`, and `render_chart`.
- Add UI-managed LLM provider/model registry with encrypted API keys and dynamic runtime routing.
- Extend the LLM gateway with function calling while preserving existing batch AI use cases and per-call accounting.

**Non-Goals:**

- No LangChain, LlamaIndex, vector database, embeddings, or RAG.
- No dashboard-widget promotion in this change. Chat artifact persistence is the hook for a later "pin to dashboard" change.
- No multi-user sharing, RBAC, tenancy, conversation export, mobile client, or external SaaS deployment.
- No hard cost cap for chat. Usage telemetry is stored, but the user explicitly chose no cap.
- No automatic Feige/IM replies. Any generated reply remains a draft only.

## Decisions

### Architecture: backend-owned agent loop over frontend orchestration

The backend owns the loop: user message -> LLM call -> tool call -> tool result -> LLM call -> final answer. The frontend receives SSE events and renders them. This keeps API keys, SQL execution, raw-data policy, and tool authorization entirely server-side.

Rejected alternative: browser-driven tool orchestration. That would expose more protocol details to the frontend, make raw-data handling harder to reason about, and complicate retries.

### LLM data access: hybrid SQL tool over predefined business tools only

The first tool set is deliberately small. `run_readonly_sql` provides broad coverage for the existing ~30 tables; `describe_schema` lets the model request detailed table/column metadata; `render_table` and `render_chart` convert results into UI artifacts.

Rejected alternative: create 15-20 predefined business tools first. It is safer but sharply limits expressiveness and delays value. The SQL sandbox is harder, but it is the right core for conversational analytics.

### SQL sandbox: AST gate plus database permissions

`sqlglot` parses SQL into an AST. The sandbox accepts only a single `SELECT` statement, rejects DML/DDL/session statements, rejects forbidden tables, rejects `information_schema` by default, injects `LIMIT` at AST level when missing, and caps `max_rows`. The execution pool uses `MYSQL_CHAT_READONLY_USER`, a MySQL user that has `SELECT` only on business data tables.

This is defense in depth: AST checks are the application guardrail; MySQL grants are the blast-radius guardrail. String-only checks are not acceptable.

### PII: merchant-authorized raw chat analysis

The SQL executor returns two row sets for the same query:

- `llm_rows`: masked values for any column in `config/pii_columns.yaml` plus best-effort free-text patterns.
- `ui_rows`: original values for rendering to the local operator.

For chat analytics, the selected LLM receives the complete tool result, including raw `ui_rows`, because the authenticated user is the merchant operator and explicitly needs exact order identifiers, phone/address fields, and customer-facing facts to diagnose operations issues. The masked `llm_rows` channel remains in the response for non-chat callers, display comparison, and future privacy modes, but it is not the only LLM-visible channel in chat.

Rejected alternative: column whitelist only. It is safer but makes normal order/comment analysis too awkward. Rejected alternative: strict LLM-only masking. That prevents the assistant from answering exact merchant questions such as "which order number/customer phone needs follow-up?"

### Schema injection: summary first, detail on demand

The system prompt carries a compact schema summary: table names, purpose, key time columns, common joins, and personal-field notes. Full columns and examples are fetched with `describe_schema(table_name)`.

This avoids paying a full 30-table DDL prompt cost every turn and reduces model confusion. The schema summary is generated from an explicit YAML/metadata file, not inferred at runtime from all tables every request.

### Conversation memory: sliding window first

The agent context includes the system prompt, schema summary, the first user message, and the latest 10 conversation turns. Old turns remain in MySQL but are not summarized in V1.

Rejected alternative: automatic summary compression. It can preserve longer context but adds another LLM call and can silently lose important detail. Sliding window is enough for the expected single-session analytics workflow.

### Streaming protocol: SSE over WebSocket

Chat generation uses `POST /api/v1/chat/conversations/{id}/messages:stream` returning Server-Sent Events. Existing WebSockets remain for dashboard/task/alert channels.

SSE is enough for one-way generation streaming, works well behind the existing Vite/nginx proxy, and is simpler to reconnect. It also avoids mixing long-lived chat generation semantics into existing broadcast WebSocket channels.

### Provider registry: two adapter kinds in V1

Provider records store `adapter_kind`:

- `openai_compat`: DeepSeek, Kimi, OpenAI, DashScope, Volcengine/豆包, GLM, Qianfan-compatible endpoints, Ollama, LM Studio.
- `anthropic`: Claude Messages API.

This gives broad coverage without an adapter hierarchy explosion. Google Gemini can be added later either through an OpenAI-compatible endpoint or a third adapter kind if needed.

### API key storage: AES-256-GCM with `.env` master key

Provider API keys are encrypted before DB storage using AES-256-GCM. The encryption master key is `CHAT_MASTER_ENCRYPTION_KEY`, a 32-byte base64 value in `.env`. Provider list/detail endpoints never return plaintext; they return only `key_set`, a masked fingerprint, and metadata.

Rejected alternative: plaintext DB storage because the app is local. Local DB backup/export leakage is still realistic. Rejected alternative: external secret manager. V1/V2 explicitly use `.env`, not hosted secret management.

### Existing LLM behavior: compatibility wrapper during migration

Current callers use `gateway.complete(prompt, kind=..., max_tokens=..., prefer=...)`. The gateway will keep a compatibility path that resolves the default chat/model from `llm_model.is_default_for_chat` and maps legacy `prefer="long_context"` to the best enabled long-context model.

Function calling uses a neutral return type (`text`, `tool_calls`, usage, model/provider metadata) so existing non-tool callers can keep reading `text`.

### Artifact storage: message kinds and render specs

`chat_message.kind` supports `text`, `tool_call`, `tool_result`, `chart`, `table`, and `sql_result`. Tool calls/results are persisted in JSON columns. Renderable artifacts include `render_spec`, `source_sql`, and `source_message_id` when applicable.

This is not dashboard promotion yet. It is the stable substrate for a later "pin this chart/table to a dashboard" change.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LLM writes expensive or unsafe SQL | Dedicated readonly MySQL user, `sqlglot` single-SELECT AST gate, table allowlist/denylist, forced `LIMIT`, row cap, timeout, and tests for DML/DDL/comment/multi-statement bypass cases. |
| Raw personal/order data reaches the selected LLM | This is an intentional product decision for the single-merchant local console. Access remains constrained by the SQL sandbox, readonly DB user, table allowlist, row caps, and explicit chat prompt. Legacy/batch AI paths keep the default scrubber unless a caller opts out. |
| The model hallucinates table/column names | Compact schema summary plus `describe_schema`; failed SQL is returned to the model as a structured tool error with guidance; agent loop budget prevents infinite retries. |
| Provider keys leak through frontend or logs | Never return plaintext API keys; log only provider id/model and masked fingerprints; encrypt at rest with AES-GCM; redact request payloads on provider CRUD endpoints. |
| Anthropic function calling diverges from OpenAI tool schema | Gateway owns a provider-neutral `ToolSchema` and adapter-specific conversion. Tests cover at least one tool-call round trip per adapter kind with mocked upstream responses. |
| SSE stream is interrupted mid-turn | Persist user message before generation and persist each tool call/result as it happens. A disconnected frontend can reload the conversation and see the last durable state; the backend may finish or mark the assistant turn failed. |
| Chat tables grow indefinitely | Conversations are permanent by product decision; `chat_message` is partitioned monthly and can be archived after 12 months without deleting the conversation index. |
| No hard cost cap | Store tokens/cost/provider/model per assistant message and `ai_generation` row. Surface usage in conversation metadata. Add cap later as configuration if needed. |

## Migration Plan

1. Add dependencies: `sqlglot`, `cryptography`, `sse-starlette`, token estimator dependency if used, `@ant-design/x`, and SQL syntax highlighter.
2. Add Alembic migration for `llm_provider`, `llm_model`, `chat_conversation`, `chat_message`, plus indexes and monthly partitioning for `chat_message.created_at`.
3. Add `CHAT_MASTER_ENCRYPTION_KEY`, `MYSQL_CHAT_READONLY_USER`, and `MYSQL_CHAT_READONLY_PASSWORD` to `.env.example`.
4. Add `backend/scripts/create_chat_readonly_user.sql` and operator docs for running it against local MySQL.
5. Seed built-in provider templates and import existing DeepSeek/Kimi settings from current settings/env values when present.
6. Implement provider registry service and settings UI, then migrate `llm-gateway` to dynamic provider lookup while keeping the legacy `complete()` calling shape.
7. Implement SQL sandbox and raw-data policy before exposing chat endpoints.
8. Implement tool registry and backend agent loop with mocked LLM/tool tests.
9. Implement `/chat` frontend page with SSE event consumption, conversation history, model selector, tool trace, table, and chart rendering.
10. Run backend tests for provider registry, gateway adapters, sandbox bypasses, and chat service; run frontend typecheck/build.

Rollback is local-machine only: disable the `/chat` route and chat API router, keep provider registry data intact, and restore legacy DeepSeek/Kimi settings. The migration is additive except for gateway routing internals.

## Open Questions

- Exact canonical table descriptions and personal-field annotations must be finalized from the implemented models before coding `schema_summary.yaml` and `pii_columns.yaml`.
- Whether `chat_message` should physically store unmasked UI rows for large SQL results or store only a capped preview plus a result handle. Default: store capped preview only.
- Which OpenAI-compatible providers beyond DeepSeek/Kimi/OpenAI should be shipped as UI presets on day one. Default: support custom entries but only preseed the four confirmed providers.
- Whether Anthropic should be allowed for SQL-writing chat if a chosen Claude model lacks reliable tool-use metadata in the current adapter. Default: expose capability flags and hide unsupported models from chat selection.
