import { createContext, useContext, useEffect, useMemo } from "react";
import type { ReactNode } from "react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { buildAntdTheme } from "./antd";
import { tokens } from "./tokens";

type ThemeContextValue = {
  mode: "light";
};

const ThemeCtx = createContext<ThemeContextValue>({ mode: "light" });

function applyCssVars() {
  const root = document.documentElement;
  const setVar = (name: string, value: string | number) => root.style.setProperty(name, String(value));
  setVar("--accent", tokens.accent);
  setVar("--accent-hover", tokens.accentHover);
  setVar("--bg", tokens.bg);
  setVar("--surface", tokens.surface);
  setVar("--surface-elevated", tokens.surfaceElevated);
  setVar("--surface-glass", tokens.surfaceGlass);
  setVar("--text", tokens.text);
  setVar("--text-secondary", tokens.textSecondary);
  setVar("--text-tertiary", tokens.textTertiary);
  setVar("--separator", tokens.separator);
  setVar("--border", tokens.border);
  setVar("--success", tokens.success);
  setVar("--warning", tokens.warning);
  setVar("--critical", tokens.critical);
  setVar("--shadow-sm", tokens.shadow.sm);
  setVar("--shadow-md", tokens.shadow.md);
  setVar("--shadow-lg", tokens.shadow.lg);
  setVar("--ease-standard", tokens.ease.standard);
  setVar("--ease-spring", tokens.ease.spring);
  setVar("--font-family", tokens.font.family);
  setVar("--font-mono", tokens.font.mono);
  root.style.colorScheme = "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    applyCssVars();
  }, []);

  const antdTheme = useMemo(() => buildAntdTheme(), []);
  const value = useMemo<ThemeContextValue>(() => ({ mode: "light" }), []);

  return (
    <ThemeCtx.Provider value={value}>
      <ConfigProvider locale={zhCN} theme={antdTheme}>
        {children}
      </ConfigProvider>
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeCtx);
}
