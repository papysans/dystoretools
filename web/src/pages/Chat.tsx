import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Bubble, Sender } from "@ant-design/x";
import { Avatar, Button, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  MessageOutlined,
  PictureOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  RobotOutlined,
  SendOutlined,
  TableOutlined,
  UserOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChatMessage,
  createConversation,
  listConversations,
  listMessages,
  streamChatMessage,
} from "../api/chat";
import { listModels, listProviders } from "../api/llm";

const MODEL_SEPARATOR = ":::";

const ORDER_STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: "待付款", color: "default" },
  1: { text: "已付款", color: "blue" },
  2: { text: "已付款", color: "blue" },
  3: { text: "已发货", color: "cyan" },
  4: { text: "已完成", color: "green" },
  5: { text: "已退款", color: "red" },
  6: { text: "已关闭", color: "default" },
};

type StreamTrace = {
  id: string;
  event: string;
  label: string;
  status: "running" | "done" | "error";
};

type ToolEnvelope = {
  status?: string;
  tool?: string;
  latency_ms?: number;
  error?: string;
  result?: Record<string, any>;
};

type RenderMessage = {
  message: ChatMessage;
  companion?: string;
};

export default function Chat() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
  const [modelValue, setModelValue] = useState<string | undefined>();
  const [draft, setDraft] = useState("");
  const [trace, setTrace] = useState<StreamTrace[]>([]);

  const quickActions = [
    { key: "video", label: "短视频创作", icon: <MessageOutlined /> },
    { key: "image", label: "智能图片", icon: <PictureOutlined /> },
    { key: "analysis", label: "数据分析", icon: <BarChartOutlined /> },
    { key: "goods", label: "智能选品", icon: <DatabaseOutlined /> },
    { key: "diagnose", label: "经营诊断", icon: <QuestionCircleOutlined /> },
  ];

  const suggestionCards = [
    "上新趋势洞察",
    "近7天主要有哪些问题导致退款？有什么可改善的建议吗",
    "怎么查看异常包裹的详细物流信息？",
    "近7天的退款数据有没有异动？",
    "即将售罄的商品有多少，怎么设置库存预警？",
  ];

  const conversations = useQuery({ queryKey: ["chat-conversations"], queryFn: listConversations });
  const messages = useQuery({
    queryKey: ["chat-messages", activeId],
    queryFn: () => listMessages(activeId!),
    enabled: !!activeId,
  });
  const providers = useQuery({ queryKey: ["llm-providers"], queryFn: listProviders });
  const models = useQuery({ queryKey: ["chat-models"], queryFn: () => listModels(undefined, true) });

  const providerNameById = useMemo(() => {
    const pairs = (providers.data?.items ?? []).map((p) => [p.id, p.name] as const);
    return new Map<number, string>(pairs);
  }, [providers.data]);

  const modelOptions = useMemo(
    () =>
      (models.data?.items ?? []).map((m) => {
        const providerName = providerNameById.get(m.provider_id) ?? `Provider ${m.provider_id}`;
        const label = `${m.display_name || m.model_name} · ${providerName}`;
        return {
          value: toModelValue(m.provider_id, m.model_name),
          label,
          searchText: `${label} ${m.model_name}`,
        };
      }),
    [models.data, providerNameById],
  );

  const activeConversation = useMemo(
    () => (conversations.data?.items ?? []).find((item) => item.id === activeId) ?? null,
    [activeId, conversations.data],
  );

  useEffect(() => {
    if (!activeId && conversations.data?.items?.[0]) {
      setActiveId(conversations.data.items[0].id);
    }
  }, [activeId, conversations.data]);

  useEffect(() => {
    setLiveMessages(messages.data?.items ?? []);
    setDraft("");
    setTrace([]);
  }, [messages.data]);

  useEffect(() => {
    const conversationModel =
      activeConversation?.provider_id && activeConversation.model_name
        ? toModelValue(activeConversation.provider_id, activeConversation.model_name)
        : undefined;
    if (conversationModel && modelOptions.some((option) => option.value === conversationModel)) {
      setModelValue(conversationModel);
      return;
    }
    if (!modelValue && modelOptions[0]) {
      setModelValue(modelOptions[0].value);
    }
  }, [activeConversation, modelOptions, modelValue]);

  const ensureConversation = async () => {
    if (activeId) return activeId;
    const [provider_id, model_name] = parseModel(modelValue);
    const created = await createConversation({ title: "新对话", provider_id, model_name });
    setActiveId(created.id);
    await qc.invalidateQueries({ queryKey: ["chat-conversations"] });
    return created.id;
  };

  const createNewConversation = async () => {
    const [provider_id, model_name] = parseModel(modelValue);
    const created = await createConversation({ title: "新对话", provider_id, model_name });
    setActiveId(created.id);
    setLiveMessages([]);
    setTrace([]);
    setDraft("");
    await qc.invalidateQueries({ queryKey: ["chat-conversations"] });
  };

  const addTrace = (event: string, data?: any) => {
    const label = traceLabel(event, data);
    const status = event === "error" ? "error" : event === "done" || event === "tool_result" ? "done" : "running";
    setTrace((prev) => [...prev.slice(-5), { id: `${Date.now()}-${event}-${prev.length}`, event, label, status }]);
  };

  const send = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    setInput("");
    setStreaming(true);
    setDraft("");
    setTrace([{ id: `${Date.now()}-start`, event: "start", label: "准备分析", status: "running" }]);
    try {
      const conversationId = await ensureConversation();
      const [provider_id, model_name] = parseModel(modelValue);
      await streamChatMessage(conversationId, { content: trimmed, provider_id, model_name }, (event, data) => {
        if (event !== "message" && event !== "delta") {
          addTrace(event, data);
        }
        if (event === "delta" && data?.content) {
          setDraft((prev) => `${prev}${data.content}`);
        }
        if (data?.id) {
          setLiveMessages((prev) => {
            const next = prev.filter((m) => m.id !== data.id);
            return [...next, data].sort((a, b) => a.id - b.id);
          });
          if (data.role === "assistant" && data.kind !== "tool_call") {
            setDraft("");
          }
        }
      });
      await qc.invalidateQueries({ queryKey: ["chat-conversations"] });
      await qc.invalidateQueries({ queryKey: ["chat-messages", conversationId] });
    } catch (e: any) {
      message.error(e?.message ?? "发送失败");
      setTrace((prev) => [...prev, { id: `${Date.now()}-failed`, event: "error", label: "发送失败", status: "error" }]);
    } finally {
      setStreaming(false);
    }
  };

  const bubbleItems = useMemo(() => {
    const renderMessages = mergeArtifactNarratives(liveMessages);
    const persisted = renderMessages.map(({ message: m, companion }) => ({
      key: String(m.id),
      role: m.role,
      content: <MessageContent message={m} companion={companion} providerName={providerNameById.get(m.provider_id ?? -1)} />,
    }));
    if (draft) {
      persisted.push({
        key: "draft",
        role: "assistant",
        content: (
          <div className="chat-text">
            <ReactMarkdown skipHtml>{draft}</ReactMarkdown>
          </div>
        ),
      });
    }
    return persisted;
  }, [draft, liveMessages, providerNameById]);

  return (
    <div className="chat-page chat-page-home">
      <div className="chat-home-nav" aria-label="聊天导航">
        <button type="button" className="chat-home-nav-item">
          <HistoryOutlined />
          <span>历史对话</span>
        </button>
        <button type="button" className="chat-home-nav-item">
          <QuestionCircleOutlined />
          <span>实操指南</span>
        </button>
        <button type="button" className="chat-home-nav-item" onClick={createNewConversation}>
          <PlusOutlined />
          <span>新对话</span>
        </button>
      </div>

      <div className="chat-home-hero">
        <div className="chat-home-title">你好，我是你专属的AI助手</div>
        <div className="chat-home-actions">
          {quickActions.map((item) => (
            <button key={item.key} type="button" className="chat-home-action-chip" onClick={() => setInput(item.label)}>
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <div className="chat-home-composer-card">
          <div className="chat-home-robot" aria-hidden="true">
            <div className="chat-home-robot-bubble chat-home-robot-bubble-left" />
            <div className="chat-home-robot-main">
              <RobotOutlined />
            </div>
            <div className="chat-home-robot-bubble chat-home-robot-bubble-right" />
          </div>

          <div className="chat-home-composer-shell">
            <div className="chat-home-composer-head">
              <Select
                className="chat-model-select"
                value={modelValue}
                onChange={setModelValue}
                options={modelOptions}
                loading={models.isLoading || providers.isLoading}
                optionFilterProp="searchText"
                showSearch
                placeholder="选择模型"
              />
            </div>
            {(streaming || trace.length > 0) && <TraceStrip traces={trace} />}
            <Sender
              rootClassName="chat-home-sender"
              value={input}
              onChange={setInput}
              onSubmit={send}
              loading={streaming}
              placeholder="近7天主要有哪些问题导致退款？有什么可改善的建议吗"
              actions={() => (
                <div className="chat-home-sender-actions">
                  <Button type="text" size="small" className="chat-home-attachment-btn" icon={<PictureOutlined />} />
                  <Button type="primary" shape="circle" icon={<SendOutlined />} onClick={() => void send(input)} />
                </div>
              )}
            />
            <div className="chat-home-thinking-row">
              <button type="button" className="chat-home-thinking-chip" onClick={() => setInput("请深度思考后给我一份经营诊断建议") }>
                <RobotOutlined />
                <span>深度思考·自动</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="chat-home-suggestions">
        <div className="chat-home-suggestions-head">
          <strong>猜你想问</strong>
          <button type="button" className="chat-home-refresh">换一批</button>
        </div>
        <div className="chat-home-suggestion-grid">
          {suggestionCards.map((item) => (
            <button key={item} type="button" className="chat-home-suggestion-card" onClick={() => setInput(item)}>
              <span className="chat-home-suggestion-quote">“</span>
              <span className="chat-home-suggestion-text">{item}</span>
              <span className="chat-home-suggestion-quote chat-home-suggestion-quote-end">”</span>
            </button>
          ))}
        </div>
      </div>

      {!!liveMessages.length && (
        <section className="chat-stage chat-home-stage" aria-label="AI 对话工作区">
          <div className="chat-stage-topbar">
            <div className="chat-stage-meta">
              <div className="chat-stage-title-row">
                <RobotOutlined />
                <strong>{activeConversation?.title || "新对话"}</strong>
              </div>
              <div className="chat-stage-subrow">
                <span>{liveMessages.length} 条消息</span>
                {activeConversation?.updated_at && <span>更新于 {formatTime(activeConversation.updated_at)}</span>}
                {streaming && <span className="chat-live-dot">运行中</span>}
              </div>
            </div>
          </div>

          <div className="chat-stage-main">
            <div className="chat-thread">
              <Bubble.List
                autoScroll
                roles={{
                  user: { placement: "end", avatar: <Avatar icon={<UserOutlined />} /> },
                  assistant: { placement: "start", avatar: <Avatar icon={<RobotOutlined />} /> },
                  tool: { placement: "start", avatar: <Avatar icon={<DatabaseOutlined />} /> },
                }}
                items={bubbleItems}
              />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function MessageContent({
  message: msg,
  companion,
  providerName,
}: {
  message: ChatMessage;
  companion?: string;
  providerName?: string;
}) {
  const meta = (
    <MessageMeta
      providerName={providerName}
      modelName={msg.model_name}
      createdAt={msg.created_at}
      tokensIn={msg.tokens_in}
      tokensOut={msg.tokens_out}
      latencyMs={msg.latency_ms}
    />
  );

  if (msg.kind === "tool_call") {
    return (
      <div className="chat-artifact chat-artifact-tool">
        <ArtifactHeader icon={<CodeOutlined />} title="工具调用" status={msg.status} />
        <div className="chat-tool-list">
          {Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0 ? (
            msg.tool_calls.map((call: any, index: number) => (
              <details key={`${call.id ?? call.name ?? index}`} className="chat-tool-call">
                <summary>{call.name || "unknown_tool"}</summary>
                <pre>{JSON.stringify(call.arguments ?? {}, null, 2)}</pre>
              </details>
            ))
          ) : (
            <span className="chat-muted">正在准备工具参数</span>
          )}
        </div>
        {meta}
      </div>
    );
  }

  if (msg.kind === "tool_result") {
    return <ToolResult message={msg} meta={meta} />;
  }

  if (msg.kind === "table" || msg.render_spec?.kind === "table") {
    return <TableArtifact message={msg} companion={companion} meta={meta} />;
  }

  if (msg.kind === "chart" || msg.render_spec?.kind === "chart") {
    return <ChartArtifact message={msg} companion={companion} meta={meta} />;
  }

  return (
    <div className="chat-text">
      <ReactMarkdown skipHtml>{msg.content ?? ""}</ReactMarkdown>
      {meta}
    </div>
  );
}

function ToolResult({ message: msg, meta }: { message: ChatMessage; meta: ReactNode }) {
  const envelope = (msg.tool_results ?? safeJson(msg.content)) as ToolEnvelope;
  const result = envelope?.result ?? {};
  const rows = Array.isArray(result.ui_rows) ? result.ui_rows : Array.isArray(result.llm_rows) ? result.llm_rows : [];
  const columns = Array.isArray(result.columns) ? result.columns : inferColumns(rows);
  const normalizedSql = result.normalized_sql || msg.source_sql;
  const hasRows = rows.length > 0;
  const failed = envelope?.status === "error" || result.status === "error";
  const orderStatus = shouldNormalizeOrderStatus(msg, columns, rows, normalizedSql);

  return (
    <div className="chat-artifact">
      <ArtifactHeader
        icon={failed ? <WarningOutlined /> : <DatabaseOutlined />}
        title={envelope?.tool || "SQL 沙箱"}
        status={failed ? "failed" : msg.status}
        extra={typeof envelope?.latency_ms === "number" ? `${envelope.latency_ms}ms` : undefined}
      />
      {normalizedSql && <SqlBlock sql={normalizedSql} />}
      {failed && <div className="chat-error">{envelope.error || result.error || "工具执行失败"}</div>}
      <div className="chat-result-metrics">
        <Metric label="Rows" value={formatNumber(result.ui_row_count ?? result.row_count ?? rows.length)} />
        <Metric label="Columns" value={formatNumber(columns.length)} />
        <Metric label="Capped" value={result.capped ? "Yes" : "No"} />
      </div>
      {hasRows && (
        <details className="chat-tool-call chat-data-preview-details">
          <summary>查看原始结果预览 ({formatNumber(rows.length)} 行)</summary>
          <DataPreview rows={rows} columns={columns} orderStatus={orderStatus} />
        </details>
      )}
      {!hasRows && !failed && <div className="chat-muted">查询执行成功，未返回数据行。</div>}
      {meta}
    </div>
  );
}

function TableArtifact({ message: msg, companion, meta }: { message: ChatMessage; companion?: string; meta: ReactNode }) {
  const spec = msg.render_spec ?? {};
  const rows = Array.isArray(spec.rows) ? spec.rows : [];
  const orderStatus = shouldNormalizeOrderStatus(msg, spec.columns, rows);
  const columns = normalizeColumns(spec.columns, rows, { orderStatus });
  return (
    <div className="chat-artifact">
      <ArtifactHeader
        icon={<TableOutlined />}
        title={spec.title || "数据表"}
        status={msg.status}
        extra={spec.capped ? "已截断" : `${rows.length} 行`}
      />
      <DataPreview rows={rows} columns={columnKeys(columns)} orderStatus={orderStatus} />
      <ArtifactNarrative content={companion} normalizeOrderStatus={orderStatus} />
      {meta}
    </div>
  );
}

function ChartArtifact({ message: msg, companion, meta }: { message: ChatMessage; companion?: string; meta: ReactNode }) {
  const option = decorateChartOption(msg.render_spec?.option ?? {});
  const orderStatus = shouldNormalizeOrderStatus(msg);
  return (
    <div className="chat-artifact">
      <ArtifactHeader icon={<BarChartOutlined />} title={msg.render_spec?.title || "图表"} status={msg.status} />
      <div className="chat-chart-frame">
        <ReactECharts option={option} style={{ height: 320, width: "100%" }} notMerge lazyUpdate />
      </div>
      <ArtifactNarrative content={companion} normalizeOrderStatus={orderStatus} />
      {meta}
    </div>
  );
}

function ArtifactNarrative({ content, normalizeOrderStatus = false }: { content?: string; normalizeOrderStatus?: boolean }) {
  const cleaned = cleanArtifactNarrative(content, normalizeOrderStatus);
  if (!cleaned) return null;
  return (
    <div className="chat-artifact-summary">
      <ReactMarkdown skipHtml>{cleaned}</ReactMarkdown>
    </div>
  );
}

function ArtifactHeader({
  icon,
  title,
  status,
  extra,
}: {
  icon: ReactNode;
  title: string;
  status?: string;
  extra?: string;
}) {
  const ok = !status || status === "ok" || status === "done";
  return (
    <div className="chat-artifact-header">
      <div className="chat-artifact-title">
        {icon}
        <strong>{title}</strong>
      </div>
      <Space size={6}>
        {extra && <span className="chat-artifact-extra">{extra}</span>}
        <Tag color={ok ? "green" : "red"} icon={ok ? <CheckCircleOutlined /> : <WarningOutlined />}>
          {ok ? "OK" : status}
        </Tag>
      </Space>
    </div>
  );
}

function DataPreview({ rows, columns, orderStatus = false }: { rows: Record<string, any>[]; columns: string[]; orderStatus?: boolean }) {
  const normalizedRows = normalizeRows(rows, columns);
  return (
    <div className="chat-table-frame">
      <Table
        size="small"
        pagination={normalizedRows.length > 12 ? { pageSize: 12, size: "small" } : false}
        rowKey={(_, index) => String(index)}
        dataSource={normalizedRows}
        columns={normalizeColumns(columns, normalizedRows, { orderStatus })}
        scroll={{ x: true }}
      />
    </div>
  );
}

function SqlBlock({ sql }: { sql: string }) {
  return (
    <div className="chat-sql-block">
      <SyntaxHighlighter
        language="sql"
        PreTag="div"
        customStyle={{ margin: 0, borderRadius: 8, fontSize: 12, background: "transparent" }}
      >
        {sql}
      </SyntaxHighlighter>
    </div>
  );
}

function MessageMeta({
  providerName,
  modelName,
  createdAt,
  tokensIn,
  tokensOut,
  latencyMs,
}: {
  providerName?: string;
  modelName?: string | null;
  createdAt?: string | null;
  tokensIn?: number;
  tokensOut?: number;
  latencyMs?: number | null;
}) {
  const parts = [
    providerName || undefined,
    modelName || undefined,
    tokensIn || tokensOut ? `${formatNumber((tokensIn ?? 0) + (tokensOut ?? 0))} token` : undefined,
    typeof latencyMs === "number" ? `${latencyMs}ms` : undefined,
    createdAt ? formatTime(createdAt) : undefined,
  ].filter(Boolean);
  if (!parts.length) return null;
  return <div className="chat-message-meta">{parts.join(" · ")}</div>;
}

function TraceStrip({ traces }: { traces: StreamTrace[] }) {
  if (!traces.length) return null;
  return (
    <div className="chat-trace-strip" aria-label="运行状态">
      {traces.map((item) => (
        <span key={item.id} className={`chat-trace-item chat-trace-${item.status}`}>
          {item.status === "running" ? <ClockCircleOutlined /> : item.status === "error" ? <WarningOutlined /> : <CheckCircleOutlined />}
          {item.label}
        </span>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="chat-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function mergeArtifactNarratives(messages: ChatMessage[]): RenderMessage[] {
  const out: RenderMessage[] = [];
  for (let index = 0; index < messages.length; index += 1) {
    const current = messages[index];
    const previous = out[out.length - 1];
    if (previous && isRenderableArtifact(previous.message) && shouldMergeNarrative(current)) {
      previous.companion = [previous.companion, current.content].filter(Boolean).join("\n\n") || undefined;
      continue;
    }
    out.push({ message: current });
  }
  return out;
}

function isRenderableArtifact(message: ChatMessage) {
  return message.kind === "table" || message.kind === "chart" || message.render_spec?.kind === "table" || message.render_spec?.kind === "chart";
}

function shouldMergeNarrative(message: ChatMessage) {
  if (message.role !== "assistant" || message.kind === "tool_call" || !message.content) return false;
  return hasMarkdownTable(message.content) || hasSummaryCue(message.content);
}

function hasMarkdownTable(content: string) {
  return /\n?\s*\|.+\|\s*\n\s*\|[\s:|-]+\|/.test(content);
}

function hasSummaryCue(content: string) {
  return /(小结|总结|建议|结论|概览|洞察|说明|情况如下|查询完成|查询结果)/.test(content);
}

function cleanArtifactNarrative(content?: string, normalizeOrderStatus = false) {
  if (!content) return "";
  const withoutTables = stripMarkdownTables(content);
  const normalized = normalizeOrderStatus ? normalizeOrderStatusNarrative(withoutTables) : withoutTables;
  return normalized.replace(/\n{3,}/g, "\n\n").trim();
}

function stripMarkdownTables(content: string) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const kept: string[] = [];
  for (let index = 0; index < lines.length; index += 1) {
    const current = lines[index];
    const next = lines[index + 1];
    if (isMarkdownTableLine(current) && isMarkdownSeparatorLine(next)) {
      index += 2;
      while (index < lines.length && isMarkdownTableLine(lines[index])) {
        index += 1;
      }
      index -= 1;
      continue;
    }
    kept.push(current);
  }
  return kept.join("\n");
}

function isMarkdownTableLine(line?: string) {
  return Boolean(line && /^\s*\|.*\|\s*$/.test(line));
}

function isMarkdownSeparatorLine(line?: string) {
  return Boolean(line && /^\s*\|[\s:|-]+\|\s*$/.test(line));
}

function normalizeOrderStatusNarrative(content: string) {
  return content
    .replace(/\*\*状态码\s*2\*\*(?:（[^）]*）)?/g, "**已付款**")
    .replace(/\*\*状态码\s*4\*\*(?:（[^）]*）)?/g, "**已完成**")
    .replace(/状态码\s*2(?:（[^）]*）)?/g, "已付款")
    .replace(/状态码\s*4(?:（[^）]*）)?/g, "已完成")
    .replace(/status\s*[=:：]\s*2/gi, "已付款")
    .replace(/status\s*[=:：]\s*4/gi, "已完成");
}

function shouldNormalizeOrderStatus(
  message: ChatMessage,
  columns?: any[],
  rows?: Record<string, any>[],
  sql?: string | null,
) {
  const spec = message.render_spec ?? {};
  const candidateSql = [sql, message.source_sql, spec.source_sql, spec.sql].filter(Boolean).join(" ").toLowerCase();
  if (candidateSql.includes("doudian_order")) return true;

  const names = Array.isArray(columns) && columns.length ? columns : rows?.length ? inferColumns(rows) : [];
  const normalizedNames = names.map((column: any) => String(columnKey(column)));
  return normalizedNames.includes("order_sn") && normalizedNames.includes("status");
}

function normalizeColumns(
  columns: any[] | undefined,
  rows: Record<string, any>[],
  options: { orderStatus?: boolean } = {},
): ColumnsType<Record<string, any>> {
  const names = Array.isArray(columns) && columns.length ? columns : inferColumns(rows);
  return names.map((column: any) => {
    const key = columnKey(column);
    const title = columnTitle(column, key);
    return {
      title: formatColumnTitle(String(title), String(key)),
      dataIndex: key,
      key,
      ellipsis: true,
      render: (value: any) => formatCell(value, String(key), options),
    };
  });
}

function columnKey(column: any) {
  return typeof column === "string" ? column : column?.dataIndex || column?.prop || column?.key || column?.title || column?.label;
}

function columnTitle(column: any, key: any) {
  return typeof column === "string" ? column : column?.title || column?.label || key;
}

function columnKeys(columns: ColumnsType<Record<string, any>>): string[] {
  return columns.map((column) => {
    if ("dataIndex" in column) {
      const value = column.dataIndex;
      return Array.isArray(value) ? value.join(".") : String(value ?? column.key ?? column.title);
    }
    return String(column.key ?? column.title);
  });
}

function normalizeRows(rows: any[], columns: string[]): Record<string, any>[] {
  return rows.map((row) => {
    if (Array.isArray(row)) {
      return columns.reduce<Record<string, any>>((out, column, index) => {
        out[column] = row[index];
        return out;
      }, {});
    }
    return row && typeof row === "object" ? row : { value: row };
  });
}

function inferColumns(rows: Record<string, any>[]): string[] {
  const first = rows[0];
  return first ? Object.keys(first) : [];
}

function formatColumnTitle(title: string, key: string) {
  if (key === "status") return "状态";
  if (key === "order_sn") return "订单编号";
  if (key === "goods_name") return "商品名称";
  if (key === "order_amount") return "金额(元)";
  return title;
}

function formatCell(value: any, key?: string, options: { orderStatus?: boolean } = {}) {
  if (value == null) return <span className="chat-muted">-</span>;
  if (typeof value === "object") return <code>{JSON.stringify(value)}</code>;
  if (key === "status" && options.orderStatus) {
    const status = ORDER_STATUS_MAP[Number(value)];
    return status ? <Tag color={status.color}>{status.text}</Tag> : String(value);
  }
  if (key === "order_amount" && value !== "") {
    const amount = Number(value);
    if (Number.isFinite(amount)) {
      return <span className="chat-money">¥{amount.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>;
    }
  }
  return String(value);
}

function decorateChartOption(option: Record<string, any>) {
  return {
    tooltip: { trigger: "axis", ...(option.tooltip ?? {}) },
    grid: { top: 36, right: 20, bottom: 36, left: 48, containLabel: true, ...(option.grid ?? {}) },
    ...option,
  };
}

function traceLabel(event: string, data?: any) {
  if (event === "tool_call") {
    const tools = Array.isArray(data?.tool_calls) ? data.tool_calls.map((call: any) => call.name).filter(Boolean) : [];
    return tools.length ? `调用 ${tools.join(", ")}` : "调用工具";
  }
  if (event === "tool_result") return data?.tool_name ? `${data.tool_name} 完成` : "工具完成";
  if (event === "done") return "回答完成";
  if (event === "error") return "执行异常";
  return event;
}

function safeJson(content?: string | null) {
  if (!content) return null;
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

function toModelValue(providerId: number, modelName: string) {
  return `${providerId}${MODEL_SEPARATOR}${modelName}`;
}

function parseModel(value?: string): [number | undefined, string | undefined] {
  if (!value) return [undefined, undefined];
  const index = value.indexOf(MODEL_SEPARATOR);
  if (index < 0) return [undefined, value];
  return [Number(value.slice(0, index)), value.slice(index + MODEL_SEPARATOR.length)];
}

function formatNumber(value?: number | null) {
  return new Intl.NumberFormat("zh-CN").format(Number(value ?? 0));
}

function formatTime(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
