## Why

`bootstrap-merchant-platform` lands the scraping + AI batch-workers + dashboard, but the user can only consume AI value through pre-baked surfaces (差评聚类报告 / 文案工坊 / 标题生成). Ad-hoc questions — "上周物流类差评涨了多少?"、"我现在卖得最差的 5 个 SKU 的客单价分布?"、"对比上月这周搜索流量趋势怎么样?" — still require manual SQL or spreadsheet work. The merchant operator wants a **ChatGPT-style conversational interface** that can read the same scraped data and answer in natural language, with charts and tables rendered inline.

In parallel, the current `llm-gateway` hardcodes DeepSeek + Kimi via `.env`. The user wants to add/switch LLM providers (OpenAI, Anthropic, custom OpenAI-compatible endpoints, local Ollama) from the UI without restarting the service. This change introduces a provider registry and refactors the gateway to consume it.

## What Changes

> 2026-05-21 update: chat now uses a merchant-authorized raw analysis mode. Any older "LLM only sees masked PII" wording in this proposal is superseded by the current behavior: SQL results still include masked `llm_rows`, but the chat agent may pass raw `ui_rows` to the selected LLM when answering the local merchant operator.

- **New independent page**: `/chat` in the React dashboard — Ant Design X `<Bubble>` / `<Sender>` / `<Conversations>` / `<ThoughtChain>` based.
- **Conversational agent** that interleaves text replies with tool calls. The agent loop runs until the LLM returns a terminal message (no further tool calls) or a turn budget is exhausted.
- **Direct SQL writing by the LLM** via a `run_readonly_sql` tool — backed by a separate MySQL read-only account, sqlglot-based AST whitelist (SELECT only, no DML/DDL, no information_schema unless explicitly allowed), forced `LIMIT` injection, 30-second timeout, and a row cap.
- **Dual-channel PII masking**: the LLM sees masked values (`13800138000` → `138****0000`, `北京市朝阳区某街某号` → `北京市朝阳区****`); the frontend renders the original values from the unmasked result set. PII column list is declared per table in a YAML registry; the SQL execution path branches a "for-LLM" and "for-UI" copy at the row mapper.
- **Inline chart / table / SQL artifact rendering**: tools return `render_spec` objects that the frontend renders as ECharts components, AntD tables, or SQL syntax-highlighted code blocks.
- **Persistent conversations** in MySQL (永久保留 + 12-month archive partition, same retention rule as scraped data). Conversations and messages survive process restarts; the frontend resumes from history on reload.
- **Multi-provider LLM management**: provider/model CRUD via REST + Ant Pro settings page; AES-256-GCM at-rest encryption of API keys with the master key in `.env`; model selector at the top of the chat page.
- **First-class providers shipped**: DeepSeek + Kimi + OpenAI + Anthropic. DeepSeek and Kimi are seeded from `.env` on first migration so existing functionality keeps working.
- **`llm-gateway` refactor**: replace hardcoded provider routing with a dynamic lookup against the registry; add function-calling support (OpenAI-compatible `tools=[...]` schema + Anthropic-flavor adaptation in the adapter).
- **V-next hooks**: `chat_message.kind` enumerates `text | tool_call | tool_result | chart | table`; `tool_calls_json` / `tool_results_json` are persisted in full so a later change can promote individual messages into a "dashboard widget" without re-executing the conversation.
- **Excluded from this change**: dashboard-widget promotion / 看板 sediment feature (planned as a separate V-next change), conversation export/share, mobile chat client, cost caps (user direction: 不限).

## Capabilities

### New Capabilities

- **`chat-service`**: REST + SSE endpoint set for conversation management (`POST /api/v1/chat/conversations`, `GET /…/conversations`, `POST /…/conversations/{id}/messages` SSE), agent loop (LLM → tool dispatch → result → LLM, bounded by `MAX_AGENT_TURNS=10`), sliding-window context management (last 10 turns + first user turn + system prompt + schema summary), and message persistence.
- **`sql-sandbox`**: A `run_readonly_sql(sql, max_rows)` callable consumed by the tool registry. Uses a dedicated MySQL `chat_readonly` user with `SELECT` grant only. sqlglot AST gate rejects non-`SELECT`, references to forbidden tables (`llm_provider`, `chat_*`, `session_event`), and queries without a parsable `FROM`. Forces `LIMIT` injection at AST level if absent; caps row count at 1000. 30-second statement timeout via MySQL `MAX_EXECUTION_TIME` hint. Returns both an LLM-bound row set (with PII masked per the column registry) and a UI-bound row set (original values), in a structured response.
- **`chat-tool-registry`**: Tool descriptor schema (name, OpenAI-compatible JSON schema for parameters, handler callable, return-shape contract); built-in tools shipped: `run_readonly_sql`, `describe_schema`, `render_chart`, `render_table`. Tool execution is observable: each call writes a row to `chat_message` with `kind="tool_call"` and the subsequent `chat_message` with `kind="tool_result"`.
- **`llm-provider-registry`**: `llm_provider` and `llm_model` MySQL tables; AES-256-GCM at-rest encryption of `api_key`; FastAPI CRUD endpoints under `/api/v1/llm/providers` and `/api/v1/llm/models`; `POST /providers/{id}/test` performs a 1-token completion to validate; `GET /providers/{id}/models` calls the upstream `/v1/models` endpoint where supported; settings page in the React dashboard with masked-key display and "re-enter to update" semantics. The provider table has two adapters built-in: `openai_compat` (covers DeepSeek, Kimi, OpenAI, Volcengine/豆包, DashScope/通义, GLM, local Ollama, LM Studio) and `anthropic` (Claude messages API).

