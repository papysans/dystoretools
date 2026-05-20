import { useEffect, useMemo, useState } from "react";
import { PageContainer } from "@ant-design/pro-components";
import { Bubble, Conversations, Sender } from "@ant-design/x";
import { Avatar, Button, Empty, Select, Space, Table, Tag, message } from "antd";
import { MessageOutlined, PlusOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChatMessage, createConversation, listConversations, listMessages, streamChatMessage } from "../api/chat";
import { listModels } from "../api/llm";
import { Card } from "../components/Card";

export default function Chat() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
  const [modelValue, setModelValue] = useState<string | undefined>();

  const conversations = useQuery({ queryKey: ["chat-conversations"], queryFn: listConversations });
  const messages = useQuery({
    queryKey: ["chat-messages", activeId],
    queryFn: () => listMessages(activeId!),
    enabled: !!activeId,
  });
  const models = useQuery({ queryKey: ["chat-models"], queryFn: () => listModels(undefined, true) });

  useEffect(() => {
    if (!activeId && conversations.data?.items?.[0]) setActiveId(conversations.data.items[0].id);
  }, [activeId, conversations.data]);

  useEffect(() => {
    setLiveMessages(messages.data?.items ?? []);
  }, [messages.data]);

  const modelOptions = useMemo(
    () =>
      (models.data?.items ?? []).map((m) => ({
        value: `${m.provider_id}:${m.model_name}`,
        label: `${m.display_name || m.model_name} · Provider ${m.provider_id}`,
      })),
    [models.data],
  );

  useEffect(() => {
    if (!modelValue && modelOptions[0]) setModelValue(modelOptions[0].value);
  }, [modelOptions, modelValue]);

  const ensureConversation = async () => {
    if (activeId) return activeId;
    const [provider_id, model_name] = parseModel(modelValue);
    const created = await createConversation({ title: "新对话", provider_id, model_name });
    setActiveId(created.id);
    qc.invalidateQueries({ queryKey: ["chat-conversations"] });
    return created.id;
  };

  const send = async (content: string) => {
    if (!content.trim()) return;
    setInput("");
    setStreaming(true);
    try {
      const conversationId = await ensureConversation();
      const [provider_id, model_name] = parseModel(modelValue);
      await streamChatMessage(conversationId, { content, provider_id, model_name }, (_event, data) => {
        if (data?.id) {
          setLiveMessages((prev) => {
            const next = prev.filter((m) => m.id !== data.id);
            return [...next, data].sort((a, b) => a.id - b.id);
          });
        }
      });
      qc.invalidateQueries({ queryKey: ["chat-conversations"] });
      qc.invalidateQueries({ queryKey: ["chat-messages", conversationId] });
    } catch (e: any) {
      message.error(e?.message ?? "发送失败");
    } finally {
      setStreaming(false);
    }
  };

  return (
    <PageContainer header={{ title: "AI 助手", subTitle: "对话式查询 · SQL 沙箱 · 图表分析" }}>
      <div className="chat-shell">
        <Card padding={12} className="chat-sidebar">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            style={{ marginBottom: 12 }}
            onClick={async () => {
              const [provider_id, model_name] = parseModel(modelValue);
              const c = await createConversation({ title: "新对话", provider_id, model_name });
              setActiveId(c.id);
              qc.invalidateQueries({ queryKey: ["chat-conversations"] });
            }}
          >
            新对话
          </Button>
          <Conversations
            activeKey={activeId ? String(activeId) : undefined}
            onActiveChange={(key) => setActiveId(Number(key))}
            items={(conversations.data?.items ?? []).map((c) => ({
              key: String(c.id),
              label: c.title || c.last_message_preview || `会话 ${c.id}`,
              icon: <MessageOutlined />,
            }))}
          />
        </Card>

        <div className="chat-main">
          <div className="chat-toolbar">
            <Space>
              <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>模型</span>
              <Select
                value={modelValue}
                onChange={setModelValue}
                options={modelOptions}
                style={{ width: 260 }}
                placeholder="选择模型"
              />
            </Space>
          </div>

          <Card className="chat-messages" padding={16}>
            {liveMessages.length === 0 ? (
              <Empty description="问一个运营问题，例如：上周差评里物流问题占比是多少？" />
            ) : (
              <Bubble.List
                autoScroll
                roles={{
                  user: { placement: "end", avatar: <Avatar icon={<UserOutlined />} /> },
                  assistant: { placement: "start", avatar: <Avatar icon={<RobotOutlined />} /> },
                  tool: { placement: "start", avatar: <Avatar icon={<MessageOutlined />} /> },
                }}
                items={liveMessages.map((m) => ({
                  key: String(m.id),
                  role: m.role,
                  content: <MessageContent message={m} />,
                  loading: streaming && m.id === liveMessages[liveMessages.length - 1]?.id,
                }))}
              />
            )}
          </Card>

          <Sender
            value={input}
            onChange={setInput}
            onSubmit={send}
            loading={streaming}
            placeholder="输入要分析的问题..."
          />
        </div>
      </div>
    </PageContainer>
  );
}

function MessageContent({ message: msg }: { message: ChatMessage }) {
  if (msg.kind === "tool_call") {
    return <Tag color="blue">调用工具</Tag>;
  }
  if (msg.kind === "tool_result") {
    const result = msg.tool_results as any;
    const sql = result?.result?.normalized_sql;
    return (
      <div>
        {sql && (
          <SyntaxHighlighter language="sql" PreTag="div" customStyle={{ borderRadius: 8, fontSize: 12 }}>
            {sql}
          </SyntaxHighlighter>
        )}
        <pre className="chat-tool-json">{JSON.stringify(msg.tool_results ?? msg.content, null, 2)}</pre>
      </div>
    );
  }
  if (msg.kind === "table" || msg.render_spec?.kind === "table") {
    const spec = msg.render_spec ?? {};
    return (
      <Table
        size="small"
        pagination={false}
        dataSource={spec.rows ?? []}
        columns={(spec.columns ?? []).map((c: any) => ({ title: c.title ?? c, dataIndex: c.dataIndex ?? c }))}
      />
    );
  }
  if (msg.kind === "chart" || msg.render_spec?.kind === "chart") {
    return <ReactECharts option={msg.render_spec?.option ?? {}} style={{ height: 320, width: "100%" }} />;
  }
  return (
    <div className="chat-text">
      <ReactMarkdown skipHtml>{msg.content ?? ""}</ReactMarkdown>
    </div>
  );
}

function parseModel(value?: string): [number | undefined, string | undefined] {
  if (!value) return [undefined, undefined];
  const [provider, model] = value.split(":");
  return [Number(provider), model];
}
