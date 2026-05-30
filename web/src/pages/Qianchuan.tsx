import { PageContainer } from "@ant-design/pro-components";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Col, Empty, Row, Select, Statistic, Table, Tag, message } from "antd";
import ReactECharts from "echarts-for-react";
import { Card } from "../components/Card";
import { qcAuthStatus, qcListAdvertisers, qcReport, qcSync, type QcReportRow } from "../api/qianchuan";

const yuan = (v: number | null | undefined) => (v == null ? "-" : `¥${v.toFixed(2)}`);
const intf = (v: number | null | undefined) => (v == null ? "-" : v.toLocaleString());

export default function Qianchuan() {
  const qc = useQueryClient();
  const [advId, setAdvId] = useState<string | undefined>(undefined);

  const status = useQuery({ queryKey: ["qc-auth"], queryFn: qcAuthStatus });
  const advertisers = useQuery({ queryKey: ["qc-advertisers"], queryFn: qcListAdvertisers });
  const report = useQuery({
    queryKey: ["qc-report", advId],
    queryFn: () => qcReport(advId, 30),
  });

  const sync = useMutation({
    mutationFn: () => qcSync(7),
    onSuccess: (r) => {
      message.success(`同步完成：${r.advertisers} 个账户，${r.rows} 行`);
      qc.invalidateQueries({ queryKey: ["qc-report"] });
      qc.invalidateQueries({ queryKey: ["qc-auth"] });
    },
    onError: (e: any) => message.error(`同步失败：${e?.response?.data?.detail || e.message}`),
  });

  const rows: QcReportRow[] = report.data ?? [];
  const totals = rows.reduce(
    (a, r) => ({
      cost: a.cost + (r.cost ?? 0),
      convert: a.convert + (r.convert_cnt ?? 0),
      gmv: a.gmv + (r.pay_order_amount ?? 0),
    }),
    { cost: 0, convert: 0, gmv: 0 },
  );

  const accent = "#0071E3";
  const muted = "#6E6E73";
  const byDate = [...rows].sort((a, b) => a.stat_date.localeCompare(b.stat_date));
  const opt = {
    grid: { left: 48, right: 20, top: 24, bottom: 32 },
    xAxis: { type: "category", data: byDate.map((r) => r.stat_date), axisLabel: { color: muted, fontSize: 11 } },
    yAxis: { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } }, axisLabel: { color: muted, fontSize: 11 } },
    series: [
      {
        type: "line", smooth: 0.4, symbol: "none", name: "消耗",
        lineStyle: { width: 2, color: accent },
        areaStyle: {
          color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [
            { offset: 0, color: "rgba(0,113,227,0.25)" },
            { offset: 1, color: "rgba(0,113,227,0)" },
          ] },
        },
        data: byDate.map((r) => r.cost ?? 0),
      },
    ],
    tooltip: { trigger: "axis" },
  };

  const columns = [
    { title: "日期", dataIndex: "stat_date" },
    { title: "账户", dataIndex: "advertiser_id" },
    { title: "消耗", dataIndex: "cost", render: yuan },
    { title: "展示", dataIndex: "show_cnt", render: intf },
    { title: "点击", dataIndex: "click_cnt", render: intf },
    { title: "转化数", dataIndex: "convert_cnt", render: intf },
    { title: "转化成本", dataIndex: "convert_cost", render: yuan },
    { title: "成交金额", dataIndex: "pay_order_amount", render: yuan },
    { title: "ROI", dataIndex: "roi", render: (v: number | null) => (v == null ? "-" : v.toFixed(2)) },
  ];

  return (
    <PageContainer
      header={{ title: "千川投放", subTitle: "巨量千川官方 API · 投放报表" }}
      extra={[
        status.data?.authorized ? (
          <Tag color="green" key="auth">已授权 · {status.data.advertiser_count} 账户</Tag>
        ) : (
          <Tag color="orange" key="auth">未授权</Tag>
        ),
        <Select
          key="adv"
          allowClear
          placeholder="全部账户"
          style={{ width: 200 }}
          value={advId}
          onChange={setAdvId}
          options={(advertisers.data ?? []).map((a) => ({ value: a.advertiser_id, label: a.advertiser_name || a.advertiser_id }))}
        />,
        <Button key="sync" type="primary" loading={sync.isPending} onClick={() => sync.mutate()}>立即同步</Button>,
      ]}
    >
      {status.data && !status.data.authorized && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="千川尚未授权"
          description="请到「设置 → 千川数据连接」完成 OAuth 授权后即可同步。"
        />
      )}

      <Card title="投放概览（近 30 天）">
        <Row gutter={16}>
          <Col span={8}><Statistic title="总消耗" value={totals.cost} precision={2} prefix="¥" /></Col>
          <Col span={8}><Statistic title="总转化数" value={totals.convert} /></Col>
          <Col span={8}><Statistic title="总成交金额" value={totals.gmv} precision={2} prefix="¥" /></Col>
        </Row>
      </Card>

      <Card title="消耗趋势" style={{ marginTop: 16 }}>
        {byDate.length > 0 ? (
          <ReactECharts option={opt} style={{ height: 300 }} notMerge lazyUpdate />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无数据 · 点右上「立即同步」或等 12:00 自动同步" />
        )}
      </Card>

      <Card title="每日明细" style={{ marginTop: 16 }}>
        <Table
          rowKey={(r) => `${r.advertiser_id}-${r.stat_date}-${r.object_id ?? ""}`}
          loading={report.isLoading}
          columns={columns}
          dataSource={rows}
          size="small"
          pagination={{ pageSize: 31 }}
        />
      </Card>
    </PageContainer>
  );
}
