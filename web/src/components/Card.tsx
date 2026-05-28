import type { CSSProperties, ReactNode } from "react";

interface Props {
  children: ReactNode;
  title?: ReactNode;
  extra?: ReactNode;
  padding?: number;
  interactive?: boolean;
  style?: CSSProperties;
  className?: string;
  onClick?: () => void;
}

export function Card({ children, title, extra, padding = 20, interactive, style, className, onClick }: Props) {
  return (
    <div
      className={`apple-card ${interactive ? "apple-card-interactive" : ""} ${className ?? ""}`}
      style={style}
      onClick={onClick}
    >
      {(title || extra) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: `${padding}px ${padding}px 0`,
            gap: 12,
          }}
        >
          {title && <div style={{ fontWeight: 600, fontSize: 15, letterSpacing: "-0.01em" }}>{title}</div>}
          {extra}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
    </div>
  );
}
