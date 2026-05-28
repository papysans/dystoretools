# Tasks — add-ai-chat-console

## 1. Dependencies and Configuration

- [x] 1.1 Add backend dependencies: `sqlglot`, `cryptography`, `sse-starlette`, and token-estimation helper if needed
- [x] 1.2 Add frontend dependencies: `@ant-design/x` and SQL syntax highlighting package
- [x] 1.3 Add `.env.example` entries for `CHAT_MASTER_ENCRYPTION_KEY`, `MYSQL_CHAT_READONLY_USER`, and `MYSQL_CHAT_READONLY_PASSWORD`
- [x] 1.4 Add settings validation for `CHAT_MASTER_ENCRYPTION_KEY` as a 32-byte base64 key
- [x] 1.5 Add `backend/scripts/create_chat_readonly_user.sql` documenting SELECT grants and explicit secret/control-table exclusions
- [x] 1.6 Add operator docs for creating or rotating the chat readonly MySQL user

## 2. Database Models and Migration

- [x] 2.1 Add SQLAlchemy models for `llm_provider` and `llm_model`
- [x] 2.2 Add SQLAlchemy models for `chat_conversation` and `chat_message`
- [x] 2.3 Add indexes for conversation ordering, message lookup, provider/model lookup, and chat usage totals
- [x] 2.4 Add monthly partitioning or archive-compatible structure for `chat_message.created_at`
- [x] 2.5 Create Alembic revision for provider/model/chat tables
- [x] 2.6 Seed provider presets for DeepSeek, Kimi, OpenAI, and Anthropic
- [x] 2.7 Migrate existing DeepSeek/Kimi settings into provider/model rows when keys are present
- [x] 2.8 Add migration tests or smoke checks for model importability and default chat model uniqueness

## 3. Provider Registry Backend

- [x] 3.1 Implement AES-256-GCM encryption/decryption utility for provider API keys
- [x] 3.2 Implement key masking and fingerprint helpers that never return plaintext
- [x] 3.3 Implement provider repository/service CRUD operations
- [x] 3.4 Implement model repository/service CRUD operations and single default-chat invariant
- [x] 3.5 Implement provider list/detail/create/update/delete FastAPI endpoints
- [x] 3.6 Implement model create/update/enable/disable/default FastAPI endpoints
- [x] 3.7 Implement provider connection test endpoint with sanitized errors
- [x] 3.8 Implement upstream model discovery endpoint for OpenAI-compatible providers
- [x] 3.9 Add backend tests for key encryption, no-plaintext responses, key replacement semantics, and default model invariants

## 4. Gateway Adapter Refactor

- [x] 4.1 Define provider-neutral request/response dataclasses for text, streaming deltas, tool schemas, and tool calls
- [x] 4.2 Implement `OpenAICompatibleAdapter` using configurable base URL, headers, model, streaming, and tools
- [x] 4.3 Implement `AnthropicAdapter` using Claude Messages API format and tool-use conversion
- [x] 4.4 Refactor `gateway.complete()` to resolve provider/model from `llm-provider-registry`
- [x] 4.5 Preserve legacy `gateway.complete(prompt, kind=..., prefer=...)` callers through a compatibility path
- [x] 4.6 Add capability checks for chat, function calling, streaming, and context window
- [x] 4.7 Extend `ai_generation` accounting to include provider_id and serialized tool-call metadata
- [x] 4.8 Keep PII scrubbing enabled by default for legacy/batch calls and allow chat-agent calls to opt out under merchant-authorized raw analysis
- [x] 4.9 Add mocked adapter tests for OpenAI-compatible text, OpenAI-compatible tool calls, Anthropic text, Anthropic tool calls, retry behavior, and accounting

## 5. SQL Sandbox

- [x] 5.1 Create `backend/dystore/sqlsandbox/` module structure
- [x] 5.2 Define table access policy configuration for allowed business tables and forbidden control/secret tables
- [x] 5.3 Define `config/pii_columns.yaml` with initial PII columns from order/comment/customer-facing tables
- [x] 5.4 Implement `sqlglot` parser and single-SELECT AST gate
- [x] 5.5 Implement forbidden-table detection across aliases, joins, subqueries, CTEs, and schema-qualified names
- [x] 5.6 Implement AST-level `LIMIT` injection and max-row reduction
- [x] 5.7 Implement readonly MySQL execution pool using chat readonly credentials
- [x] 5.8 Implement 30-second execution timeout and structured timeout errors
- [x] 5.9 Implement dual-channel result mapper producing masked `llm_rows` and original `ui_rows`
- [x] 5.10 Implement structured result contract with normalized SQL, columns, row count, capped flag, latency, status, and error codes
- [x] 5.11 Add sandbox tests for valid SELECT, DML rejection, DDL rejection, multi-statement rejection, forbidden table rejection, limit injection, row cap, and PII masking

## 6. Schema Metadata