### Modified Capabilities

- **`llm-gateway`** — MODIFIED:
  - Replaces the hardcoded DeepSeek/Kimi `prefer="long_context"` routing with **dynamic provider/model lookup against `llm-provider-registry`**. Callers pass `provider_id` and `model_name` (or rely on the row marked `is_default_for_chat`).
  - ADDS function-calling support: `LLM.complete(..., tools: list[ToolSchema] | None = None)` returns a structured result distinguishing `text` completions from `tool_calls`. Adapters translate the gateway's neutral `ToolSchema` to provider-specific shapes.
  - PII scrubbing requirement is unchanged but now consumes the PII column registry from `sql-sandbox` for tabular tool results in addition to the existing free-text scrubbing for comments.

## Impact

- **Affected specs**: ADD `chat-service`, `sql-sandbox`, `chat-tool-registry`, `llm-provider-registry`. MODIFY `llm-gateway` (provider routing + function calling).
- **Affected code**:
  - Backend new packages: `backend/dystore/chat/` (service, agent loop, SSE), `backend/dystore/sqlsandbox/` (executor, AST gate, PII mask), `backend/dystore/llm/registry/` (CRUD, encryption, adapters refactor).
  - Backend modified: `backend/dystore/llm/gateway.py` (dynamic routing), `backend/dystore/db/models/` (new models: `llm_provider`, `llm_model`, `chat_conversation`, `chat_message`).
  - Frontend new pages: `web/src/pages/Chat/` (page + components consuming Ant Design X), `web/src/pages/Settings/Providers/` (CRUD UI).
  - Alembic: one new revision adds 4 tables + monthly partition on `chat_message.created_at`.
- **External dependencies added**:
  - Python: `sqlglot` (AST gate), `cryptography` (AES-256-GCM), `sse-starlette` (SSE response helper), `tiktoken` (token estimation for sliding window).
  - Frontend: `@ant-design/x` (^1.x), `react-syntax-highlighter` (SQL block rendering).
- **Schema**: 4 new MySQL tables (`llm_provider`, `llm_model`, `chat_conversation`, `chat_message`). `chat_message` is RANGE-partitioned monthly on `created_at` and follows the 12-month retention rule applied to all time-series tables.
- **`.env` additions**: `CHAT_MASTER_ENCRYPTION_KEY` (32-byte base64); `MYSQL_CHAT_READONLY_USER` and `MYSQL_CHAT_READONLY_PASSWORD` (separate creds for the SQL sandbox connection pool).
- **Migration prerequisites**: A bootstrap migration MUST create the `chat_readonly` MySQL user with `SELECT` grants on the business-data tables and explicit `REVOKE` on `llm_provider`, `llm_model`, `chat_*`, `session_event`. Documented as a one-shot script in `backend/scripts/create_chat_readonly_user.sql`.
- **Risk surface**:
  - **SQL injection by LLM is the highest-risk vector**. Mitigated via dedicated read-only user (defense in depth), sqlglot AST (no string parsing), table allowlist, `LIMIT` enforcement, timeout. Penetration test cases shipped as part of `sql-sandbox` tests.
  - **PII leakage through LLM context** is the secondary risk. Mitigated via dual-channel return — LLM never sees raw `receiver_phone` / `receiver_address` / `buyer_nick` even when the SQL selects those columns.
  - **API key exfiltration via the frontend** is mitigated by the never-return-plaintext rule: edit flows accept new keys but the read side returns only `sk-…ab12` and a `key_set: true` flag.
- **Out-of-scope follow-ups (V-next candidates)**:
  - "Sediment to dashboard": promote a chat artifact (chart / table / SQL view) into a pinnable widget on a 看板 page. Schema hooks (`chat_message.kind`, `tool_results_json`) are intentionally introduced in this change so the follow-up is purely additive.
  - Conversation export (markdown / JSON), conversation tagging, multi-user sharing (single-user system: deferred indefinitely).
