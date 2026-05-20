# Launch a dedicated Chrome instance with remote debugging enabled.
# dystoretools docker container connects to this Chrome via CDP at host.docker.internal:9222.
#
# Usage:
#   pwsh scripts/launch-host-chrome.ps1
#
# First time:
#   1. Run this script (this opens a fresh Chrome with a separate profile dir)
#   2. Inside that Chrome, navigate to https://fxg.jinritemai.com and log in (handle OTP if asked)
#   3. Leave the Chrome window OPEN (it can be minimised)
#   4. In dystoretools Settings, switch "浏览器后端" → cdp → save
#   5. Trigger any scrape — real data flows
#
# Subsequent times: just run this script. Cookies persist in the profile dir.

$ProfileDir = "$env:USERPROFILE\.dystore-chrome"
$Port = 9222
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $ChromePath)) {
    $ChromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}
if (-not (Test-Path $ChromePath)) {
    Write-Error "Google Chrome not found. Install from https://www.google.com/chrome/"
    exit 1
}

# Refuse if something is already listening on $Port — likely a previous instance still alive
$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "端口 $Port 已被占用，可能已有一个 dystoretools Chrome 在运行。"
    Write-Host "若要新开，先关闭旧的：taskkill /F /PID <pid>"
    exit 1
}

Write-Host "启动专用 Chrome（user-data-dir=$ProfileDir, debug-port=$Port）..."
Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-default-browser-check",
    "--no-first-run",
    "https://fxg.jinritemai.com/ffa/mshop/homepage/index?from=buyin"
)

Write-Host ""
Write-Host "Chrome 已启动。"
Write-Host "  1. 在弹出的窗口里登录抖店（首次会需要短信验证码）"
Write-Host "  2. dystoretools 设置页 → 浏览器后端 → cdp → 保存"
Write-Host "  3. 任务页触发任何 scrape，真实数据就开始流"
