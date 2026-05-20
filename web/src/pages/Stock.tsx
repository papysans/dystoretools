import { PageContainer } from "@ant-design/pro-components";
import { Empty, Tag } from "antd";
import { Card } from "../components/Card";

export default function Stock() {
  return (
    <PageContainer header={{ title: "库存", subTitle: "SKU 健康度诊断" }}>
      <Card title="库存等级图例">
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <Tag color="orange">低库存</Tag>
          <Tag color="red">缺货</Tag>
          <Tag color="blue">超量</Tag>
          <Tag>呆滞</Tag>
        </div>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无数据 · 等待首次 stock 抓取" />
      </Card>
    </PageContainer>
  );
}
