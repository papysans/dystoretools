import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Button, Form, Input, Space, message } from "antd";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getJSON, postJSON } from "../api/client";
import { Card } from "../components/Card";

interface Peer { id: number; shop_id: string; shop_name: string | null; follower_count: number | null }

export default function Peer() {
  const qc = useQueryClient();
  const peers = useQuery({ queryKey: ["peers"], queryFn: () => getJSON<Peer[]>("/peer/list") });

  const onAdd = async (vals: { shop_id: string; shop_name?: string }) => {
    try {
      await postJSON("/peer/watch", vals);
      message.success("已加入监控");
      qc.invalidateQueries({ queryKey: ["peers"] });
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "添加失败");
    }
  };

  return (
    <PageContainer header={{ title: "同行监控", subTitle: "公开数据 · DataSource 可切换" }}>
      <Card title="新增同行店铺">
        <Form layout="inline" onFinish={onAdd}>
          <Form.Item name="shop_id" rules={[{ required: true }]}>
            <Input placeholder="抖音店铺 ID" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="shop_name">
            <Input placeholder="店铺名（可选）" style={{ width: 220 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit">加入</Button>
        </Form>
      </Card>

      <ProTable<Peer>
        style={{ marginTop: 16 }}
        rowKey="id"
        dataSource={peers.data ?? []}
        loading={peers.isLoading}
        search={false}
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        columns={[
          { title: "店铺 ID", dataIndex: "shop_id", copyable: true },
          { title: "名称", dataIndex: "shop_name" },
          { title: "粉丝数", dataIndex: "follower_count" },
          {
            title: "操作",
            render: (_, r) => (
              <Space>
                <a onClick={() => postJSON(`/peer/${r.shop_id}/refresh`).then(() => message.info("已触发刷新"))}>刷新</a>
              </Space>
            ),
          },
        ]}
      />
    </PageContainer>
  );
}
