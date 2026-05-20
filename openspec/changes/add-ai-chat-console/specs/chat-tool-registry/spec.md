## ADDED Requirements

### Requirement: Tool descriptor registry
The system SHALL provide a chat tool registry that exposes tool descriptors with name, description, OpenAI-compatible JSON schema parameters, capability flags, handler callable, and return-shape contract. The registry MUST be the only source used by the chat agent to advertise tools to the LLM.

#### Scenario: Tools are listed for LLM call
- **WHEN** the chat agent prepares an LLM call that supports tools
- **THEN** it obtains tool schemas from the registry rather than hardcoding them in the agent loop

#### Scenario: Disabled tool omitted
- **WHEN** a tool is marked disabled by configuration
- **THEN** the registry does not include it in the schemas sent to the LLM

### Requirement: run_readonly_sql tool
The registry SHALL include a `run_readonly_sql` tool that accepts SQL and optional max_rows, delegates execution to `sql-sandbox`, and returns the sandbox structured result. The LLM-visible tool result MUST use masked rows.

#### Scenario: SQL tool returns masked result
- **WHEN** the LLM calls `run_readonly_sql`
- **THEN** the tool response sent back to the LLM contains `llm_rows` and excludes raw `ui_rows`

#### Scenario: SQL tool emits UI artifact data
- **WHEN** the SQL tool succeeds
- **THEN** the chat stream includes UI-bound result data for frontend rendering without exposing it to subsequent LLM prompts

### Requirement: describe_schema tool
The registry SHALL include a `describe_schema` tool that returns approved schema metadata for one table or a bounded group of tables. The tool MUST NOT expose provider secrets, application settings, chat message content, Alembic metadata, or blocked tables.

#### Scenario: Describe allowed table
- **WHEN** the LLM calls `describe_schema` for `doudian_comment`
- **THEN** the tool returns approved columns, descriptions, key time fields, join hints, and PII annotations for that table

#### Scenario: Describe forbidden table
- **WHEN** the LLM calls `describe_schema` for `llm_provider`
- **THEN** the tool returns a structured forbidden-table error

### Requirement: render_table tool
The registry SHALL include a `render_table` tool that converts a SQL result or provided row/column payload into a table artifact render spec for the frontend. The render spec MUST cap preview rows and include column labels, data keys, and source metadata.

#### Scenario: Table render spec created
- **WHEN** the LLM calls `render_table` with valid columns and rows
- **THEN** the tool returns a `kind="table"` render spec that the frontend can render with AntD Table

#### Scenario: Oversized table preview capped
- **WHEN** the source result contains more rows than the table preview cap
- **THEN** the render spec includes only capped preview rows and marks the artifact as capped

### Requirement: render_chart tool
The registry SHALL include a `render_chart` tool that accepts chart type, dimensions, measures, and source result reference or inline data, then returns an ECharts-compatible render spec. The tool MUST validate the output enough to prevent arbitrary script injection.

#### Scenario: Bar chart render spec created
- **WHEN** the LLM asks to render a bar chart for category/value data
- **THEN** the tool returns a chart artifact with an ECharts option JSON using only allowed option keys

#### Scenario: Invalid chart rejected
- **WHEN** the LLM provides a render spec containing script, function text, or unsupported option keys
- **THEN** the tool rejects the render request with a structured validation error

### Requirement: Tool execution observability
Each tool call SHALL be persisted as a `chat_message` with `kind="tool_call"` and each result SHALL be persisted as a separate `chat_message` with `kind="tool_result"` or a renderable artifact kind. Tool messages MUST include execution status, latency, input arguments, sanitized output, and source assistant message id when available.

#### Scenario: Tool call persisted
- **WHEN** the agent dispatches any registered tool
- **THEN** a tool-call message is persisted before the handler is executed

#### Scenario: Tool result persisted
- **WHEN** a registered tool returns or fails
- **THEN** a corresponding tool-result message is persisted with status and latency

### Requirement: Tool error feedback
Tool failures SHALL be returned to the LLM as structured errors, not Python tracebacks. The agent loop SHALL be able to continue after a tool validation error until the turn budget is exhausted.

#### Scenario: Tool validation error
- **WHEN** the LLM calls a tool with invalid arguments
- **THEN** the registry returns a structured validation error to the agent
- **AND** the agent may pass that error back to the LLM for self-correction
