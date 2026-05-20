// Apple-style design tokens. Mirrored as CSS variables in global.css.
// Light + dark variants. Values pulled from Apple's Human Interface Guidelines.

export const tokens = {
  // System Blue
  accent: { light: "#0071E3", dark: "#0A84FF" },
  accentHover: { light: "#0077ED", dark: "#1A8FFF" },

  // Backgrounds
  bg: { light: "#F5F5F7", dark: "#000000" },           // page
  surface: { light: "#FFFFFF", dark: "#1C1C1E" },      // cards
  surfaceElevated: { light: "#FFFFFF", dark: "#2C2C2E" },
  surfaceGlass: { light: "rgba(255,255,255,0.72)", dark: "rgba(28,28,30,0.72)" },

  // Text
  text: { light: "#1D1D1F", dark: "#F5F5F7" },
  textSecondary: { light: "#6E6E73", dark: "#98989D" },
  textTertiary: { light: "#86868B", dark: "#6E6E73" },

  // Separators & borders
  separator: { light: "rgba(60,60,67,0.12)", dark: "rgba(84,84,88,0.6)" },
  border: { light: "rgba(0,0,0,0.06)", dark: "rgba(255,255,255,0.08)" },

  // Semantic
  success: { light: "#34C759", dark: "#30D158" },
  warning: { light: "#FF9F0A", dark: "#FF9F0A" },
  critical: { light: "#FF3B30", dark: "#FF453A" },
  info: { light: "#5AC8FA", dark: "#64D2FF" },

  // Radius (continuous corners feel)
  radius: { xs: 6, sm: 8, md: 12, lg: 16, xl: 20, "2xl": 28 },

  // Spacing scale (HIG)
  space: { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48 },

  // Soft multi-layer shadows
  shadow: {
    sm: "0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
    md: "0 4px 6px rgba(0,0,0,0.04), 0 10px 15px rgba(0,0,0,0.06)",
    lg: "0 10px 25px rgba(0,0,0,0.06), 0 20px 40px rgba(0,0,0,0.1)",
  },

  // Motion
  ease: {
    standard: "cubic-bezier(0.4, 0, 0.2, 1)",
    spring: "cubic-bezier(0.16, 1, 0.3, 1)",
  },
  duration: { fast: 150, base: 200, slow: 350 },

  // Typography
  font: {
    family:
      `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Inter", "PingFang SC", "Helvetica Neue", Helvetica, Arial, sans-serif`,
    mono:
      `"SF Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`,
  },
} as const;
