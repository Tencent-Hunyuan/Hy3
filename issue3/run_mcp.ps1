# MCP 启动脚本：从同目录 .env 读环境变量后以 stdio 运行 server
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $name = $line.Substring(0, $i).Trim()
        $val = $line.Substring($i + 1).Trim()
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        Set-Item -Path "Env:$name" -Value $val
    }
}

if (-not $env:HY3_API_KEY) {
    [Console]::Error.WriteLine("HY3_API_KEY missing: copy .env.example to .env and fill in your key")
    exit 1
}
if (-not $env:HY3_MCP_ROOT) {
    $env:HY3_MCP_ROOT = $Root
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $py = "python"
}

& $py (Join-Path $Root "server.py")
