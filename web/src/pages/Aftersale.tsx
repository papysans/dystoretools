import { PageContainer } from "@ant-design/pro-components";
import { Card } from "../components/Card";

const DIMS: { key: string; label: string; tone: string }[] = [
  { key: "approaching_deadline_audit", label: "即将超时", tone: "var(--critical)" },
  { key: "urge_audit", label: "用户催办", tone: "var(--warning)" },
  { key: "refund_audit", label: "退款待审", tone: "var(--info)" },
  { key: "return_audit", label: "退货待审", tone: "var(--info)" },
  { key: "exchange_audit", label: "换货待审", tone: "var(--info)" },
  { key: "resend_audit", label: "补发待审", tone: "var(--info)" },
  { key: "arbitrate_pending", label: "仲裁待处理", tone: "var(--critical)" },
  { key: "arbitrate_pending_evidence", label: "仲裁待举证", tone: "var(--critical)" },
];

export default function Aftersale() {
  return (
    <PageContainer header={{ title: "售后", subTitle: "18 维度即时计数" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        {DIMS.map((d) => (
          <div key={d.key} className="apple-card" style={{ padding: 16 }}>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{d.label}</div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginTop: 6 }}>
              <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>—</div>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: d.tone }} />
            </div>
            <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>{d.key}</div>
          </div>
        ))}
      </div>
      <Card title="售后单列表" style={{ marginTop: 16 }}>
        <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
          等待 <code style={{ fontFamily: "var(--font-mono)" }}>/after_sale/pc/list</code> 抓取后填充。
        </div>
      </Card>
    </PageContainer>
  );
}
