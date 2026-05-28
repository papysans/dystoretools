## ADDED Requirements

### Requirement: Conversation persistence
The system SHALL persist chat conversations and messages in MySQL so history survives process restarts. Each conversation MUST store title, selected provider/model, created_at, updated_at, archived_at, token/cost totals, and last message preview. Each message MUST store conversation_id, role, kind, content, provider/model metadata when applicable, tool call/result JSON when applicable, token/cost metrics, error state, and created_at.

#### Scenario: Create conversation
- **WHEN** the frontend calls `POST /api/v1/chat/conversations` with an optional title and selected model
- **THEN** the system creates a `chat_conversation` row and returns its id, title, selected model, and created_at

#### Scenario: Reload conversation history
- **WHEN** the API service restarts and the frontend calls `GET /api/v1/chat/conversations`
- **THEN** previously created conversations are returned ordered by `updated_at DESC`

#### Scenario: Fetch messages
- **WHEN** the frontend calls `GET /api/v1/chat/conversations/{conversation_id}/messages`
- **THEN** the system returns all persisted messages for that conversation in chronological order, including renderable table/chart metadata

### Requirement: Streaming chat turn endpoint
The system SHALL expose a streaming endpoint `POST /api/v1/chat/conversations/{conversation_id}/messages:stream` that accepts a user message, persists it before generation, runs the agent loop, and emits Server-Sent Events for assistant text deltas, tool calls, tool results, renderable artifacts, completion, and errors.

#### Scenario: Successful streamed answer
- **WHEN** the user sends a message to the stream endpoint
- **THEN** the first durable write is the user `chat_message`
- **AND** the response emits SSE events until a final `done` event is sent
- **AND** the final assistant message is persisted before `done`

#### Scenario: Tool trace streamed
- **WHEN** the LLM requests `run_readonly_sql`
- **THEN** the stream emits a `tool_call` event before execution and a `tool_result` event after execution
- **AND** both events reference persisted `chat_message` ids

#### Scenario: Stream error
- **WHEN** the agent loop fails after the user message was persisted
- **THEN** the stream emits an `error` event
- **AND** the conversation contains a failed assistant or tool message with an error payload

### Requirement: Bounded agent loop
The system SHALL run a bounded agent loop that alternates between LLM calls and registered tool execution until the LLM returns a terminal assistant message or the configured turn budget is exhausted. The default budget MUST be 10 tool/LLM iterations per user turn.

#### Scenario: Terminal response
- **WHEN** the LLM returns assistant text with no tool calls
- **THEN** the agent loop stops and persists that text as the final assistant message

#### Scenario: Turn budget exhausted
- **WHEN** the LLM still requests tools after `MAX_AGENT_TURNS` iterations
- **THEN** the agent loop stops, persists an assistant error message, and returns a user-visible explanation that the analysis exceeded the tool-call limit

#### Scenario: Unknown tool requested
- **WHEN** the LLM requests a tool name that is not registered
- **THEN** the system returns a structured tool error to the LLM and counts it against the turn budget

### Requirement: Sliding-window context assembly
The system SHALL assemble LLM context from the chat system prompt, schema summary, first user message, and the latest 10 conversation turns. Older messages SHALL remain persisted but SHALL NOT be sent unless a future summarization feature is added.

#### Scenario: Short conversation
- **WHEN** a conversation has fewer than 10 previous turns
- **THEN** all previous turns are eligible for the next LLM context after PII and tool-result masking rules are applied

#### Scenario: Long conversation
- **WHEN** a conversation has more than 10 previous turns
- **THEN** the assembled context includes the first user message and the latest 10 turns, excluding older middle turns

### Requirement: Chat page frontend
The system SHALL add an independent `/chat` page in the Ant Design Pro frontend using Ant Design X components for conversation list, message bubbles, sender input, and tool-call trace display. The page MUST support model selection from enabled chat-capable models, streaming answer rendering, Markdown rendering, table artifacts, and ECharts chart artifacts.

#### Scenario: User opens chat page
- **WHEN** the user navigates to `/chat`
- **THEN** the page loads conversation history and enabled chat-capable models
- **AND** it renders the latest selected conversation or an empty new-chat state

#### Scenario: Chart artifact renders
- **WHEN** a streamed assistant result includes a chart render spec
- **THEN** the frontend renders the chart with ECharts inside the corresponding assistant bubble

#### Scenario: Table artifact renders
- **WHEN** a streamed assistant result includes a table render spec
- **THEN** the frontend renders an AntD table with the provided columns and capped rows

### Requirement: Chat usage telemetry
The system SHALL record provider_id, model_name, tokens_in, tokens_out, and cost_cny for each assistant LLM call associated with a chat turn. Conversation list responses MUST include cumulative tokens and cost.

#### Scenario: Assistant call succeeds
- **WHEN** an assistant LLM call completes
- **THEN** the corresponding `chat_message` and `ai_generation` records include provider/model, token, and cost fields

#### Scenario: Conversation list shows totals
- **WHEN** the frontend loads conversation history
- **THEN** each conversation item includes cumulative tokens and cost derived from its assistant messages

### Requirement: Dashboard-promotion hooks
The system SHALL persist renderable chat artifacts with enough metadata for a future dashboard-widget promotion change. This change MUST NOT implement dashboard pinning, but each chart/table/sql_result message MUST store `kind`, `render_spec`, `source_sql` when applicable, and the source tool result id.

#### Scenario: Chart result is persisted
- **WHEN** a tool returns a chart render spec
- **THEN** the system persists a `chat_message` with `kind="chart"` and stores the render spec in JSON

#### Scenario: No dashboard widget is created
- **WHEN** a chart or table artifact is produced
- **THEN** the system does not create any dashboard widget row or dashboard route entry in this change
