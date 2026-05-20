#!/usr/bin/env bash
# macOS/Linux variant of launch-host-chrome.ps1.
set -euo pipefail

PROFILE_DIR="$HOME/.dystore-chrome"
PORT=9222

if [[ "$(uname)" == "Darwin" ]]; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
  CHROME="$(command -v google-chrome || command -v google-chrome-stable || true)"
fi

if [[ -z "${CHROME:-}" || ! -x "$CHROME" ]]; then
  echo "Google Chrome 未找到。请安装 https://www.google.com/chrome/" >&2
  exit 1
fi

if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "端口 $PORT 已被占用（可能已有 dystoretools Chrome 在跑）。" >&2
  exit 1
fi

"$CHROME" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-default-browser-check \
  --no-first-run \
  "https://fxg.jinritemai.com/ffa/mshop/homepage/index?from=buyin" &

echo "Chrome 已启动 (port=$PORT, profile=$PROFILE_DIR)"
echo "1. 在弹出的窗口登录抖店"
echo "2. dystoretools 设置 → 浏览器后端 → cdp"
echo "3. 任务页跑 scrape，真实数据流通"
