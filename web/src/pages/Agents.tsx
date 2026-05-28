import { useMemo, useState } from "react";
import { PageContainer, ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { Button, Card, Drawer, Empty, Form, Input, Modal, Select, Space, Switch, Tabs, Tag, Typography, message } from "antd";
import { PlayCircleOutlined, PlusOutlined, RobotOutlined, ScheduleOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AgentRun,
  AgentSchedule,
  UserAgent,
  createAgent,
  createSchedule,
  deleteAgent,
  deleteSchedule,
  listAgentRuns,
  listAgents,
  listSchedules,
  runAgent,
  updateAgent,
  updateSchedule,
} from "../api/agents";
import { listModels, listProviders } from "../api/llm";

const DEFAULT_PROMPT = "你是一个用户自定义的抖店运营智能体。请按用户给定目标执行分析，必要时使用可用工具读取本地数据，输出简洁、可执行的中文结论。";

const statusTag = (status: string) => {
  if (status === "done") return <Tag color="green">完成</Tag>;
  if (status === "running") return <Tag color="blue">运行中</Tag>;
  if (status === "queued") return <Tag color="gold">排队中</Tag>;
  if (status === "failed") return <Tag color="red">失败</Tag>;
  return <Tag>{status}</Tag>;
};

export default function Agents() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [runOpen, setRunOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<UserAgent | null>(null);
  const [editingSchedule, setEditingSchedule] = useState<AgentSchedule | null>(null);
  const [agentForm] = Form.useForm();
  const [scheduleForm] = Form.useForm();
  const [runForm] = Form.useForm();

  const agents = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const schedules = useQuery({ queryKey: ["agent-schedules", activeId], queryFn: () => listSchedules(activeId ?? undefined) });
  const runs = useQuery({ queryKey: ["agent-runs", activeId], queryFn: () => listAgentRuns(activeId ?? undefined), refetchInterval: 5000 });
  const providers = useQuery({ queryKey: ["llm-providers"], queryFn: listProviders });
  const models = useQuery({ queryKey: ["chat-models"], queryFn: () => listModels(undefined, true) });

  const activeAgent = useMemo(() => (agents.data?.items ?? []).find((item) => item.id === activeId) ?? null, [activeId, agents.data]);
  const providerNameById = useMemo(() => new Map((providers.data?.items ?? []).map((p) => [p.id, p.name] as const)), [providers.data]);
  const modelOptions = useMemo(
    () =>
      (models.data?.items ?? []).map((m) => ({
        value: `${m.provider_id}:::${m.model_name}`,
        label: `${m.display_name || m.model_name} · ${providerNameById.get(m.provider_id) ?? m.provider_id}`,
      })),
    [models.data, providerNameById],
  );

  const refreshAll = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["agents"] }),
      qc.invalidateQueries({ queryKey: ["agent-schedules"] }),
      qc.invalidateQueries({ queryKey: ["agent-runs"] }),
    ]);
  };

  const openCreateAgent = () => {
    setEditingAgent(null);
    agentForm.setFieldsValue({ enabled: true, system_prompt: DEFAULT_PROMPT });
    setAgentOpen(true);
  };

  const openEditAgent = (row: UserAgent) => {
    setEditingAgent(row);
    agentForm.setFieldsValue({
      ...row,
      model_value: row.provider_id && row.model_name ? `${row.provider_id}:::${row.model_name}` : undefined,
    });
    setAgentOpen(true);
  };

  const saveAgent = async () => {
    const values = await agentForm.validateFields();
    const [providerRaw, modelName] = String(values.model_value ?? "").split(":::");
    const body = {
      name: values.name,
      description: values.description,
      system_prompt: values.system_prompt,
      provider_id: providerRaw ? Number(providerRaw) : null,
      model_name: modelName || null,
      enabled: values.enabled ?? true,
      tools: [],
    };
    if (editingAgent) {
      await updateAgent(editingAgent.id, body);
      message.success("智能体已更新");
    } else {
      const created = await createAgent(body);
      setActiveId(created.id);
      message.success("智能体已创建");
    }
    setAgentOpen(false);
    await refreshAll();
  };

  const openCreateSchedule = () => {
    if (!activeAgent) {
      message.warning("请先选择一个智能体");
      return;
    }
    setEditingSchedule(null);
    scheduleForm.setFieldsValue({ agent_id: activeAgent.id, timezone: "Asia/Shanghai", enabled: true, cron: "0 9 * * *" });
    setScheduleOpen(true);
  };

  const openEditSchedule = (row: AgentSchedule) => {
    setEditingSchedule(row);
    scheduleForm.setFieldsValue(row);
    setScheduleOpen(true);
  };

  const saveSchedule = async () => {
    const values = await scheduleForm.validateFields();
    if (editingSchedule) {
      await updateSchedule(editingSchedule.id, values);
      message.success("定时任务已更新");
    } else {
      await createSchedule(values);
      message.success("定时任务已创建");
    }
    setScheduleOpen(false);
    await refreshAll();
  };

  const submitRun = async () => {
    if (!activeAgent) return;
    const values = await runForm.validateFields();
    await runAgent(activeAgent.id, values.prompt);
    setRunOpen(false);
    runForm.resetFields();
    message.success("已派发智能体任务");
    await qc.invalidateQueries({ queryKey: ["agent-runs"] });
  };

  const runColumns: ProColumns<AgentRun>[] = [
    { title: "ID", dataIndex: "id", width: 72 },
    { title: "触发", dataIndex: "trigger_kind", width: 92, render: (v) => <Tag>{String(v) === "schedule" ? "定时" : "手动"}</Tag> },
    { title: "状态", dataIndex: "status", width: 100, render: (v) => statusTag(String(v)) },
    { title: "任务", dataIndex: "prompt", ellipsis: true },
    { title: "结果", dataIndex: "result_text", ellipsis: true },
    { title: "错误", dataIndex: "error_msg", ellipsis: true },
    { title: "开始", dataIndex: "started_at", valueType: "dateTime", width: 170 },
    { title: "结束", dataIndex: "finished_at", valueType: "dateTime", width: 170 },
  ];

  return (
    <PageContainer header={{ title: "自定义智能体", subTitle: "创建可复用 AI 角色，并按 Cron 定时自动执行任务" }}>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <Card
          title="智能体"
          extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreateAgent}>新建</Button>}
          styles={{ body: { padding: 8 } }}
        >
          {(agents.data?.items ?? []).length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无智能体" />
          ) : (
            <Space direction="vertical" style={{ width: "100%" }}>
              {(agents.data?.items ?? []).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveId(item.id)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    border: activeId === item.id ? "1px solid var(--accent)" : "1px solid var(--border)",
                    borderRadius: 12,
                    padding: 12,
                    background: activeId === item.id ? "rgba(0,113,227,0.08)" : "var(--bg-elevated)",
                    cursor: "pointer",
                  }}
                >
                  <Space align="start">
                    <RobotOutlined style={{ color: "var(--accent)", marginTop: 4 }} />
                    <div>
                      <Typography.Text strong>{item.name}</Typography.Text>
                      <div style={{ color: "var(--text-tertiary)", fontSize: 12 }}>{item.description || "无描述"}</div>
                      <Tag color={item.enabled ? "green" : "default"}>{item.enabled ? "启用" : "停用"}</Tag>
                    </div>
                  </Space>
                </button>
              ))}
            </Space>
          )}
        </Card>

        <Card
          title={activeAgent ? activeAgent.name : "请选择智能体"}
          extra={
            activeAgent && (
              <Space>
                <Button icon={<PlayCircleOutlined />} onClick={() => setRunOpen(true)}>立即执行</Button>
                <Button icon={<ScheduleOutlined />} onClick={openCreateSchedule}>新增定时</Button>
                <Button onClick={() => openEditAgent(activeAgent)}>编辑</Button>
                <Button danger onClick={() => Modal.confirm({ title: "删除智能体", content: "会同时删除该智能体的定时任务。", onOk: async () => { await deleteAgent(activeAgent.id); setActiveId(null); await refreshAll(); } })}>删除</Button>
              </Space>
            )
          }
        >
          {!activeAgent ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="从左侧选择或创建智能体" />
          ) : (
            <Tabs
              items={[
                {
                  key: "profile",
                  label: "设定",
                  children: (
                    <Space direction="vertical" size={12} style={{ width: "100%" }}>
                      <Typography.Paragraph>{activeAgent.description || "暂无描述"}</Typography.Paragraph>
                      <Typography.Text type="secondary">系统提示词</Typography.Text>
                      <pre style={{ whiteSpace: "pre-wrap", background: "var(--bg-muted)", padding: 12, borderRadius: 8 }}>{activeAgent.system_prompt}</pre>
                    </Space>
                  ),
                },
                {
                  key: "schedules",
                  label: "定时任务",
                  children: (
                    <ProTable<AgentSchedule>
                      rowKey="id"
                      search={false}
                      options={false}
                      dataSource={schedules.data?.items ?? []}
                      loading={schedules.isLoading}
                      pagination={{ pageSize: 6 }}
                      columns={[
                        { title: "名称", dataIndex: "name" },
                        { title: "Cron", dataIndex: "cron", width: 130 },
                        { title: "状态", dataIndex: "enabled", width: 90, render: (_, r) => <Tag color={r.enabled ? "green" : "default"}>{r.enabled ? "启用" : "停用"}</Tag> },
                        { title: "下次执行", dataIndex: "next_run_at", valueType: "dateTime", width: 170 },
                        { title: "操作", width: 150, render: (_, r) => <Space><Button size="small" onClick={() => openEditSchedule(r)}>编辑</Button><Button size="small" danger onClick={async () => { await deleteSchedule(r.id); await refreshAll(); }}>删除</Button></Space> },
                      ]}
                    />
                  ),
                },
                {
                  key: "runs",
                  label: "执行记录",
                  children: <ProTable<AgentRun> rowKey="id" search={false} options={false} dataSource={runs.data?.items ?? []} loading={runs.isLoading} columns={runColumns} pagination={{ pageSize: 8 }} />,
                },
              ]}
            />
          )}
        </Card>
      </div>

      <Drawer title={editingAgent ? "编辑智能体" : "新建智能体"} open={agentOpen} width={620} onClose={() => setAgentOpen(false)} extra={<Button type="primary" onClick={saveAgent}>保存</Button>}>
        <Form form={agentForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="model_value" label="默认模型"><Select allowClear showSearch optionFilterProp="label" options={modelOptions} placeholder="不选则使用全局默认模型" /></Form.Item>
          <Form.Item name="system_prompt" label="智能体提示词" rules={[{ required: true, message: "请输入提示词" }]}><Input.TextArea rows={10} /></Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Drawer>

      <Drawer title={editingSchedule ? "编辑定时任务" : "新增定时任务"} open={scheduleOpen} width={620} onClose={() => setScheduleOpen(false)} extra={<Button type="primary" onClick={saveSchedule}>保存</Button>}>
        <Form form={scheduleForm} layout="vertical">
          <Form.Item name="agent_id" hidden><Input /></Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}><Input /></Form.Item>
          <Form.Item name="cron" label="Cron 表达式" tooltip="5 段格式：分钟 小时 日 月 星期，例如每天 9 点为 0 9 * * *" rules={[{ required: true, message: "请输入 Cron" }]}><Input /></Form.Item>
          <Form.Item name="timezone" label="时区"><Input /></Form.Item>
          <Form.Item name="prompt" label="自动执行任务词" rules={[{ required: true, message: "请输入任务词" }]}><Input.TextArea rows={8} /></Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Drawer>

      <Modal title={`运行智能体${activeAgent ? `：${activeAgent.name}` : ""}`} open={runOpen} onCancel={() => setRunOpen(false)} onOk={submitRun} okText="执行">
        <Form form={runForm} layout="vertical">
          <Form.Item name="prompt" label="本次任务" rules={[{ required: true, message: "请输入任务" }]}><Input.TextArea rows={6} placeholder="例如：分析最近差评并给出今天客服处理建议" /></Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