- [x] 6.1 Create schema metadata file with table descriptions, key columns, time columns, common joins, and PII annotations
- [x] 6.2 Generate compact schema summary text for the chat system prompt
- [x] 6.3 Implement `describe_schema(table_name)` service with forbidden-table filtering
- [x] 6.4 Add tests that schema summary excludes secret/control tables and includes core scraped data tables

## 7. Chat Tool Registry

- [x] 7.1 Create `backend/dystore/chat/tools.py` or equivalent registry module
- [x] 7.2 Define tool descriptor schema with name, description, JSON parameter schema, handler, and return contract
- [x] 7.3 Register `run_readonly_sql` tool and ensure chat-agent LLM-visible results include raw `ui_rows` for merchant-authorized analysis
- [x] 7.4 Register `describe_schema` tool
- [x] 7.5 Register `render_table` tool with preview caps and source metadata
- [x] 7.6 Register `render_chart` tool with ECharts option allowlist validation
- [x] 7.7 Implement tool-call and tool-result persistence hooks
- [x] 7.8 Add tests for tool schema export, disabled tool omission, invalid arguments, tool error feedback, and render-spec validation

## 8. Chat Service Backend

- [x] 8.1 Create `backend/dystore/chat/` module structure for conversation service, agent loop, SSE events, and prompt assembly
- [x] 8.2 Implement conversation CRUD/list endpoints under `/api/v1/chat/conversations`
- [x] 8.3 Implement message history endpoint for a conversation
- [x] 8.4 Implement sliding-window context assembly: system prompt, schema summary, first user message, and latest 10 turns
- [x] 8.5 Implement SSE endpoint `POST /api/v1/chat/conversations/{id}/messages:stream`
- [x] 8.6 Persist user messages before generation starts
- [x] 8.7 Implement bounded agent loop with default `MAX_AGENT_TURNS=10`
- [x] 8.8 Dispatch registered tool calls and stream `tool_call` / `tool_result` events
- [x] 8.9 Persist assistant final text, failed assistant messages, chart/table/sql artifacts, tokens, and cost
- [x] 8.10 Handle client disconnects without losing already persisted messages
- [x] 8.11 Register chat API router in FastAPI application
- [x] 8.12 Add backend tests for conversation persistence, SSE event order, agent loop terminal response, tool call flow, turn budget exhaustion, and stream error persistence

## 9. Provider Settings Frontend

- [x] 9.1 Add API client functions for provider and model CRUD/test/discovery/default selection
- [x] 9.2 Add provider settings route under the existing settings/navigation structure
- [x] 9.3 Build provider list view with enabled state, adapter kind, base URL, masked key status, and model summary
- [x] 9.4 Build add/edit provider form with "re-enter to update" API key behavior
- [x] 9.5 Build model list/edit/default selection UI for each provider
- [x] 9.6 Add provider test connection and model discovery interactions
- [x] 9.7 Add frontend typecheck coverage for provider/model API types

## 10. Chat Frontend

- [x] 10.1 Add `/chat` route and sidebar menu entry
- [x] 10.2 Build chat page layout with Ant Design X conversations list, bubble list, sender, and thought/tool trace area
- [x] 10.3 Add API client functions for conversations, messages, enabled chat models, and SSE message streaming
- [x] 10.4 Add model selector populated from enabled chat-capable models
- [x] 10.5 Implement SSE event parser for text deltas, tool calls, tool results, artifacts, done, and error
- [x] 10.6 Render Markdown assistant messages without allowing unsafe HTML/script injection
- [x] 10.7 Render table artifacts with AntD Table and capped-row indicator
- [x] 10.8 Render chart artifacts with ECharts from validated render specs
- [x] 10.9 Render SQL artifacts with syntax highlighting and raw merchant-visible result support
- [x] 10.10 Add conversation reload/resume behavior after page refresh
- [x] 10.11 Add frontend typecheck/build verification for chat page

## 11. Integration and Observability

- [x] 11.1 Add structured logs for chat turn start/end, provider/model selection, tool dispatch, SQL rejection, and agent budget exhaustion
- [x] 11.2 Add usage totals to conversation list API from persisted assistant messages
- [x] 11.3 Ensure `ai_generation` rows are linked to chat assistant messages where applicable
- [x] 11.4 Add system health detail for provider registry encryption readiness and chat readonly DB connectivity
- [x] 11.5 Update README/operator guide with provider setup, chat readonly user setup, and chat usage notes

## 12. Verification

- [x] 12.1 Run backend unit tests for provider registry, gateway, SQL sandbox, tool registry, and chat service
- [x] 12.2 Run frontend typecheck and production build
- [x] 12.3 Run Alembic upgrade against local MySQL and verify all new tables exist
- [x] 12.4 Manually configure a DeepSeek or Kimi provider from the UI and run provider test connection
- [x] 12.5 Manually ask a chat question that produces SQL, a table, and a chart
- [x] 12.6 Verify raw phone/address/order identifiers do not appear in LLM-bound prompts or `ai_generation` input hashes/log payloads
- [x] 12.7 Verify conversation history persists across API restart
- [x] 12.8 Review and sign off that dashboard-widget promotion remains out of scope for this change
