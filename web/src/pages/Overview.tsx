import { PageContainer } from "@ant-design/pro-components";
import { useQuery } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { Card } from "../components/Card";
import { KpiTile } from "../components/KpiTile";
import { Empty, Tag } from "antd";

interface Task { id: number; target: string; status: string; items_count: number; finished_at: string | null }
interface AlertRow { id: number; kind: string; severity: string; dispatched_at: string }

const sevTone = (s: string) =>
  s === "critical" ? "var(--critical)" : s === "warn" ? "var(--warning)" : "var(--info)";

export default function Overview() {
  const tasks = useQuery({ queryKey: ["recent-tasks"], queryFn: () => getJSON<Task[]>("/scrape/runs", { limit: 10 }) });
  const alerts = useQuery({
    queryKey: ["recent-alerts"],
    queryFn: () => getJSON<AlertRow[]>("/alerts", { limit: 10, acked: false }),
  });

  const ok = tasks.data?.filter((t) => t.status === "done").length ?? 0;
  const fail = tasks.data?.filter((t) => t.status === "failed").length ?? 0;
  const unacked = alerts.data?.length ?? 0;

  return (
    <PageContainer header={{ title: "总览", subTitle: "实时运营态势" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <KpiTile label="今日完成抓取" value={ok} hint={`失败 ${fail}`} />
        <KpiTile label="活跃告警" value={unacked} hint="未确认" accent={unacked > 0 ? "var(--critical)" : undefined} />
        <KpiTile label="抓取目标总数" value={tasks.data?.length ?? "-"} hint="近 10 次" />
        <KpiTile label="平均条数" value={tasks.data && tasks.data.length ? Math.round(tasks.data.reduce((a, b) => a + b.items_count, 0) / tasks.data.length) : "-"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <Card title="最近抓取任务">
          {tasks.data?.length ? tasks.data.map((t) => (
            <div
              key={t.id}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--separator)" }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>{t.target}</div>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  {t.finished_at ? new Date(t.finished_at).toLocaleString("zh-CN") : "—"}
                </div>
              </div>
              <Tag color={t.status === "done" ? "green" : t.status === "failed" ? "red" : "default"}>
                {t.status} · {t.items_count}
              </Tag>
            </div>
          )) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无运行记录" />}
        </Card>

        <Card title="活跃告警">
          {alerts.data?.length ? alerts.data.map((a) => (
            <div
              key={a.id}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--separator)" }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>{a.kind}</div>
                <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  {new Date(a.dispatched_at).toLocaleString("zh-CN")}
                </div>
              </div>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  color: sevTone(a.severity),
                }}
              >
                {a.severity}
              </span>
            </div>
          )) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="一切平静" />}
        </Card>
      </div>
    </PageContainer>
  );
}
