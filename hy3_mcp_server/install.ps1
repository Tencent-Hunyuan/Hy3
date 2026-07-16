# 一键安装脚本（Windows PowerShell）
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "[1/3] 创建虚拟环境 .venv ..."
python -m venv .venv

Write-Host "[2/3] 安装依赖 ..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip 2>$null | Out-Null
& .\.venv\Scripts\python.exe -m pip install mcp "openai>=1.40.0" pandas python-dotenv

Write-Host "[3/3] 准备 .env ..."
if (-Not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "  已生成 .env，请填入 HY3_API_KEY"
} else {
    Write-Host "  .env 已存在，跳过"
}

Write-Host ""
Write-Host "安装完成。连通性自测（PowerShell）："
Write-Host '  $env:PYTHONPATH="src"; python scripts\smoke_test.py'
