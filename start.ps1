$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "未找到 .venv。请先按照 README.md 创建环境并安装 requirements.txt。"
}

& $python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
