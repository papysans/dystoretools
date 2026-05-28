// Apple-style design tokens. Mirrored as CSS variables in global.css.
// Fixed light-only theme.

export const tokens = {
  accent: "#0071E3",
  accentHover: "#0077ED",
  bg: "#F5F5F7",
  surface: "#FFFFFF",
  surfaceElevated: "#FFFFFF",
  surfaceGlass: "rgba(255,255,255,0.72)",
  text: "#1D1D1F",
  textSecondary: "#6E6E73",
  textTertiary: "#86868B",
  separator: "rgba(60,60,67,0.12)",
  border: "rgba(0,0,0,0.06)",
  success: "#34C759",
  warning: "#FF9F0A",
  critical: "#FF3B30",
  info: "#5AC8FA",
  radius: { xs: 6, sm: 8, md: 12, lg: 16, xl: 20, "2xl": 28 },
  space: { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48 },
  shadow: {
    sm: "0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
    md: "0 4px 6px rgba(0,0,0,0.04), 0 10px 15px rgba(0,0,0,0.06)",
    lg: "0 10px 25px rgba(0,0,0,0.06), 0 20px 40px rgba(0,0,0,0.1)",
  },
  ease: {
    standard: "cubic-bezier(0.4, 0, 0.2, 1)",
    spring: "cubic-bezier(0.16, 1, 0.3, 1)",
  },
  duration: { fast: 150, base: 200, slow: 350 },
  font: {
    family:
      `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "PingFang SC", "Helvetica Neue", Helvetica, Arial, sans-serif`,
    mono:
      `"SF Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`,
  },
} as const;
