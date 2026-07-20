# Hy3 Deep Research MCP - Windows one-click install (ASCII-only; avoids PS encoding issues)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Test-Py([string]$Exe, [string[]]$PrefixArgs = @()) {
  & $Exe @PrefixArgs -c "import sys; assert sys.version_info >= (3,10)" 2>$null
  return ($LASTEXITCODE -eq 0)
}

$PyExe = $null
$PyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  if (Test-Py "py" @("-3")) { $PyExe = "py"; $PyArgs = @("-3") }
}
if (-not $PyExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
  if (Test-Py "python") { $PyExe = "python" }
}
if (-not $PyExe) {
  throw "Python >= 3.10 required. Install from python.org and add to PATH."
}

Write-Host "==> $PyExe $($PyArgs -join ' ') | $Root"
if (-not (Test-Path ".venv")) {
  & $PyExe @PyArgs -m venv .venv
}

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPy -m pip install -U pip setuptools wheel | Out-Null
& $VenvPy -m pip install -r (Join-Path $Root "requirements.txt")
& $VenvPy -m pip install -e $Root | Out-Null

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

$Gen = Join-Path $Root "configs\generated"
New-Item -ItemType Directory -Force -Path $Gen | Out-Null
$cfg = @{
  mcpServers = @{
    "hy3-deep-research" = @{
      command = $VenvPy
      args    = @((Join-Path $Root "server.py"))
      env     = @{
        HY3_API_KEY  = "sk-xxxxxxxx"
        HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
        HY3_MODEL    = "hy3"
      }
    }
  }
} | ConvertTo-Json -Depth 6

$cfg | Set-Content -Encoding utf8 (Join-Path $Gen "cursor.mcp.json")
$cfg | Set-Content -Encoding utf8 (Join-Path $Gen "workbuddy.mcp.json")

& $VenvPy -c "import server; print('ok', server.mcp.name)"
Write-Host "Done. Edit .env (HY3_API_KEY), then use configs\generated\workbuddy.mcp.json in WorkBuddy."
