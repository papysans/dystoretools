import { useMemo, useState } from "react";
import { PageContainer, ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { Button, Drawer, Form, Input, Modal, Select, Space, Switch, Tag, message } from "antd";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { LocalUser } from "../api/auth";
import { deleteUser, listUsers, updateUser } from "../api/auth";

const PERMISSION_OPTIONS = [
  { label: "全部权限", value: "*" },
  { label: "总览查看", value: "dashboard:view" },
  { label: "订单查看", value: "orders:view" },
  { label: "商品查看", value: "goods:view" },
  { label: "库存查看", value: "stock:view" },
  { label: "评论查看", value: "comments:view" },
  { label: "售后查看", value: "aftersale:view" },
  { label: "用户查看", value: "member:view" },
  { label: "罗盘查看", value: "compass:view" },
  { label: "文案管理", value: "content:manage" },
  { label: "AI 助手", value: "chat:use" },
  { label: "智能体管理", value: "agents:manage" },
  { label: "任务管理", value: "tasks:manage" },
  { label: "告警查看", value: "alerts:view" },
  { label: "系统设置", value: "settings:view" },
];

const roleText: Record<string, string> = { admin: "管理员", operator: "运营", viewer: "只读" };

export default function AccessControl() {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["local-users"], queryFn: listUsers });
  const [editing, setEditing] = useState<LocalUser | null>(null);
  const [form] = Form.useForm();

  const columns = useMemo<ProColumns<LocalUser>[]>(
    () => [
      { title: "ID", dataIndex: "id", width: 72 },
      { title: "账号", dataIndex: "username" },
      { title: "显示名称", dataIndex: "display_name" },
      { title: "角色", dataIndex: "role", width: 110, render: (_, r) => <Tag color={r.role === "admin" ? "blue" : "default"}>{roleText[r.role]}</Tag> },
      { title: "状态", dataIndex: "enabled", width: 90, render: (_, r) => <Tag color={r.enabled ? "green" : "red"}>{r.enabled ? "启用" : "停用"}</Tag> },
      { title: "权限", dataIndex: "permissions", ellipsis: true, render: (_, r) => r.permissions.includes("*") ? "全部权限" : `${r.permissions.length} 项` },
      { title: "最后登录", dataIndex: "last_login_at", valueType: "dateTime", width: 170 },
      {
        title: "操作",
        width: 150,
        render: (_, r) => (
          <Space>
            <Button size="small" onClick={() => openEdit(r)}>编辑</Button>
            <Button size="small" danger onClick={() => Modal.confirm({ title: "删除账号", content: `确认删除 ${r.username}？`, onOk: async () => { await deleteUser(r.id); await qc.invalidateQueries({ queryKey: ["local-users"] }); } })}>删除</Button>
          </Space>
        ),
      },
    ],
    [qc],
  );

  const openEdit = (row: LocalUser) => {
    setEditing(row);
    form.setFieldsValue({ ...row, password: undefined });
  };

  const save = async () => {
    if (!editing) return;
    const values = await form.validateFields();
    const body = { ...values };
    if (!body.password) delete body.password;
    await updateUser(editing.id, body);
    message.success("权限已更新");
    setEditing(null);
    await qc.invalidateQueries({ queryKey: ["local-users"] });
  };

  return (
    <PageContainer header={{ title: "权限管理", subTitle: "本机账号、角色与功能权限" }}>
      <ProTable<LocalUser>
        rowKey="id"
        search={false}
        options={false}
        columns={columns}
        dataSource={users.data?.items ?? []}
        loading={users.isLoading}
        pagination={{ pageSize: 10 }}
      />
      <Drawer title="编辑账号权限" open={!!editing} onClose={() => setEditing(null)} width={620} extra={<Button type="primary" onClick={save}>保存</Button>}>
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="账号"><Input disabled /></Form.Item>
          <Form.Item name="display_name" label="显示名称"><Input /></Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={[{ label: "管理员", value: "admin" }, { label: "运营", value: "operator" }, { label: "只读", value: "viewer" }]} />
          </Form.Item>
          <Form.Item name="permissions" label="权限">
            <Select mode="multiple" options={PERMISSION_OPTIONS} optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name="password" label="重置密码"><Input.Password placeholder="留空则不修改" /></Form.Item>
        </Form>
      </Drawer>
    </PageContainer>
  );
}
