import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  delta?: { value: string; trend: "up" | "down" | "flat" };
  hint?: string;
  accent?: string;
}

export function KpiTile({ label, value, delta, hint, accent }: Props) {
  const trendColour =
    delta?.trend === "up" ? "var(--success)" : delta?.trend === "down" ? "var(--critical)" : "var(--text-tertiary)";
  return (
    <div className="apple-card" style={{ padding: 20 }}>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 8 }}>
        <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", color: accent ?? "var(--text)" }}>
          {value}
        </div>
        {delta && <div style={{ fontSize: 13, color: trendColour, fontWeight: 500 }}>{delta.value}</div>}
      </div>
      {hint && <div style={{ marginTop: 4, fontSize: 12, color: "var(--text-tertiary)" }}>{hint}</div>}
    </div>
  );
}
