import { ProLayout } from "@ant-design/pro-components";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Badge, Button, Modal, Space, notification } from "antd";
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  MessageOutlined,
  CustomerServiceOutlined,
  UserOutlined,
  CompassOutlined,
  EditOutlined,
  ScheduleOutlined,
  AlertOutlined,
  TeamOutlined,
  SettingOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAuthRequiredStore, useAlertStreamStore, useTaskStreamStore } from "../stores";
import { postJSON } from "../api/client";
import { ThemeToggle } from "../components/ThemeToggle";

const menu = [
  { path: "/chat", name: "AI 助手", icon: <RobotOutlined /> },
  { path: "/", name: "总览", icon: <DashboardOutlined /> },
  { path: "/orders", name: "订单", icon: <ShoppingCartOutlined /> },
  { path: "/goods", name: "商品", icon: <AppstoreOutlined /> },
  { path: "/stock", name: "库存", icon: <DatabaseOutlined /> },
  { path: "/comments", name: "评论", icon: <MessageOutlined /> },
  { path: "/aftersale", name: "售后", icon: <CustomerServiceOutlined /> },
  { path: "/member", name: "用户", icon: <UserOutlined /> },
  { path: "/compass", name: "罗盘", icon: <CompassOutlined /> },
  { path: "/content-workshop", name: "文案工坊", icon: <EditOutlined /> },
  { path: "/peer", name: "同行", icon: <TeamOutlined /> },
  { path: "/tasks", name: "任务", icon: <ScheduleOutlined /> },
  { path: "/alerts", name: "告警", icon: <AlertOutlined /> },
  { path: "/settings", name: "设置", icon: <SettingOutlined /> },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const loc = useLocation();
  const authStore = useAuthRequiredStore();
  const alertStore = useAlertStreamStore();
  const taskStore = useTaskStreamStore();

  useWebSocket<{ kind: string; payload?: { reason?: string } }>("auth-required", (msg) => {
    if (msg.kind === "session_expired" || msg.kind === "risk_verification_required" || msg.kind === "session_required") {
      authStore.setOpen(true, msg.kind);
    } else if (msg.kind === "session_ready") {
      authStore.setOpen(false);
      notification.success({ message: "登录态已就绪", placement: "topRight" });
    }
  });

  useWebSocket<{ kind: string; target?: string; items?: number; error?: string; run_id?: number }>("tasks", (m) => {
    taskStore.push(m);
    if (m.kind === "task_failed") {
      notification.error({ message: `任务失败: ${m.target}`, description: m.error, placement: "topRight" });
    }
  });

  useWebSocket<{ id?: number; kind: string; severity?: string; payload?: Record<string, unknown>; dispatched_at?: string }>(
    "alerts",
    (m) => {
      if (m.kind === "alert_acked") return;
      if (m.id && m.severity && m.dispatched_at) {
        alertStore.push({ id: m.id, kind: m.kind, severity: m.severity, payload: m.payload, dispatched_at: m.dispatched_at });
      }
    }
  );

  return (
    <>
      <ProLayout
        title="dystoretools"
        layout="mix"
        fixSiderbar
        fixedHeader
        contentWidth="Fluid"
        siderWidth={232}
        location={{ pathname: loc.pathname }}
        route={{ routes: menu }}
        menuItemRender={(item, dom) => <a onClick={() => navigate(item.path!)}>{dom}</a>}
        siderMenuType="sub"
        token={{
          sider: {
            colorMenuBackground: "transparent",
            colorBgMenuItemSelected: "transparent",
          },
          header: {
            colorBgHeader: "transparent",
          },
        }}
        ErrorBoundary={false}
        className="apple-prolayout"
        headerRender={(_, defaultDom) => (
          <div className="glass-topbar" style={{ width: "100%" }}>
            {defaultDom}
          </div>
        )}
        menuHeaderRender={(_logo, title) => (
          <Space size={10}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, var(--accent) 0%, #00C7FF 100%)",
                boxShadow: "0 4px 12px rgba(0,113,227,0.3)",
              }}
            />
            <span style={{ fontWeight: 600, letterSpacing: "-0.01em" }}>{title}</span>
          </Space>
        )}
        rightContentRender={() => (
          <Space size={4}>
            <Badge count={alertStore.unread} offset={[-4, 4]} size="small">
              <Button
                type="text"
                shape="circle"
                icon={<AlertOutlined />}
                onClick={() => {
                  alertStore.markRead();
                  navigate("/alerts");
                }}
              />
            </Badge>
            <ThemeToggle />
          </Space>
        )}
      >
        <Outlet />
      </ProLayout>

      <Modal
        title="需要登录抖店"
        open={authStore.open}
        closable={false}
        maskClosable={false}
        centered
        width={420}
        footer={
          <Button
            type="primary"
            block
            size="large"
            onClick={async () => {
              try {
                await postJSON("/auth/open-login-window");
              } catch {
                /* ignore */
              }
            }}
          >
            去浏览器完成登录
          </Button>
        }
      >
        <p style={{ marginBottom: 8 }}>系统已暂停抓取任务，等待你完成登录或安全验证。</p>
        <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>原因：{authStore.reason}</p>
      </Modal>
    </>
  );
}
