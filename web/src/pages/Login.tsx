import { useEffect, useMemo, useState } from "react";
import { Button, Form, Input, message } from "antd";
import { LockOutlined, UserOutlined, DashboardOutlined, RobotOutlined, WarningOutlined, LineChartOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { bootstrapAuth, currentUser, login, register } from "../api/auth";
import { useLocalAuthStore } from "../stores/auth";
import logo from "../assets/logo.png";
import loginBackground from "../assets/login-bj.jpg";

export default function Login() {
  const navigate = useNavigate();
  const auth = useLocalAuthStore();
  const [loading, setLoading] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const [form] = Form.useForm();

  useEffect(() => {
    bootstrapAuth().then((r) => setHasUsers(r.has_users)).catch(() => setHasUsers(true));
    currentUser()
      .then((r) => {
        auth.setUser(r.user);
        auth.setChecked(true);
        navigate("/", { replace: true });
      })
      .catch(() => auth.setChecked(true));
  }, []);

  const title = useMemo(() => (hasUsers ? "欢迎来到店灵工作台" : "初始化管理员"), [hasUsers]);

  const submit = async () => {
    const values = await form.validateFields();
    setLoading(true);
    try {
      const r = hasUsers ? await login(values) : await register(values);
      auth.setUser(r.user);
      message.success(hasUsers ? "登录成功" : "管理员已创建");
      navigate("/", { replace: true });
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "认证失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell" style={{ backgroundImage: `url(${loginBackground})` }}>
      <header className="login-header">
        <div className="login-logo">
          <img src={logo} alt="店灵AI Logo" className="login-logo-image" />
        </div>
        <h1 className="login-header-title">店灵AI</h1>
      </header>

      <main className="login-main">
        <section className="login-left">
          <div className="login-left-panel">
            <h2 className="login-hero-title">店灵 <span>AI 运营平台</span></h2>
            <p className="login-hero-subtitle">面向电商商家的一体化经营中台，聚合数据看板、智能分析与运营辅助能力。</p>

            <div className="login-features">
              <div className="login-feature-card">
                <DashboardOutlined className="login-feature-icon" />
                <h3 className="login-feature-title">经营数据总览</h3>
                <p className="login-feature-desc">统一查看订单、商品、库存、售后等核心指标，帮助运营人员快速掌握店铺状态。</p>
              </div>
              <div className="login-feature-card">
                <RobotOutlined className="login-feature-icon" />
                <h3 className="login-feature-title">AI 助手协同</h3>
                <p className="login-feature-desc">支持智能体辅助生成回复、内容与经营建议，提升日常运营效率与处理速度。</p>
              </div>
              <div className="login-feature-card">
                <WarningOutlined className="login-feature-icon" />
                <h3 className="login-feature-title">库存与告警联动</h3>
                <p className="login-feature-desc">结合库存诊断、风险预警与任务提醒，减少缺货、超卖及异常遗漏问题。</p>
              </div>
              <div className="login-feature-card">
                <LineChartOutlined className="login-feature-icon" />
                <h3 className="login-feature-title">评论与趋势分析</h3>
                <p className="login-feature-desc">围绕商品反馈、用户洞察与趋势变化进行分析，为选品和优化提供决策参考。</p>
              </div>
            </div>
          </div>
        </section>

        <section className="login-right">
          <div className="login-card">
            <h2 className="login-title">{title}</h2>
            <Form form={form} layout="vertical" onFinish={submit} requiredMark={false} size="large">
              <Form.Item name="username" rules={[{ required: true, message: "请输入账号" }]}>
                <Input prefix={<UserOutlined />} placeholder="请输入账号/手机号" autoComplete="username" />
              </Form.Item>
              {!hasUsers && (
                <Form.Item name="display_name">
                  <Input placeholder="请设置运营人员显示名称" />
                </Form.Item>
              )}
              <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }, { min: 6, message: "密码至少 6 位" }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="请输入登录密码" autoComplete={hasUsers ? "current-password" : "new-password"} />
              </Form.Item>
              <Button type="primary" block htmlType="submit" loading={loading} style={{ marginTop: 12, height: 44, fontSize: 16 }}>
                {hasUsers ? "登录" : "创建账号并登录"}
              </Button>
            </Form>
            <div className="login-form-footer">
              登录即视为您已阅读并同意 店灵工作台 <span>服务条款</span> 和 <span>隐私政策</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
