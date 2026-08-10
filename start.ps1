$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "未找到 .venv。请先按照 README.md 创建环境并安装 requirements.txt。"
}

# Listen on all local network interfaces so other devices on the LAN can connect.
& $python -m uvicorn server.app:app --host 0.0.0.0 --port 8001 --reload
