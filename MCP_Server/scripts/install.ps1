$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
python -m pip install -e .
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}
Write-Host "Hy3 MCP Server installed. Edit MCP_Server\.env or set HY3_* environment variables before use."
