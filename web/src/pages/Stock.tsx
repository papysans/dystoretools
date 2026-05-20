import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { KpiTile } from "../components/KpiTile";

interface StockRow {
  goods_id: string;
  title: string | null;
  on_hand: number;
  available: number;
  locked: number;
  level: string;
  scraped_at: string | null;
}

interface StockListResponse {
  total: number;
  items: StockRow[];
}

interface StockLevels {
  out: number;
  low: number;
  normal: number;
  over: number;
}

// API exposes `normal` (not `dead`); the 4th tile is relabeled 正常 accordingly.
const LEVEL_MAP: Record<string, { text: string; color: string }> = {
  out: { text: "缺货", color: "red" },
  low: { text: "低库存", color: "orange" },
  over: { text: "超量", color: "blue" },
  normal: { text: "正常", color: "default" },
};

const numCell: React.CSSProperties = { fontVariantNumeric: "tabular-nums", textAlign: "right", display: "block" };

export default function Stock() {
  const levels = useQuery<StockLevels>({
    queryKey: ["stock-levels"],
    queryFn: () => getJSON("/stock/levels"),
  });

  return (
    <PageContainer header={{ title: "库存", subTitle: "SKU 健康度诊断" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 16 }}>
        <KpiTile label="低库存" value={levels.data?.low ?? "—"} accent="var(--warning)" />
        <KpiTile label="缺货" value={levels.data?.out ?? "—"} accent="var(--critical)" />
        <KpiTile label="超量" value={levels.data?.over ?? "—"} accent="var(--info)" />
        <KpiTile label="正常" value={levels.data?.normal ?? "—"} />
      </div>

      <ProTable<StockRow>
        rowKey="goods_id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async (params) => {
          const { current = 1, pageSize = 50, goods_id } = params as any;
          const r = await getJSON<StockListResponse>("/stock", {
            page: current - 1,
            page_size: pageSize,
            goods_id,
          });
          return { data: r.items, success: true, total: r.total };
        }}
        pagination={{ defaultPageSize: 50 }}
        columns={[
          {
            title: "商品",
            dataIndex: "title",
            ellipsis: true,
            render: (_, r) =>
              r.title ?? <span style={{ color: "var(--text-tertiary)" }}>{r.goods_id}</span>,
          },
          { title: "商品 ID", dataIndex: "goods_id", hideInTable: true },
          {
            title: "在仓",
            dataIndex: "on_hand",
            width: 80,
            search: false,
            render: (_, r) => <span style={numCell}>{r.on_hand}</span>,
          },
          {
            title: "可用",
            dataIndex: "available",
            width: 80,
            search: false,
            render: (_, r) => <span style={numCell}>{r.available}</span>,
          },
          {
            title: "锁定",
            dataIndex: "locked",
            width: 80,
            search: false,
            render: (_, r) => <span style={numCell}>{r.locked}</span>,
          },
          {
            title: "等级",
            dataIndex: "level",
            width: 90,
            search: false,
            render: (_, r) => {
              const m = LEVEL_MAP[r.level];
              return m ? <Tag color={m.color}>{m.text}</Tag> : <Tag>{r.level}</Tag>;
            },
          },
          {
            title: "抓取时间",
            dataIndex: "scraped_at",
            valueType: "dateTime",
            width: 170,
            search: false,
          },
        ]}
      />
    </PageContainer>
  );
}
