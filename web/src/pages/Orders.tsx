import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { KpiTile } from "../components/KpiTile";

interface Order {
  id: number;
  order_sn: string;
  goods_name: string | null;
  sale_num: number | null;
  order_amount: number;
  pay_time: string | null;
  status: number | null;
  scraped_at: string | null;
}

interface OrderListResponse {
  total: number;
  items: Order[];
}

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: "待付款", color: "default" },
  1: { text: "已付款", color: "blue" },
  2: { text: "待发货", color: "orange" },
  3: { text: "已发货", color: "cyan" },
  4: { text: "已完成", color: "green" },
  5: { text: "已退款", color: "red" },
  6: { text: "已关闭", color: "default" },
};

export default function Orders() {
  const stats = useQuery<{ total_orders: number; total_amount_yuan: number }>({
    queryKey: ["orders-stats"],
    queryFn: () => getJSON("/orders/stats"),
  });

  return (
    <PageContainer header={{ title: "订单", subTitle: "真实抖店订单 · 实时分析" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 16 }}>
        <KpiTile label="订单总数" value={stats.data?.total_orders ?? "—"} />
        <KpiTile
          label="累计 GMV"
          value={stats.data ? `¥${stats.data.total_amount_yuan.toFixed(2)}` : "—"}
          accent="var(--accent)"
        />
      </div>

      <ProTable<Order>
        rowKey="id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async (params) => {
          const { current = 1, pageSize = 20, status } = params as any;
          const r = await getJSON<OrderListResponse>("/orders", {
            page: current - 1,
            page_size: pageSize,
            status,
          });
          return { data: r.items, success: true, total: r.total };
        }}
        columns={[
          { title: "订单号", dataIndex: "order_sn", copyable: true, width: 200, search: false },
          { title: "商品", dataIndex: "goods_name", ellipsis: true, search: false },
          { title: "数量", dataIndex: "sale_num", width: 70, search: false },
          {
            title: "金额",
            dataIndex: "order_amount",
            width: 110,
            search: false,
            render: (_, r) => (
              <span style={{ fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>
                ¥{r.order_amount.toFixed(2)}
              </span>
            ),
          },
          {
            title: "状态",
            dataIndex: "status",
            width: 100,
            valueEnum: Object.fromEntries(
              Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
            ),
            render: (_, r) => {
              const s = STATUS_MAP[r.status ?? -1];
              return s ? <Tag color={s.color}>{s.text}</Tag> : <Tag>{r.status}</Tag>;
            },
          },
          {
            title: "支付时间",
            dataIndex: "pay_time",
            valueType: "dateTime",
            width: 170,
            search: false,
          },
        ]}
      />
    </PageContainer>
  );
}
