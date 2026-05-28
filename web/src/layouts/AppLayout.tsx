import { ProLayout } from "@ant-design/pro-components";
import backendBg from "../assets/backend.svg";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Badge, Button, Dropdown, Input, Modal, Typography, notification } from "antd";
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
  SafetyCertificateOutlined,
  LogoutOutlined,
  SearchOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { useEffect, useRef } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAuthRequiredStore, useAlertStreamStore, useTaskStreamStore } from "../stores";
import { postJSON } from "../api/client";
import { logout } from "../api/auth";
import { useLocalAuthStore } from "../stores/auth";

const menu = [
  { path: "/", name: "首页概览", icon: <DashboardOutlined />, permission: "dashboard:view" },
  {
    path: "/goods",
    name: "商品",
    icon: <AppstoreOutlined />,
    permission: "goods:view",
    routes: [
      { path: "/goods", name: "商品列表", icon: <AppstoreOutlined />, permission: "goods:view" },
      { path: "/stock", name: "库存", icon: <DatabaseOutlined />, permission: "stock:view" },
    ],
  },
  {
    path: "/orders",
    name: "订单",
    icon: <ShoppingCartOutlined />,
    permission: "orders:view",
    routes: [
      { path: "/orders", name: "订单列表", icon: <ShoppingCartOutlined />, permission: "orders:view" },
      { path: "/aftersale", name: "售后列表", icon: <CustomerServiceOutlined />, permission: "aftersale:view" },
    ],
  },
  {
    path: "/comments",
    name: "AI运营",
    icon: <RobotOutlined />,
    permission: "comments:view",
    routes: [
      { path: "/chat", name: "AI看板", icon: <RobotOutlined />, permission: "chat:use" },
      { path: "/comments", name: "评论", icon: <MessageOutlined />, permission: "comments:view" },
      { path: "/compass", name: "罗盘", icon: <CompassOutlined />, permission: "compass:view" },
      { path: "/peer", name: "同行", icon: <TeamOutlined />, permission: "dashboard:view" },
      { path: "/tasks", name: "定时任务", icon: <ScheduleOutlined />, permission: "tasks:manage" },
      { path: "/agents", name: "智能体列表", icon: <RobotOutlined />, permission: "agents:manage" },
      { path: "/content-workshop", name: "文案工坊", icon: <EditOutlined />, permission: "content:manage" },
    ],
  },
  {
    path: "/alerts",
    name: "系统管理",
    icon: <SafetyCertificateOutlined />,
    permission: "alerts:view",
    routes: [
      { path: "/alerts", name: "告警", icon: <AlertOutlined />, permission: "alerts:view" },
      { path: "/access-control", name: "权限管理", icon: <SafetyCertificateOutlined />, permission: "*" },
    ],
  },
  { path: "/settings", name: "设置", icon: <SettingOutlined />, permission: "settings:view" },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const loc = useLocation();
  const authStore = useAuthRequiredStore();
  const alertStore = useAlertStreamStore();
  const taskStore = useTaskStreamStore();
  const localAuth = useLocalAuthStore();
  const routes = menu
    .map((item) => {
      if (!item.routes) {
        return localAuth.hasPermission(item.permission) ? item : null;
      }

      const children = item.routes.filter((child) => localAuth.hasPermission(child.permission));
      if (!children.length) {
        return null;
      }

      return {
        ...item,
        routes: children,
      };
    })
    .filter(Boolean);

  useWebSocket<{ kind: string; payload?: { reason?: string } }>("auth-required", (msg) => {
    if (msg.kind === "session_expired" || msg.kind === "risk_verification_required" || msg.kind === "session_required") {
      authStore.setOpen(true, msg.kind);
    } else if (msg.kind === "session_ready") {
      authStore.setOpen(false);
      notification.success({ message: "抖店登录态已就绪", placement: "topRight" });
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

  const doLogout = async () => {
    await logout();
    localAuth.setUser(null);
    navigate("/login", { replace: true });
  };

  const bgDecoRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const FADE_START = 50;
    const FADE_END = 280;
    const MIN_OPACITY = 0.45;

    const onScroll = () => {
      const scrollY = window.scrollY;
      const ratio = Math.min(Math.max((scrollY - FADE_START) / (FADE_END - FADE_START), 0), 1);
      const opacity = 1 - ratio * (1 - MIN_OPACITY);
      if (bgDecoRef.current) bgDecoRef.current.style.opacity = String(opacity);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const shopName = localAuth.user?.display_name || localAuth.user?.username || "店灵AI工作台";

  return (
    <>
      <img ref={bgDecoRef} src={backendBg} aria-hidden="true" className="admin-bg-deco" />
      {/* Topbar rendered OUTSIDE ProLayout — full-width fixed bar like 抖店 original */}
      <header className="admin-header-shell">
        <div className="admin-topbar-left">
          <h1 className="admin-topbar-brand">店灵AI</h1>
          <div className="admin-topbar-search">
            <Input
              aria-label="智能搜索"
              placeholder="智能搜索"
              prefix={<SearchOutlined />}
              variant="borderless"
            />
          </div>
        </div>
        <div className="admin-topbar-right">
          <Badge count={alertStore.unread} offset={[-2, 2]} size="small">
            <Button
              type="text"
              shape="circle"
              className="admin-topbar-icon-btn"
              icon={<AlertOutlined />}
              onClick={() => {
                alertStore.markRead();
                navigate("/alerts");
              }}
            />
          </Badge>
          <Button type="text" shape="circle" className="admin-topbar-icon-btn" icon={<QuestionCircleOutlined />} />
          <Dropdown
            menu={{
              items: [
                { key: "user", label: <Typography.Text>{shopName}</Typography.Text>, disabled: true },
                { key: "logout", label: "退出登录", icon: <LogoutOutlined />, onClick: doLogout },
              ],
            }}
          >
            <button type="button" className="admin-topbar-avatar-btn" aria-label={shopName}>
              <span className="admin-topbar-shop-avatar admin-topbar-shop-avatar-light">
                <UserOutlined />
              </span>
            </button>
          </Dropdown>
        </div>
      </header>

      <ProLayout
        title="店灵AI"
        layout="side"
        fixSiderbar
        contentWidth="Fluid"
        siderWidth={220}
        location={{ pathname: loc.pathname }}
        route={{ routes }}
        menuItemRender={(item, dom) => <a onClick={() => navigate(item.path!)}>{dom}</a>}
        siderMenuType="sub"
        token={{
          sider: {
            colorMenuBackground: "var(--surface)",
            colorBgMenuItemSelected: "rgba(22, 119, 255, 0.10)",
          },
        }}
        ErrorBoundary={false}
        className="admin-prolayout"
        headerRender={false}
        menuHeaderRender={false}
      >
        <div className="admin-content-bg">
          <Outlet />
        </div>
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
