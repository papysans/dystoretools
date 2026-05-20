import { useEffect, useState } from "react";
import { PageContainer } from "@ant-design/pro-components";
import { Alert, Button, Form, Input, Select, Space, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { Card } from "../components/Card";
import { ProviderSettings } from "./ProviderSettings";
import axios from "axios";

interface AuthStatus {
  last_event: { kind: string; occurred_at: string; payload: Record<string, unknown> | null } | null;
  session_ready: boolean;
}

interface SettingValue {
  value: string | null;
  kind: "secret" | "string";
  source: "db" | "env" | "none";
  has_value: boolean;
}

interface SettingsResponse {
  keys: string[];
  values: Record<string, SettingValue>;
}

const LLM_KEYS = [
  { key: "deepseek_api_key", label: "DeepSeek API Key", placeholder: "sk-...", secret: true },
  { key: "deepseek_base_url", label: "DeepSeek Base URL", placeholder: "https://api.deepseek.com" },
  {
    key: "deepseek_model",
    label: "DeepSeek 模型",
    placeholder: "deepseek-v4-pro",
    options: ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
  },
  { key: "kimi_api_key", label: "Kimi (Moonshot) API Key", placeholder: "sk-...", secret: true },
  { key: "kimi_base_url", label: "Kimi Base URL", placeholder: "https://api.moonshot.cn/v1" },
  {
    key: "kimi_model",
    label: "Kimi 模型",
    placeholder: "moonshot-v1-128k",
    options: ["moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
  },
] as const;

const BROWSER_KEYS = [
  {
    key: "merchant_browser_mode",
    label: "抖店浏览器模式",
    placeholder: "playwright",
    options: ["playwright", "cdp"],
  },
  {
    key: "merchant_cdp_url",
    label: "CDP 端点 URL",
    placeholder: "http://host.docker.internal:9222",
  },
] as const;

const PUBLIC_KEYS = [
  {
    key: "public_scraper_backend",
    label: "同行抓取后端",
    placeholder: "playwright",
    options: ["playwright", "huitu", "chanmama"],
  },
  { key: "huitu_api_key", label: "灰豚 API Key", placeholder: "（可选，使用 huitu 后端时填）", secret: true },
  { key: "chanmama_api_key", label: "蝉妈妈 API Key", placeholder: "（可选，使用 chanmama 后端时填）", secret: true },
] as const;

function sourceTag(s: SettingValue["source"]) {
  if (s === "db") return <Tag color="blue">数据库</Tag>;
  if (s === "env") return <Tag>环境变量</Tag>;
  return <Tag color="default">未配置</Tag>;
}

export default function Settings() {
  const qc = useQueryClient();
  const [form] = Form.useForm();

  const q = useQuery<SettingsResponse>({
    queryKey: ["settings"],
    queryFn: () => getJSON<SettingsResponse>("/settings"),
  });

  useEffect(() => {
    if (!q.data) return;
    const init: Record<string, string> = {};
    for (const k of q.data.keys) init[k] = q.data.values[k]?.value ?? "";
    form.setFieldsValue(init);
  }, [q.data, form]);

  const mut = useMutation({
    mutationFn: (values: Record<string, string | null>) =>
      axios.put("/api/v1/settings", { values }).then((r) => r.data),
    onSuccess: () => {
      message.success("已保存");
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.detail ?? "保存失败"),
  });

  const onSave = async () => {
    const vals = await form.validateFields();
    mut.mutate(vals);
  };

  const onClearOne = (key: string) => {
    form.setFieldValue(key, "");
    mut.mutate({ [key]: "" });
  };

  const renderField = (k: { key: string; label: string; placeholder: string; secret?: boolean; options?: readonly string[] }) => {
    const v = q.data?.values[k.key];
    return (
      <Form.Item
        key={k.key}
        name={k.key}
        label={
          <Space>
            <span>{k.label}</span>
            {v && sourceTag(v.source)}
          </Space>
        }
        extra={
          v?.source === "db" ? (
            <a onClick={() => onClearOne(k.key)} style={{ fontSize: 12 }}>清除数据库覆盖（恢复环境变量）</a>
          ) : undefined
        }
      >
        {k.options ? (
          <Select placeholder={k.placeholder} options={k.options.map((o) => ({ label: o, value: o }))} allowClear />
        ) : k.secret ? (
          <Input.Password placeholder={k.placeholder} autoComplete="new-password" />
        ) : (
          <Input placeholder={k.placeholder} />
        )}
      </Form.Item>
    );
  };

  return (
    <PageContainer header={{ title: "设置", subTitle: "API Key · Base URL · 登录态导入" }}>
      <Alert
        type="info"
        showIcon
        message="覆盖优先级"
        description="此处填入的值会以数据库优先，环境变量 .env 作为兜底。密钥字段在读取时会被掩码（前 4 + 后 4），保存原值不变；只有真正修改后才写库。"
        style={{ marginBottom: 16 }}
      />

      <CookieImportCard />
      <ProviderSettings />

      <Form form={form} layout="vertical" onFinish={onSave} disabled={mut.isPending || q.isLoading}>
        <Card title="抖店浏览器后端" style={{ marginTop: 16 }}>
          <Alert
            type="warning"
            showIcon
            message="为什么有这个选项？"
            description={
              <span>
                抖店风控认得出 docker 里 Chromium 的指纹，拦截 API 请求。
                选 <b>cdp</b> 模式后，dystoretools 通过 CDP 连接你电脑上常驻的 Chrome（真指纹、真 IP），完美绕开。
                <br />
                启动 host Chrome（一次性）：
                <code style={{ display: "block", marginTop: 6, fontFamily: "var(--font-mono)", padding: 8, background: "rgba(0,0,0,0.05)", borderRadius: 6 }}>
                  pwsh scripts/launch-host-chrome.ps1  &nbsp;# Windows
                  <br />
                  bash scripts/launch-host-chrome.sh   &nbsp;# macOS/Linux
                </code>
                然后在弹出的 Chrome 里登录抖店，切此处为 cdp，保存。
              </span>
            }
            style={{ marginBottom: 12 }}
          />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16 }}>
            {BROWSER_KEYS.map(renderField)}
          </div>
        </Card>

        <Card title="LLM 提供商" style={{ marginTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {LLM_KEYS.map(renderField)}
          </div>
        </Card>

        <Card title="同行抓取" style={{ marginTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            {PUBLIC_KEYS.map(renderField)}
          </div>
        </Card>

        <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button onClick={() => q.refetch()}>重新加载</Button>
          <Button type="primary" onClick={onSave} loading={mut.isPending}>
            保存
          </Button>
        </div>
      </Form>
    </PageContainer>
  );
}


function CookieImportCard() {
  const [raw, setRaw] = useState("");
  const qc = useQueryClient();

  const status = useQuery<AuthStatus>({
    queryKey: ["auth-status"],
    queryFn: () => getJSON<AuthStatus>("/auth/status"),
    refetchInterval: 10_000,
  });

  const mut = useMutation({
    mutationFn: (payload: string) => axios.post("/api/v1/auth/import-cookies", { raw: payload }).then((r) => r.data),
    onSuccess: (r) => {
      message.success(`已导入 ${r.imported} 条 cookie`);
      setRaw("");
      qc.invalidateQueries({ queryKey: ["auth-status"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.detail ?? "导入失败"),
  });

  const sessionBadge = () => {
    if (status.data?.session_ready) {
      return <Tag color="green">登录态有效</Tag>;
    }
    const k = status.data?.last_event?.kind;
    if (k === "session_expired") return <Tag color="orange">登录态过期</Tag>;
    if (k === "risk_verification_required") return <Tag color="red">需安全验证</Tag>;
    return <Tag color="default">未登录</Tag>;
  };

  return (
    <Card
      title={
        <Space>
          抖店登录态
          {sessionBadge()}
        </Space>
      }
    >
      <Alert
        type="warning"
        showIcon
        message="为什么要导入 cookies？"
        description="Docker 内无显示器，无法直接弹窗扫码登录。请在你的电脑浏览器（已登录抖店）里用插件如「EditThisCookie」或「Cookie-Editor」导出 fxg.jinritemai.com 的所有 cookies（JSON 格式），粘贴到下方。系统只会保留 jinritemai / bytedance / oceanengine 三个域名的 cookies。"
        style={{ marginBottom: 12 }}
      />
      <Input.TextArea
        rows={6}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        placeholder='粘贴 cookies JSON 数组，例如 [{"name":"SESSIONID","value":"...","domain":".jinritemai.com",...},...]'
        style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
      />
      <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
        <Button type="primary" onClick={() => mut.mutate(raw)} disabled={!raw.trim()} loading={mut.isPending}>
          导入并保存
        </Button>
      </div>
      {status.data?.last_event && (
        <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
          最近一次事件：{status.data.last_event.kind} · {new Date(status.data.last_event.occurred_at).toLocaleString("zh-CN")}
        </div>
      )}
    </Card>
  );
}
