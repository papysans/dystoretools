import { PageContainer } from "@ant-design/pro-components";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { getJSON } from "../api/client";
import { KpiTile } from "../components/KpiTile";
import { Card } from "../components/Card";

interface AggItem {
  index_name: string;
  index_display: string;
  value: number;
  unit: string;
  change_value: number;
  peer_excellent: number;
}

interface DailyItem {
  date: string;
  metric: string;
  value: number;
}

interface HistItem {
  bucket: string;
  value: number;
  dim: string;
}

interface DashboardResponse {
  agg: AggItem[];
  daily: DailyItem[];
  hist: HistItem[];
}

function formatValue(value: number, unit: string): string {
  if (unit === "price") {
    return `¥${value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (unit === "ratio") {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toLocaleString("zh-CN");
}

function buildDelta(change: number): { value: string; trend: "up" | "down" | "flat" } {
  if (change > 0) return { value: `▲ ${(change * 100).toFixed(1)}%`, trend: "up" };
  if (change < 0) return { value: `▼ ${(Math.abs(change) * 100).toFixed(1)}%`, trend: "down" };
  return { value: "持平", trend: "flat" };
}

export default function Member() {
  const dashboard = useQuery<DashboardResponse>({
    queryKey: ["member-dashboard"],
    queryFn: () => getJSON("/member/dashboard"),
  });

  const agg = dashboard.data?.agg ?? [];
  const daily = dashboard.data?.daily ?? [];
  const hist = dashboard.data?.hist ?? [];
  const topAgg = agg.slice(0, 4);

  const dailyMetric = daily[0]?.metric ?? "";
  const isPriceMetric = dailyMetric.includes("order_amt");

  const lineOption = {
    tooltip: {
      trigger: "axis",
      formatter: isPriceMetric ? "{b}<br/>¥{c}" : "{b}<br/>{c}",
    },
    grid: { left: 48, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: "category",
      data: daily.map((d) => d.date),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        smooth: true,
        data: daily.map((d) => d.value),
        itemStyle: { color: "#1677ff" },
        areaStyle: { color: "rgba(22, 119, 255, 0.15)" },
      },
    ],
  };

  const barOption = {
    tooltip: { trigger: "axis", formatter: "{b}: {c}" },
    grid: { left: 48, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: "category",
      data: hist.map((h) => h.bucket),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: "value" },
    series: [
      {
        type: "bar",
        data: hist.map((h) => h.value),
        itemStyle: { color: "#52c41a", borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  return (
    <PageContainer header={{ title: "用户运营", subTitle: "会员看板 · 受众画像" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        {topAgg.length === 0
          ? Array.from({ length: 4 }).map((_, i) => (
              <KpiTile key={i} label="—" value="—" />
            ))
          : topAgg.map((item) => (
              <KpiTile
                key={item.index_name}
                label={item.index_display}
                value={formatValue(item.value, item.unit)}
                delta={buildDelta(item.change_value)}
              />
            ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16, marginTop: 16 }}>
        <Card title={`日趋势 · ${dailyMetric}`}>
          {daily.length === 0 ? (
            <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0", textAlign: "center" }}>
              暂无数据
            </div>
          ) : (
            <ReactECharts option={lineOption} style={{ height: 280 }} notMerge lazyUpdate />
          )}
        </Card>
        <Card title="受众画像">
          {hist.length === 0 ? (
            <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: "32px 0", textAlign: "center" }}>
              暂无数据
            </div>
          ) : (
            <ReactECharts option={barOption} style={{ height: 280 }} notMerge lazyUpdate />
          )}
        </Card>
      </div>
    </PageContainer>
  );
}
