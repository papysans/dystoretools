## ADDED Requirements

### Requirement: Readonly SQL execution
The system SHALL expose a backend-only `run_readonly_sql(sql, max_rows)` function that executes LLM-authored SQL using a dedicated MySQL readonly connection configured by `MYSQL_CHAT_READONLY_USER` and `MYSQL_CHAT_READONLY_PASSWORD`. The function MUST NOT use the normal application write-capable database session.

#### Scenario: Valid readonly query
- **WHEN** `run_readonly_sql("SELECT goods_id, title FROM doudian_goods LIMIT 20", max_rows=20)` is called
- **THEN** the query executes through the chat readonly connection
- **AND** the result contains no more than 20 rows

#### Scenario: Write-capable session not used
- **WHEN** the sandbox executes any accepted SQL query
- **THEN** the connection identity is the configured chat readonly user rather than the application database user

### Requirement: SQL AST safety gate
The system SHALL parse SQL with `sqlglot` and reject any query that is not exactly one `SELECT` statement. The gate MUST reject DML, DDL, transaction/session statements, multi-statements, comments that hide additional statements, unparsable SQL, and queries without a parsable `FROM`.

#### Scenario: DML rejected
- **WHEN** the LLM submits `DELETE FROM doudian_order`
- **THEN** the sandbox rejects the SQL before execution and returns a structured safety error

#### Scenario: Multiple statements rejected
- **WHEN** the LLM submits `SELECT * FROM doudian_goods; DROP TABLE doudian_goods`
- **THEN** the sandbox rejects the SQL before execution

#### Scenario: Unparsable SQL rejected
- **WHEN** the LLM submits malformed SQL
- **THEN** the sandbox rejects the SQL before execution with a parse error category

### Requirement: Table access policy
The system SHALL enforce a table access policy for chat SQL. Business data tables containing scraped merchant facts MAY be queried. Secret/configuration/control tables including `llm_provider`, `llm_model`, `chat_*`, `session_event`, settings tables, Alembic tables, and `information_schema` MUST be rejected unless explicitly allowed in a future spec.

#### Scenario: Business table allowed
- **WHEN** the LLM submits a valid `SELECT` against `doudian_comment`
- **THEN** the sandbox allows the query if all other safety checks pass

#### Scenario: Provider table rejected
- **WHEN** the LLM submits `SELECT * FROM llm_provider`
- **THEN** the sandbox rejects the query before execution

#### Scenario: Information schema rejected
- **WHEN** the LLM submits `SELECT * FROM information_schema.tables`
- **THEN** the sandbox rejects the query before execution

### Requirement: Limit and timeout enforcement
The system SHALL cap SQL result size and runtime. If an accepted query has no `LIMIT`, the sandbox MUST inject one at AST level. If the query has a `LIMIT` greater than the configured cap, the sandbox MUST reduce it. The default row cap MUST be 1000 and each statement MUST have a 30-second execution timeout.

#### Scenario: Missing limit is injected
- **WHEN** the LLM submits `SELECT * FROM doudian_comment`
- **THEN** the SQL executed by MySQL includes a limit no greater than the sandbox cap

#### Scenario: Excessive limit is reduced
- **WHEN** the LLM submits `SELECT * FROM doudian_comment LIMIT 100000`
- **THEN** the SQL executed by MySQL limits rows to the sandbox cap

#### Scenario: Timeout stops long query
- **WHEN** an accepted query exceeds the configured execution timeout
- **THEN** the sandbox aborts it and returns a timeout error without crashing the chat service

### Requirement: Dual-channel PII masking
The system SHALL return SQL results in two channels: `llm_rows` with PII masked and `ui_rows` with original values. Only `llm_rows` MAY be sent back to the LLM or stored in LLM-bound prompt/accounting content. PII columns MUST be declared in a registry and include customer phone, address, name/nickname, and order identifiers where present.

#### Scenario: Phone number masked for LLM
- **WHEN** SQL results include a receiver phone value `13900000001`
- **THEN** `llm_rows` contains a masked placeholder or redacted value
- **AND** `ui_rows` contains the original value for local rendering

#### Scenario: Address masked for LLM
- **WHEN** SQL results include a street address
- **THEN** `llm_rows` does not contain the full raw address

#### Scenario: LLM-bound persistence excludes raw PII
- **WHEN** a tool result is persisted for agent context
- **THEN** the LLM-bound portion of `tool_results_json` contains masked rows only

### Requirement: Structured SQL result contract
The sandbox SHALL return a structured result containing status, normalized_sql, columns, row_count, capped flag, execution_ms, `llm_rows`, `ui_rows`, and error details when rejected or failed.

#### Scenario: Successful result shape
- **WHEN** a valid query succeeds
- **THEN** the result includes normalized SQL, column metadata, row count, execution time, and both result channels

#### Scenario: Rejected result shape
- **WHEN** a query is rejected by policy
- **THEN** the result includes `status="rejected"` and an error code suitable for the agent to explain or repair the query

### Requirement: Sandbox test coverage
The system SHALL include automated tests for SQL sandbox acceptance, rejection, limit injection, timeout handling where feasible, table policy, and PII masking.

#### Scenario: Safety tests run
- **WHEN** backend tests are executed
- **THEN** representative DML, DDL, multi-statement, forbidden table, missing limit, and PII cases are covered
