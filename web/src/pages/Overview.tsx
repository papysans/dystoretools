import { PageContainer } from "@ant-design/pro-components";
import { useQuery } from "@tanstack/react-query";
import { Empty, Tag } from "antd";
import {
  AlertOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CompassOutlined,
  FireOutlined,
  MessageOutlined,
  RiseOutlined,
  RobotOutlined,
  ScheduleOutlined,
  ShoppingCartOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { getJSON } from "../api/client";
import { Card } from "../components/Card";

interface Task { id: number; target: string; status: string; items_count: number; finished_at: string | null }
interface AlertRow { id: number; kind: string; severity: string; dispatched_at: string }
interface OrderStats { total_orders: number; total_amount_yuan: number }
interface GoodsStats { total: number; on_sale: number; low_count: number }
interface StockLevels { out: number; low: number; normal: number; over: number }

const sevTone = (s: string) =>
  s === "critical" ? "var(--critical)" : s === "warn" ? "var(--warning)" : "var(--info)";

const taskLabelMap: Record<string, string> = {
  doudian_order: "订单抓取",
  doudian_product: "商品抓取",
  doudian_stock: "库存诊断",
  doudian_comment_list: "评论抓取",
  doudian_comment_negative: "差评抓取",
  doudian_aftersale: "售后抓取",
  doudian_aftersale_counts: "售后计数",
  compass_search_core: "罗盘分析",
  compass_search_trend: "趋势抓取",
};

const taskStatusText: Record<string, string> = {
  done: "已完成",
  failed: "失败",
  queued: "排队中",
  running: "执行中",
};

const focusActions = [
  { title: "评论情绪跟进", desc: "查看负面评论与痛点聚类，快速定位体验问题。", path: "/comments", icon: <MessageOutlined /> },
  { title: "库存风险巡检", desc: "优先处理低库存、缺货与异常锁定商品。", path: "/stock", icon: <ThunderboltOutlined /> },
  { title: "智能体协作", desc: "进入 AI 智能体列表，统一管理运营自动化能力。", path: "/agents", icon: <RobotOutlined /> },
];

const trendSignals = [
  { title: "订单履约", metric: "发货与售后协同", path: "/orders", icon: <ShoppingCartOutlined /> },
  { title: "商品经营", metric: "在售商品与库存健康", path: "/goods", icon: <AppstoreOutlined /> },
  { title: "市场洞察", metric: "罗盘与同行趋势对比", path: "/compass", icon: <CompassOutlined /> },
];

function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN") : "—";
}

