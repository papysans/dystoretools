import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { buildAntdTheme } from "./antd";
import { tokens } from "./tokens";

type Mode = "light" | "dark";

interface Ctx {
  mode: Mode;
  toggle: () => void;
  set: (m: Mode) => void;
}

const ThemeCtx = createContext<Ctx>({ mode: "light", toggle: () => {}, set: () => {} });

const STORAGE_KEY = "dystore.theme";

function detectInitial(): Mode {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyCssVars(mode: Mode) {
  const root = document.documentElement;
  const setVar = (name: string, value: string | number) => root.style.setProperty(name, String(value));
  setVar("--accent", tokens.accent[mode]);
  setVar("--accent-hover", tokens.accentHover[mode]);
  setVar("--bg", tokens.bg[mode]);
  setVar("--surface", tokens.surface[mode]);
  setVar("--surface-elevated", tokens.surfaceElevated[mode]);
  setVar("--surface-glass", tokens.surfaceGlass[mode]);
  setVar("--text", tokens.text[mode]);
  setVar("--text-secondary", tokens.textSecondary[mode]);
  setVar("--text-tertiary", tokens.textTertiary[mode]);
  setVar("--separator", tokens.separator[mode]);
  setVar("--border", tokens.border[mode]);
  setVar("--success", tokens.success[mode]);
  setVar("--warning", tokens.warning[mode]);
  setVar("--critical", tokens.critical[mode]);
  setVar("--shadow-sm", tokens.shadow.sm);
  setVar("--shadow-md", tokens.shadow.md);
  setVar("--shadow-lg", tokens.shadow.lg);
  setVar("--ease-standard", tokens.ease.standard);
  setVar("--ease-spring", tokens.ease.spring);
  setVar("--font-family", tokens.font.family);
  setVar("--font-mono", tokens.font.mono);
  root.dataset.theme = mode;
  root.style.colorScheme = mode;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(() => detectInitial());

  useEffect(() => {
    applyCssVars(mode);
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const antdTheme = useMemo(() => buildAntdTheme(mode), [mode]);

  const value: Ctx = useMemo(
    () => ({
      mode,
      toggle: () => setMode((m) => (m === "light" ? "dark" : "light")),
      set: setMode,
    }),
    [mode]
  );

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
