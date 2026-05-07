# run_analytics.ps1 — start the analytics HTTP server on Windows
# Run from PowerShell in the ApexNotification directory:
#   .\run_analytics.ps1

Set-Location $PSScriptRoot

# Load .env if present
if (Test-Path .env) {
    Get-Content .env | Where-Object { $_ -notmatch "^#" -and $_.Trim() -ne "" } | ForEach-Object {
        $parts = $_ -split "=", 2
        if ($parts.Count -eq 2) { [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim()) }
    }
}

$port = if ($env:ANALYTICS_PORT) { $env:ANALYTICS_PORT } else { "8080" }
$host_addr = if ($env:ANALYTICS_HOST) { $env:ANALYTICS_HOST } else { "0.0.0.0" }

Write-Host "=== ApexNotification Analytics Server ===" -ForegroundColor Cyan
Write-Host "Listening on ${host_addr}:${port}" -ForegroundColor Green
Write-Host ""

C:\Python310\python.exe analytics_server.py --host $host_addr --port $port
