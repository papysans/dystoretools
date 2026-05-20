import { PageContainer } from "@ant-design/pro-components";
import { KpiTile } from "../components/KpiTile";
import { Card } from "../components/Card";

export default function Member() {
  return (
    <PageContainer header={{ title: "用户运营", subTitle: "会员看板 · 受众画像" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <KpiTile label="会员总数" value="—" hint="等待 12:00 抓取" />
        <KpiTile label="活跃会员" value="—" />
        <KpiTile label="新增会员" value="—" />
        <KpiTile label="复购率" value="—" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16, marginTop: 16 }}>
        <Card title="日趋势">
          <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0", textAlign: "center" }}>
            <code style={{ fontFamily: "var(--font-mono)" }}>member_dashboard_day</code> 抓取后渲染折线图。
          </div>
        </Card>
        <Card title="受众画像">
          <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0", textAlign: "center" }}>
            <code style={{ fontFamily: "var(--font-mono)" }}>audience_feature</code> 抓取后渲染分布图。
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}
