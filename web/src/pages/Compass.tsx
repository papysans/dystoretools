import { PageContainer } from "@ant-design/pro-components";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { Empty } from "antd";
import { getJSON } from "../api/client";
import { Card } from "../components/Card";
import { useTheme } from "../theme/ThemeProvider";

export default function Compass() {
  const { mode } = useTheme();
  const trend = useQuery({
    queryKey: ["compass-trend", "pay_amt"],
    queryFn: () => getJSON<{ date: string; value: number }[]>("/compass/trend", { index_name: "pay_amt", limit: 90 }),
  });

  const accent = mode === "dark" ? "#0A84FF" : "#0071E3";
  const ink = mode === "dark" ? "#F5F5F7" : "#1D1D1F";
  const muted = mode === "dark" ? "#98989D" : "#6E6E73";

  const opt = {
    grid: { left: 40, right: 20, top: 24, bottom: 32 },
    xAxis: {
      type: "category",
      data: trend.data?.map((d) => d.date) ?? [],
      axisLine: { lineStyle: { color: muted } },
      axisLabel: { color: muted, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      splitLine: { lineStyle: { color: mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)" } },
      axisLabel: { color: muted, fontSize: 11 },
    },
    series: [
      {
        type: "line",
        smooth: 0.4,
        symbol: "none",
        lineStyle: { width: 2, color: accent },
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: mode === "dark" ? "rgba(10,132,255,0.35)" : "rgba(0,113,227,0.25)" },
              { offset: 1, color: mode === "dark" ? "rgba(10,132,255,0)" : "rgba(0,113,227,0)" },
            ],
          },
        },
        data: trend.data?.map((d) => d.value) ?? [],
      },
    ],
    tooltip: { trigger: "axis", backgroundColor: mode === "dark" ? "#2C2C2E" : "#fff", borderColor: "transparent", textStyle: { color: ink } },
    textStyle: { color: ink },
  };

  return (
    <PageContainer header={{ title: "罗盘", subTitle: "搜索运营 · 行业词 · 店播视频" }}>
      <Card title="支付金额趋势（pay_amt · 近 90 天）">
        {trend.data && trend.data.length > 0 ? (
          <ReactECharts option={opt} style={{ height: 320 }} notMerge lazyUpdate />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无数据 · 等待 12:00/18:00 罗盘抓取" />
        )}
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16, marginTop: 16 }}>
        <Card title="平台优化建议">
          <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
            来自 <code style={{ fontFamily: "var(--font-mono)" }}>/compass/diagnose</code>，附"来自抖店罗盘"署名。
            <br />
            等待 18:00 罗盘抓取后填充。
          </div>
        </Card>
        <Card title="行业词排名">
          <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
            支持按 industry / category / rank_type 切换，等待 18:30 抓取后填充。
          </div>
        </Card>
        <Card title="店播视频">
          <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
            自家视频清单：播放量 · GMV · 审核状态。
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}
