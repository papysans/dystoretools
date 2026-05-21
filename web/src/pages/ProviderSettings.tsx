import { useState } from "react";
import { Button, Form, Input, Modal, Select, Space, Switch, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "../components/Card";
import {
  LlmProvider,
  listModels,
  listProviders,
  saveModel,
  saveProvider,
  syncProviderModels,
  testProvider,
} from "../api/llm";

export function ProviderSettings() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<LlmProvider | null>(null);
  const [syncingProviderId, setSyncingProviderId] = useState<number | null>(null);
  const providers = useQuery({ queryKey: ["llm-providers"], queryFn: listProviders });
  const models = useQuery({ queryKey: ["llm-models"], queryFn: () => listModels() });
  const providerNameById = new Map((providers.data?.items ?? []).map((provider) => [provider.id, provider.name]));

  const saveProviderMutation = useMutation({
    mutationFn: saveProvider,
    onSuccess: () => {
      message.success("Provider 已保存");
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["llm-providers"] });
    },
  });

  const saveModelMutation = useMutation({
    mutationFn: saveModel,
    onSuccess: () => {
      message.success("模型已更新");
      qc.invalidateQueries({ queryKey: ["llm-models"] });
    },
  });

  const runTest = async (id: number) => {
    const r = await testProvider(id);
    if (r.ok) message.success(`连接成功 · ${r.latency_ms ?? 0}ms`);
    else message.error(r.error ?? "连接失败");
  };

  const syncModels = async (id: number) => {
    setSyncingProviderId(id);
    try {
      const r = await syncProviderModels(id);
      if (r.ok) {
        message.success(`已同步 ${r.total ?? r.models?.length ?? 0} 个模型，新增 ${r.created ?? 0} 个`);
        await Promise.all([
          qc.invalidateQueries({ queryKey: ["llm-models"] }),
          qc.invalidateQueries({ queryKey: ["llm-providers"] }),
          qc.invalidateQueries({ queryKey: ["chat-models"] }),
        ]);
      } else {
        message.warning(r.error ?? "模型同步失败");
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail ?? error?.message ?? "模型同步失败");
    } finally {
      setSyncingProviderId(null);
    }
  };

  return (
    <Card
      title="模型与 Provider"
      extra={<Button type="primary" onClick={() => setEditing({} as LlmProvider)}>添加 Provider</Button>}
      style={{ marginTop: 16 }}
    >
      <Table<LlmProvider>
        rowKey="id"
        dataSource={providers.data?.items ?? []}
        loading={providers.isLoading}
        pagination={false}
        columns={[
          { title: "名称", dataIndex: "name" },
          { title: "适配器", dataIndex: "adapter_kind", render: (v) => <Tag>{v}</Tag> },
          { title: "Base URL", dataIndex: "base_url" },
          { title: "Key", render: (_, r) => (r.key_set ? <Tag color="green">{r.key_fingerprint}</Tag> : <Tag>未配置</Tag>) },
          { title: "状态", render: (_, r) => <Tag color={r.enabled ? "green" : "default"}>{r.enabled ? "启用" : "停用"}</Tag> },
          {
            title: "操作",
            render: (_, r) => (
              <Space>
                <Button size="small" onClick={() => setEditing(r)}>编辑</Button>
                <Button size="small" onClick={() => runTest(r.id)}>测试</Button>
                <Button size="small" loading={syncingProviderId === r.id} onClick={() => syncModels(r.id)}>
                  同步模型
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Table
        rowKey="id"
        dataSource={models.data?.items ?? []}
        loading={models.isLoading}
        pagination={false}
        style={{ marginTop: 16 }}
        columns={[
          { title: "Provider", dataIndex: "provider_id", width: 140, render: (id: number) => providerNameById.get(id) ?? id },
          { title: "模型", dataIndex: "model_name" },
          { title: "上下文", dataIndex: "context_window", width: 120 },
          {
            title: "能力",
            dataIndex: "capabilities",
            render: (v: string[]) => (v?.length ? v.map((x) => <Tag key={x}>{x}</Tag>) : <Tag>非聊天</Tag>),
          },
          {
            title: "默认聊天",
            render: (_, r: any) => (
              <Switch
                checked={r.is_default_for_chat}
                onChange={(checked) => saveModelMutation.mutate({ id: r.id, is_default_for_chat: checked })}
              />
            ),
          },
        ]}
      />

      <ProviderModal
        provider={editing}
        onCancel={() => setEditing(null)}
        onSave={(values) => saveProviderMutation.mutate(values)}
      />
    </Card>
  );
}

function ProviderModal({
  provider,
  onCancel,
  onSave,
}: {
  provider: LlmProvider | null;
  onCancel: () => void;
  onSave: (values: any) => void;
}) {
  const [form] = Form.useForm();
  return (
    <Modal
      title={provider?.id ? "编辑 Provider" : "添加 Provider"}
      open={!!provider}
      onCancel={onCancel}
      onOk={() => form.submit()}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={provider ?? { adapter_kind: "openai_compat", enabled: true }}
        onFinish={(values) => onSave({ ...values, id: provider?.id })}
      >
        <Form.Item name="name" label="名称" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="adapter_kind" label="适配器" rules={[{ required: true }]}>
          <Select options={[
            { label: "OpenAI Compatible", value: "openai_compat" },
            { label: "Anthropic", value: "anthropic" },
          ]} />
        </Form.Item>
        <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="api_key" label="API Key" extra="留空表示不替换已有 key">
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <Form.Item name="enabled" label="启用" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
