import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag } from "antd";
import { getJSON } from "../api/client";

interface Comment {
  id: number;
  comment_id: string;
  goods_id: string;
  rating: number;
  content: string;
  user_nick: string;
  sentiment: string | null;
  pain_points: { tag: string; evidence: string }[];
}

const sentimentDot = (s: string | null) => {
  const colour = s === "positive" ? "var(--success)" : s === "negative" ? "var(--critical)" : "var(--text-tertiary)";
  const label = s === "positive" ? "正面" : s === "negative" ? "负面" : "中性";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 500 }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: colour }} />
      {label}
    </span>
  );
};

export default function Comments() {
  return (
    <PageContainer header={{ title: "评论", subTitle: "AI 情感判定 · 痛点聚类" }}>
      <ProTable<Comment>
        rowKey="id"
        ghost
        cardProps={{ bodyStyle: { padding: 0 } }}
        options={false}
        search={{ filterType: "light" }}
        request={async ({ current = 1, pageSize = 20, sentiment }) => {
          const r = await getJSON<{ items: Comment[] }>("/comments", { page: current - 1, page_size: pageSize, sentiment });
          return { data: r.items, success: true };
        }}
        columns={[
          { title: "商品", dataIndex: "goods_id", width: 160, search: false },
          { title: "评分", dataIndex: "rating", width: 60, search: false, render: (r) => <span style={{ fontVariantNumeric: "tabular-nums" }}>{r ?? "-"}</span> },
          {
            title: "情感",
            dataIndex: "sentiment",
            valueEnum: { positive: "positive", neutral: "neutral", negative: "negative" },
            render: (_, r) => sentimentDot(r.sentiment),
          },
          {
            title: "痛点",
            dataIndex: "pain_points",
            search: false,
            render: (_, r) =>
              r.pain_points?.length
                ? r.pain_points.map((p) => (
                    <Tag key={p.tag} color="default" style={{ marginInlineEnd: 4 }}>
                      {p.tag}
                    </Tag>
                  ))
                : <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>—</span>,
          },
          { title: "内容", dataIndex: "content", ellipsis: true, search: false },
        ]}
      />
    </PageContainer>
  );
}
