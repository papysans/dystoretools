import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Button, Select, Space, Tag, message } from "antd";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getJSON, postJSON } from "../api/client";
import { useTaskStreamStore } from "../stores";
import { Card } from "../components/Card";

interface Run { id: number; target: string; subsystem: string; status: string; started_at: string | null; finished_at: string | null; items_count: number; error_msg: string | null }
interface Target { target: string; subsystem: string; nav_url: string; cron: string; sink_table: string }

const statusTag = (s: string) => {
  if (s === "done") return <Tag color="green">完成</Tag>;
  if (s === "running") return <Tag color="blue">运行中</Tag>;
  if (s === "failed") return <Tag color="red">失败</Tag>;
  if (s === "auth_expired") return <Tag color="orange">需登录</Tag>;
  return <Tag>{s}</Tag>;
};

export default function Tasks() {
  const [pickedTarget, setPickedTarget] = useState<string | null>(null);
  const targets = useQuery({ queryKey: ["scrape-targets"], queryFn: () => getJSON<Target[]>("/scrape/targets") });
  const events = useTaskStreamStore((s) => s.events);

  const onRun = async () => {
    if (!pickedTarget) return;
    try {
      await postJSON(`/scrape/run?target=${encodeURIComponent(pickedTarget)}`);
      message.success("已派发");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "派发失败");
    }
  };

  return (
    <PageContainer header={{ title: "任务", subTitle: "Scrape 编排 · 实时事件流" }}>
      <Card title="手动运行">
        <Space wrap>
          <Select
            style={{ width: 360 }}
            placeholder="选择 scrape 目标"
            showSearch
            optionFilterProp="label"
            options={targets.data?.map((t) => ({ label: `${t.target} · ${t.subsystem}`, value: t.target }))}
            onChange={setPickedTarget}
          />
          <Button type="primary" onClick={onRun} disabled={!pickedTarget}>立即执行</Button>
        </Space>
      </Card>

      <Card title="实时事件流" style={{ marginTop: 16 }}>
        {events.length === 0 ? (
          <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>等待事件…</div>
        ) : (
          <div style={{ maxHeight: 240, overflowY: "auto", fontFamily: "var(--font-mono)", fontSize: 12 }}>
            {events.slice(0, 50).map((e, i) => (
              <div key={i} style={{ padding: "4px 0", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--text-tertiary)" }}>
                  [{new Date(e.ts).toLocaleTimeString("zh-CN")}]
                </span>{" "}
                <span style={{ color: "var(--accent)" }}>{e.kind}</span>
                {" · "}{e.target} {e.items !== undefined ? `· ${e.items} items` : ""}{e.error ? ` · ${e.error}` : ""}
              </div>
            ))}
          </div>
        )}
      </Card>

      <ProTable<Run>
        style={{ marginTop: 16 }}
        rowKey="id"
        search={false}
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        request={async () => {
          const runs = await getJSON<Run[]>("/scrape/runs", { limit: 100 });
          return { data: runs, success: true };
        }}
        columns={[
          { title: "ID", dataIndex: "id", width: 70 },
          { title: "目标", dataIndex: "target" },
          { title: "状态", dataIndex: "status", render: (_, r) => statusTag(r.status) },
          { title: "条数", dataIndex: "items_count", width: 80 },
          { title: "起始", dataIndex: "started_at", valueType: "dateTime" },
          { title: "结束", dataIndex: "finished_at", valueType: "dateTime" },
        ]}
      />
    </PageContainer>
  );
}
