## ADDED Requirements

### Requirement: React 18 + Vite + TypeScript + Ant Design Pro SPA
The frontend SHALL be built with React 18, Vite, TypeScript (strict mode), and Ant Design Pro as the UI scaffold. The system MUST NOT introduce Recharts, Material-UI, Chakra, or other competing UI/chart libraries in V1+V2.

#### Scenario: Project bootstrap
- **WHEN** the developer runs `pnpm install` and `pnpm dev` from `web/`
- **THEN** the system SHALL start a Vite dev server on port 5173 with HMR

### Requirement: Dashboard Page Inventory
The SPA SHALL provide exactly the following pages in V1+V2: `总览 (/)`, `订单 (/orders)`, `商品 (/goods)`, `库存 (/stock)`, `评论 (/comments)`, `售后 (/aftersale)`, `用户 (/member)`, `罗盘 (/compass)`, `文案工坊 (/content-workshop)`, `任务 (/tasks)`, `告警 (/alerts)`. Pages MUST NOT be added or removed without an accompanying spec change.

#### Scenario: Operator navigates to all pages
- **WHEN** the user clicks each of the 11 sidebar entries
- **THEN** each page SHALL load without runtime errors and SHALL display at least its primary data section (filled, loading, or empty-state)

### Requirement: Four WebSocket Channels
The frontend SHALL maintain four WebSocket connections to: `/ws/dashboard` (KPI deltas), `/ws/tasks` (scrape lifecycle), `/ws/alerts` (alert fan-out), `/ws/auth-required` (session expiry / risk verification). Lost connections SHALL reconnect with exponential backoff capped at 30 seconds.

#### Scenario: Backend restarts
- **WHEN** the FastAPI process restarts while the frontend is open
- **THEN** the frontend SHALL detect each disconnected channel and reconnect within 30 seconds without page reload

### Requirement: Server-State via React Query, Local-State via Zustand
The frontend SHALL use TanStack Query (React Query) for all server-cache state and Zustand for local UI state. The system MUST NOT use Redux, MobX, or hand-rolled context providers for server cache.

#### Scenario: Two tabs show order list
- **WHEN** the operator opens two browser tabs showing the orders page
- **THEN** the order-list query SHALL be cached once via React Query and SHALL re-fetch on the configured stale window (default 60 seconds) rather than per-tab

### Requirement: Charts via ECharts
All charts SHALL be rendered using ECharts via `echarts-for-react`. The system MUST NOT load Recharts, Chart.js, or D3 directly for charting.

#### Scenario: KPI tile renders a line chart
- **WHEN** the 总览 page mounts and a member-daily series query resolves
- **THEN** the chart SHALL render via ECharts with the configured theme `chalk`

### Requirement: Auth-Required Modal Surfaces Risk Verification
When the frontend receives a `risk_verification_required` or `session_expired` message on `/ws/auth-required`, it SHALL surface a modal explaining the situation, with a single primary action "去浏览器完成登录" that POSTs `/api/v1/auth/open-login-window`. The modal SHALL block other interaction until the backend reports `session_ready`.

#### Scenario: Session expires while operator is browsing
- **WHEN** the backend publishes `session_expired` on `/ws/auth-required`
- **THEN** the frontend SHALL render a blocking modal within 1 second, and POSTing the open-login-window action SHALL trigger the backend to launch a visible Chromium window
