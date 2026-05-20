import { useState } from "react";
import { PageContainer } from "@ant-design/pro-components";
import { Button, Form, Input, Select, message, Space, Tag } from "antd";
import { postJSON } from "../api/client";
import { Card } from "../components/Card";

const KINDS = [
  { label: "商品标题", value: "title" },
  { label: "商品详情", value: "detail" },
  { label: "直播话术", value: "livestream_script" },
  { label: "短视频脚本", value: "short_video_script" },
];

interface GenResult {
  ai_generation_id: number;
  output_text: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
}

export default function ContentWorkshop() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenResult | null>(null);

  const onFinish = async (vals: { kind: string; goods_id: string; extra_context?: string }) => {
    setLoading(true);
    try {
      const r = await postJSON<GenResult>("/content/generate", vals);
      setResult(r);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "生成失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer header={{ title: "文案工坊", subTitle: "AI 生成商品文案 · 直播话术 · 短视频脚本" }}>
      <div style={{ display: "grid", gridTemplateColumns: result ? "minmax(360px, 1fr) 1.4fr" : "1fr", gap: 16 }}>
        <Card title="生成参数">
          <Form layout="vertical" onFinish={onFinish}>
            <Form.Item name="kind" label="内容类型" rules={[{ required: true }]}>
              <Select options={KINDS} placeholder="选择类型" size="large" />
            </Form.Item>
            <Form.Item name="goods_id" label="商品 ID" rules={[{ required: true }]}>
              <Input placeholder="例如：3700000123456" size="large" />
            </Form.Item>
            <Form.Item name="extra_context" label="补充上下文">
              <Input.TextArea rows={4} placeholder="可选：附加背景，例如目标人群、活动主题、卖点强调…" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} size="large" block>
              开始生成
            </Button>
          </Form>
        </Card>

        {result && (
          <Card
            title={
              <Space>
                生成结果
                <Tag color="blue">{result.model}</Tag>
              </Space>
            }
            extra={
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                in {result.tokens_in} · out {result.tokens_out}
              </span>
            }
          >
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "var(--font-family)",
                fontSize: 14,
                lineHeight: 1.6,
                margin: 0,
                color: "var(--text)",
              }}
            >
              {result.output_text}
            </pre>
          </Card>
        )}
      </div>
    </PageContainer>
  );
}
