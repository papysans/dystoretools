import { PageContainer, ProTable } from "@ant-design/pro-components";
import { getJSON } from "../api/client";

interface Run { id: number; target: string; status: string; items_count: number; finished_at: string | null }

export default function GoodsPage() {
  return (
    <PageContainer header={{ title: "商品", subTitle: "在售 · 库存 · 转化" }}>
      <ProTable<Run>
        rowKey="id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async () => {
          const runs = await getJSON<Run[]>("/scrape/runs", { target: "doudian_product", limit: 20 });
          return { data: runs, success: true };
        }}
        columns={[
          { title: "运行 ID", dataIndex: "id", width: 100 },
          { title: "目标", dataIndex: "target" },
          { title: "状态", dataIndex: "status" },
          { title: "条数", dataIndex: "items_count" },
          { title: "完成时间", dataIndex: "finished_at", valueType: "dateTime", search: false },
        ]}
      />
    </PageContainer>
  );
}
