import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Button, message } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { getJSON, postJSON } from "../api/client";

interface AlertRow {
  id: number;
  kind: string;
  severity: string;
  payload: Record<string, unknown>;
  dispatched_at: string;
  acked_at: string | null;
}

const sevColour: Record<string, string> = {
  critical: "var(--critical)",
  warn: "var(--warning)",
  info: "var(--info)",
};

function SeverityDot({ severity }: { severity: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 500, fontSize: 12 }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: sevColour[severity] ?? "var(--text-tertiary)" }} />
      <span style={{ textTransform: "uppercase", letterSpacing: "0.04em" }}>{severity}</span>
    </span>
  );
}

export default function Alerts() {
  const qc = useQueryClient();

  const ack = async (id: number) => {
    try {
      await postJSON(`/alerts/${id}/ack`);
      message.success("已确认");
      qc.invalidateQueries({ queryKey: ["alerts-table"] });
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "确认失败");
    }
  };

  return (
    <PageContainer header={{ title: "告警", subTitle: "实时事件 · 一键确认" }}>
      <ProTable<AlertRow>
        rowKey="id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async (params) => {
          const { pageSize = 50, kind, severity, acked } = params as any;
          const items = await getJSON<AlertRow[]>("/alerts", { kind, severity, acked, limit: pageSize });
          return { data: items, success: true, total: items.length };
        }}
        columns={[
          { title: "ID", dataIndex: "id", width: 80, search: false },
          { title: "类型", dataIndex: "kind" },
          {
            title: "级别",
            dataIndex: "severity",
            valueEnum: { critical: "critical", warn: "warn", info: "info" },
            render: (_, r) => <SeverityDot severity={r.severity} />,
          },
          { title: "时间", dataIndex: "dispatched_at", valueType: "dateTime", search: false },
          {
            title: "状态",
            dataIndex: "acked_at",
            search: false,
            render: (_, r) => (
              <span style={{ fontSize: 12, color: r.acked_at ? "var(--text-tertiary)" : "var(--accent)" }}>
                {r.acked_at ? "已确认" : "未确认"}
              </span>
            ),
          },
          {
            title: "操作",
            search: false,
            render: (_, r) => (r.acked_at ? null : <Button size="small" onClick={() => ack(r.id)}>确认</Button>),
          },
        ]}
      />
    </PageContainer>
  );
}
