import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { Card } from "../components/Card";
import { AFTERSALE_TYPE, AFTERSALE_STATUS, AFTERSALE_STATUS_COLOR } from "../api/enums";

// dim key → 中文 display label (canonical 18-dim order)
const DIM_LABELS: Record<string, string> = {
  all_audit_reg_spill: "全审单溢出",
  approaching_deadline_audit: "即将超时",
  urge_audit: "用户催办",
  presale_all_audit: "预售审单",
  refund_audit: "退款待审",
  return_audit: "退货待审",
  exchange_audit: "换货待审",
  resend_audit: "补发待审",
  repair_audit: "维修待审",
  wait_for_receive_and_delivery: "待收货发货",
  return_for_receive: "退货待收",
  exchange_for_receive: "换货待收",
  wait_user_delivery: "待用户寄回",
  wait_user_sign: "待用户签收",
  exchange_wait_user_sign: "换货待用户签收",
  arbitrate_pending_negotiation: "仲裁待协商",
  arbitrate_pending_evidence: "仲裁待举证",
  arbitrate_pending: "仲裁待处理",
};

const DIM_ORDER = Object.keys(DIM_LABELS);

const CRITICAL = new Set([
  "approaching_deadline_audit",
  "urge_audit",
  "arbitrate_pending",
  "arbitrate_pending_evidence",
  "arbitrate_pending_negotiation",
]);

const WARNING = new Set([
  "refund_audit",
  "return_audit",
  "exchange_audit",
  "resend_audit",
  "repair_audit",
  "wait_user_delivery",
  "wait_user_sign",
  "exchange_wait_user_sign",
]);

function toneOf(dim: string): string {
  if (CRITICAL.has(dim)) return "var(--critical)";
  if (WARNING.has(dim)) return "var(--warning)";
  return "var(--info)";
}

const TYPE_TAG_COLOR: Record<string, string> = {
  退款: "blue",
  退货: "orange",
  换货: "purple",
};

interface CountsResponse {
  scraped_at: string | null;
  dims: Record<string, number>;
}

interface AftersaleItem {
  aftersale_id: string;
  order_sn: string;
  type: number | null;
  type_label: string | null;
  status: number | null;
  status_label: string | null;
  refund_amount: number;
  deadline_at: string | null;
  scraped_at: string | null;
}

interface AftersaleListResponse {
  total: number;
  items: AftersaleItem[];
}

export default function Aftersale() {
  const counts = useQuery<CountsResponse>({
    queryKey: ["aftersale-counts"],
    queryFn: () => getJSON("/aftersale/counts"),
  });

  const dims = counts.data?.dims ?? {};

  return (
    <PageContainer header={{ title: "售后", subTitle: "18 维度即时计数" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        {DIM_ORDER.map((dim) => (
          <div key={dim} className="apple-card" style={{ padding: 16 }}>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {DIM_LABELS[dim]}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginTop: 6 }}>
              <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>
                {dims[dim] ?? "—"}
              </div>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: toneOf(dim) }} />
            </div>
            <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>{dim}</div>
          </div>
        ))}
      </div>

      <Card title="售后单列表" style={{ marginTop: 16 }} padding={0}>
        <ProTable<AftersaleItem>
          rowKey="aftersale_id"
          ghost
          cardProps={{ bodyStyle: { padding: 0 } }}
          options={false}
          search={{ filterType: "light" }}
          request={async (params) => {
            const { current = 1, pageSize = 20, status, type } = params as {
              current?: number;
              pageSize?: number;
              status?: number;
              type?: number;
            };
            const r = await getJSON<AftersaleListResponse>("/aftersale", {
              page: current - 1,
              page_size: pageSize,
              status,
              type,
            });
            return { data: r.items, success: true, total: r.total };
          }}
          columns={[
            { title: "售后号", dataIndex: "aftersale_id", width: 200, copyable: true, search: false },
            { title: "订单号", dataIndex: "order_sn", width: 200, copyable: true, search: false },
            {
              title: "类型",
              dataIndex: "type",
              width: 80,
              valueEnum: Object.fromEntries(
                Object.entries(AFTERSALE_TYPE).map(([k, v]) => [k, { text: v }])
              ),
              render: (_, r) => {
                if (!r.type_label) return <Tag>{r.type ?? "—"}</Tag>;
                const color = TYPE_TAG_COLOR[r.type_label] ?? "default";
                return <Tag color={color}>{r.type_label}</Tag>;
              },
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              valueEnum: Object.fromEntries(
                Object.entries(AFTERSALE_STATUS).map(([k, v]) => [k, { text: v }])
              ),
              render: (_, r) => {
                const color = r.status != null ? AFTERSALE_STATUS_COLOR[r.status] : undefined;
                const text = r.status_label ?? (r.status ?? "—");
                return <Tag color={color ?? "default"}>{text}</Tag>;
              },
            },
            {
              title: "退款金额",
              dataIndex: "refund_amount",
              width: 110,
              search: false,
              render: (_, r) => (
                <span style={{ fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>
                  ¥{r.refund_amount.toFixed(2)}
                </span>
              ),
            },
            {
              title: "截止时间",
              dataIndex: "deadline_at",
              valueType: "dateTime",
              width: 170,
              search: false,
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
}
