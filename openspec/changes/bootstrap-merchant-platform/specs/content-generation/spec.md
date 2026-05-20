## ADDED Requirements

### Requirement: Four Content Kinds Supported
The system SHALL support generation of four content kinds: `title` (商品标题), `detail` (商品详情段落), `livestream_script` (直播话术：开场 / 讲品 / 互动 / 促单), and `short_video_script` (短视频脚本：30 / 60 / 90 秒三档时长). Each kind SHALL be selectable by the operator via the 文案工坊 page.

#### Scenario: Operator generates a livestream script
- **WHEN** the operator selects `livestream_script` for a specific goods_id, sets time-of-day = `evening`, and clicks "生成"
- **THEN** the system SHALL invoke `LLM.complete` with a prompt assembled from the goods row, recent comments (PII-scrubbed), and the livestream-script template, and SHALL display the result on screen within 15 seconds

### Requirement: Output Persisted and Editable
Every successful generation SHALL persist its `ai_generation` row id, `kind`, and `output_text`. The frontend SHALL allow the operator to edit the output and save the edited version as a new row referencing the original via a `parent_id` field.

#### Scenario: Operator edits a generated title
- **WHEN** the operator modifies generated text and clicks "保存"
- **THEN** the system SHALL persist a new `ai_generation` row with `kind=title`, `parent_id=<original id>`, and the edited `output_text`

### Requirement: Per-Kind Template Definitions
Prompt templates per kind SHALL live in `backend/dystore/content/templates/<kind>.j2` (Jinja2). Operators SHALL NOT be able to edit templates from the UI in V1+V2 (templates are code-owned). The template SHALL receive: `goods` (row dict), `recent_comments_summary` (string, PII-scrubbed), `extra_context` (operator-provided free text).

#### Scenario: Template missing for a requested kind
- **WHEN** the operator requests a kind whose template file does not exist
- **THEN** the system SHALL respond with HTTP 400 and SHALL NOT call the LLM

### Requirement: Cost Visibility per Generation
The frontend 文案工坊 page SHALL display the `tokens_in`, `tokens_out`, and `cost` of each completed generation alongside the output text.

#### Scenario: Generation completes
- **WHEN** the LLM call returns successfully
- **THEN** the frontend SHALL display the output text and the cost metrics from the `ai_generation` row