export default function Overview() {
  const tasks = useQuery({ queryKey: ["recent-tasks"], queryFn: () => getJSON<Task[]>("/scrape/runs", { limit: 10 }) });
  const alerts = useQuery({
    queryKey: ["recent-alerts"],
    queryFn: () => getJSON<AlertRow[]>("/alerts", { limit: 10, acked: false }),
  });
  const orderStats = useQuery<OrderStats>({
    queryKey: ["overview-order-stats"],
    queryFn: () => getJSON("/orders/stats"),
  });
  const goodsStats = useQuery<GoodsStats>({
    queryKey: ["overview-goods-stats"],
    queryFn: () => getJSON("/goods/stats"),
  });
  const stockLevels = useQuery<StockLevels>({
    queryKey: ["overview-stock-levels"],
    queryFn: () => getJSON("/stock/levels"),
  });

  const taskRows = tasks.data ?? [];
  const alertRows = alerts.data ?? [];
  const ok = taskRows.filter((t) => t.status === "done").length;
  const fail = taskRows.filter((t) => t.status === "failed").length;
  const running = taskRows.filter((t) => t.status === "running").length;
  const totalItems = taskRows.reduce((sum, row) => sum + row.items_count, 0);
  const lowStock = (stockLevels.data?.low ?? 0) + (stockLevels.data?.out ?? 0);
  const onSale = goodsStats.data?.on_sale ?? 0;

  const bannerText = fail > 0
    ? `当前有 ${fail} 个抓取任务失败，请优先检查任务队列与告警中心。`
    : running > 0
      ? `当前有 ${running} 个任务正在执行，建议关注库存、评论与售后波动。`
      : "当前抓取链路运行平稳，可继续关注评论、库存与售后变化。";

  const headlineCards = [
    {
      title: "待关注告警",
      value: alertRows.length,
      note: alertRows.length ? "存在未确认风险项" : "当前暂无活跃告警",
      accent: alertRows.length ? "var(--critical)" : "var(--success)",
      icon: <AlertOutlined />,
    },
    {
      title: "近 10 次任务成功",
      value: ok,
      note: `失败 ${fail} · 执行中 ${running}`,
      accent: "var(--accent)",
      icon: <CheckCircleOutlined />,
    },
    {
      title: "低库存/缺货",
      value: lowStock,
      note: `正常 ${stockLevels.data?.normal ?? 0} · 超量 ${stockLevels.data?.over ?? 0}`,
      accent: lowStock > 0 ? "var(--warning)" : "var(--success)",
      icon: <ThunderboltOutlined />,
    },
    {
      title: "在售商品",
      value: onSale,
      note: `总商品 ${goodsStats.data?.total ?? 0}`,
      accent: "var(--info)",
      icon: <AppstoreOutlined />,
    },
    {
      title: "累计 GMV",
      value: orderStats.data ? `¥${orderStats.data.total_amount_yuan.toFixed(2)}` : "—",
      note: `订单 ${orderStats.data?.total_orders ?? 0} 单`,
      accent: "var(--text)",
      icon: <RiseOutlined />,
    },
    {
      title: "抓取条数",
      value: totalItems,
      note: "近 10 次任务累计处理",
      accent: "var(--text)",
      icon: <ScheduleOutlined />,
    },
  ];

  return (
    <PageContainer
      header={{
        title: undefined,
        subTitle: undefined,
        breadcrumb: undefined,
      }}
    >
      <div className="overview-shell">
        <section className="overview-hero">
          <div className="overview-hero-main apple-card">
            <div className="overview-hero-copy">
              <div className="overview-eyebrow">抖店经营驾驶舱</div>
              <h2 className="overview-title">今日店铺运营概况</h2>
              <p className="overview-subtitle">参考抖店后台的首页布局，聚合订单、商品、库存、评论和任务数据，形成更适合运营人员日常查看的首页总览。</p>
            </div>
            <div className="overview-hero-banner">
              <FireOutlined />
              <span>{bannerText}</span>
            </div>
            <div className="overview-summary-grid">
              {headlineCards.map((item) => (
                <div key={item.title} className="overview-summary-card">
                  <div className="overview-summary-head">
                    <span>{item.title}</span>
                    <span className="overview-summary-icon" style={{ color: item.accent }}>{item.icon}</span>
                  </div>
                  <div className="overview-summary-value" style={{ color: item.accent }}>{item.value}</div>
                  <div className="overview-summary-note">{item.note}</div>
                </div>
              ))}
            </div>
          </div>

          <aside className="overview-side-column">
            <Card title="运营快照" className="overview-side-card" padding={18}>
              <div className="overview-side-list">
                <div className="overview-side-row">
                  <span>评论待分析</span>
                  <strong>{alertRows.length > 0 ? `${alertRows.length} 项` : "正常"}</strong>
                </div>
                <div className="overview-side-row">
                  <span>库存预警商品</span>
                  <strong>{lowStock}</strong>
                </div>
                <div className="overview-side-row">
                  <span>在售商品数</span>
                  <strong>{onSale}</strong>
                </div>
                <div className="overview-side-row">
                  <span>最新任务状态</span>
                  <strong>{taskRows[0] ? (taskStatusText[taskRows[0].status] ?? taskRows[0].status) : "暂无"}</strong>
                </div>
              </div>
            </Card>

            <Card title="重点动作" className="overview-side-card" padding={18}>
              <div className="overview-action-list">
                {focusActions.map((action) => (
                  <a key={action.title} href={action.path} className="overview-action-item">
                    <span className="overview-action-icon">{action.icon}</span>
                    <span>
                      <strong>{action.title}</strong>
                      <em>{action.desc}</em>
                    </span>
                  </a>
                ))}
              </div>
            </Card>
          </aside>
        </section>

        <section className="overview-section-grid">
          <Card
            title="经营数据"
            extra={<span className="overview-card-extra">实时汇总</span>}
            className="overview-wide-card"
            padding={0}
          >
            <div className="overview-metric-board">
              <div className="overview-metric-item">
                <span>订单总数</span>
                <strong>{orderStats.data?.total_orders ?? "—"}</strong>
                <em>累计订单规模</em>
              </div>
              <div className="overview-metric-item">
                <span>累计 GMV</span>
                <strong>{orderStats.data ? `¥${orderStats.data.total_amount_yuan.toFixed(2)}` : "—"}</strong>
                <em>订单成交金额</em>
              </div>
              <div className="overview-metric-item">
                <span>商品总数</span>
                <strong>{goodsStats.data?.total ?? "—"}</strong>
                <em>商品库规模</em>
              </div>
              <div className="overview-metric-item">
                <span>低库存数</span>
                <strong>{goodsStats.data?.low_count ?? "—"}</strong>
                <em>需及时补货处理</em>
              </div>
              <div className="overview-metric-item">
                <span>抓取成功数</span>
                <strong>{ok}</strong>
                <em>近 10 次任务完成</em>
              </div>
              <div className="overview-metric-item">
                <span>活跃告警</span>
                <strong>{alertRows.length}</strong>
                <em>等待确认与处理</em>
              </div>
            </div>
          </Card>

          <Card
            title="趋势关注"
            extra={<span className="overview-card-extra">运营建议</span>}
            className="overview-side-card"
            padding={18}
          >
            <div className="overview-trend-list">
              {trendSignals.map((signal) => (
                <a key={signal.title} href={signal.path} className="overview-trend-item">
                  <span className="overview-trend-icon">{signal.icon}</span>
                  <span>
                    <strong>{signal.title}</strong>
                    <em>{signal.metric}</em>
                  </span>
                </a>
              ))}
            </div>
          </Card>
        </section>

        <section className="overview-section-grid overview-bottom-grid">
          <Card title="最近抓取任务" extra={<span className="overview-card-extra">任务中心</span>} className="overview-wide-card" padding={0}>
            {taskRows.length ? (
              <div className="overview-list-table">
                {taskRows.slice(0, 6).map((t) => (
                  <div key={t.id} className="overview-list-row">
                    <div>
                      <div className="overview-list-title">{taskLabelMap[t.target] ?? t.target}</div>
                      <div className="overview-list-meta">
                        <ClockCircleOutlined />
                        <span>{formatDateTime(t.finished_at)}</span>
                      </div>
                    </div>
                    <div className="overview-list-right">
                      <Tag color={t.status === "done" ? "green" : t.status === "failed" ? "red" : "blue"}>
                        {taskStatusText[t.status] ?? t.status}
                      </Tag>
                      <span className="overview-list-count">{t.items_count} 条</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="overview-empty-wrap"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无任务记录" /></div>
            )}
          </Card>

          <Card title="活跃告警" extra={<span className="overview-card-extra">告警中心</span>} className="overview-side-card" padding={0}>
            {alertRows.length ? (
              <div className="overview-list-table">
                {alertRows.slice(0, 6).map((a) => (
                  <div key={a.id} className="overview-list-row overview-alert-row">
                    <div>
                      <div className="overview-list-title">{a.kind}</div>
                      <div className="overview-list-meta">
                        <ClockCircleOutlined />
                        <span>{formatDateTime(a.dispatched_at)}</span>
                      </div>
                    </div>
                    <span className="overview-severity" style={{ color: sevTone(a.severity) }}>
                      {a.severity}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="overview-empty-wrap"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无活跃告警" /></div>
            )}
          </Card>
        </section>
      </div>
    </PageContainer>
  );
}
