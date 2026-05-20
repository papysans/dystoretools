import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getJSON } from "../api/client";
import { KpiTile } from "../components/KpiTile";

interface Good {
  goods_id: string;
  title: string;
  price: number;
  stock: number;
  tab: string | null;
  check_status: number | null;
  scraped_at: string | null;
}

interface GoodsListResponse {
  total: number;
  items: Good[];
}

interface GoodsStats {
  total: number;
  on_sale: number;
  low_count: number;
}

export default function GoodsPage() {
  const stats = useQuery<GoodsStats>({
    queryKey: ["goods-stats"],
    queryFn: () => getJSON("/goods/stats"),
  });

  return (
    <PageContainer header={{ title: "商品", subTitle: "在售 · 库存 · 审核" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 16 }}>
        <KpiTile label="商品总数" value={stats.data?.total ?? "—"} />
        <KpiTile label="在售商品" value={stats.data?.on_sale ?? "—"} accent="var(--accent)" />
        <KpiTile label="低库存数" value={stats.data?.low_count ?? "—"} accent="var(--critical)" />
      </div>

      <ProTable<Good>
        rowKey="goods_id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async (params) => {
          const { current = 1, pageSize = 20, tab, check_status } = params as any;
          const r = await getJSON<GoodsListResponse>("/goods", {
            page: current,
            page_size: pageSize,
            tab,
            check_status,
          });
          return { data: r.items, success: true, total: r.total };
        }}
        columns={[
          { title: "商品", dataIndex: "title", ellipsis: true, copyable: false, search: false },
          {
            title: "价格",
            dataIndex: "price",
            width: 100,
            search: false,
            render: (_, r) => (
              <span style={{ fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>
                ¥{r.price.toFixed(2)}
              </span>
            ),
          },
          {
            title: "库存",
            dataIndex: "stock",
            width: 80,
            search: false,
            align: "right",
            render: (_, r) => (
              <span style={{ fontVariantNumeric: "tabular-nums" }}>{r.stock}</span>
            ),
          },
          {
            title: "状态",
            dataIndex: "tab",
            width: 100,
            valueEnum: {
              "售卖中": { text: "售卖中" },
              "已下架": { text: "已下架" },
            },
          },
          {
            title: "审核",
            dataIndex: "check_status",
            width: 80,
            search: false,
            render: (_, r) =>
              r.check_status === 3 ? <Tag color="green">已通过</Tag> : <Tag>{r.check_status ?? "—"}</Tag>,
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
