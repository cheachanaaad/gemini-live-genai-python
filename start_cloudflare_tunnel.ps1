$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$cloudflared = "C:\Users\chae\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
    throw "cloudflared.exe not found at $cloudflared"
}

$serverCheck = $null
try {
    $serverCheck = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8001/"
} catch {
    throw "FreshCheck server is not running on http://127.0.0.1:8001"
}

if ($serverCheck.StatusCode -ne 200) {
    throw "FreshCheck server returned status $($serverCheck.StatusCode)"
}

Write-Host ""
Write-Host "Starting Cloudflare Quick Tunnel for FreshCheck..."
Write-Host "Keep this terminal open while testing on mobile."
Write-Host ""

& $cloudflared tunnel --url http://127.0.0.1:8001
