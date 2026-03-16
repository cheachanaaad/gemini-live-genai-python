$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$serverPort = 8001
$subdomain = "freshcheck-" + (Get-Random -Minimum 100000 -Maximum 999999)
$serverLog = Join-Path $projectRoot "freshcheck-server.log"
$serverErrLog = Join-Path $projectRoot "freshcheck-server.err.log"
$tunnelLog = Join-Path $projectRoot "freshcheck-tunnel.log"
$tunnelErrLog = Join-Path $projectRoot "freshcheck-tunnel.err.log"
$localTunnelBin = Join-Path $projectRoot "node_modules\.bin\lt.cmd"

function Remove-IfExists($path) {
    if (Test-Path $path) {
        try {
            Remove-Item $path -Force
        } catch {
            Clear-Content $path -ErrorAction SilentlyContinue
        }
    }
}

Remove-IfExists $serverLog
Remove-IfExists $serverErrLog
Remove-IfExists $tunnelLog
Remove-IfExists $tunnelErrLog

$existingConnections = Get-NetTCPConnection -LocalPort $serverPort -State Listen -ErrorAction SilentlyContinue
if ($existingConnections) {
    $existingPids = $existingConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $existingPids) {
        try {
            Stop-Process -Id $procId -Force
        } catch {
        }
    }
    Start-Sleep -Seconds 2
}

$envContent = Get-Content ".env" -ErrorAction Stop
$apiLine = $envContent | Where-Object { $_ -match "^GEMINI_API_KEY=" } | Select-Object -First 1
$apiKey = ""
if ($apiLine) {
    $apiKey = ($apiLine -replace "^GEMINI_API_KEY=", "").Trim()
}

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $fallbackEnv = Join-Path (Split-Path $projectRoot -Parent) "gemini-live-ephemeral-tokens-websocket\.env"
    if (Test-Path $fallbackEnv) {
        $fallbackLine = Get-Content $fallbackEnv | Where-Object { $_ -match "^GEMINI_API_KEY=" } | Select-Object -First 1
        if ($fallbackLine) {
            $apiKey = ($fallbackLine -replace "^GEMINI_API_KEY=", "").Trim()
        }
    }
}

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw "GEMINI_API_KEY is empty in .env and no fallback key was found"
}

$env:GEMINI_API_KEY = $apiKey
$env:HOST = "0.0.0.0"

$serverProcess = Start-Process `
    -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList "main.py" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $serverLog `
    -RedirectStandardError $serverErrLog `
    -WindowStyle Minimized `
    -PassThru

Start-Sleep -Seconds 4

$serverCheck = $null
try {
    $serverCheck = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$serverPort/"
} catch {
    throw "FreshCheck server failed to start. Check $serverLog and $serverErrLog"
}

if ($serverCheck.StatusCode -ne 200) {
    throw "FreshCheck server returned status $($serverCheck.StatusCode)"
}

$ltCheck = Test-Path $localTunnelBin
if (-not $ltCheck) {
    throw "localtunnel is not installed. Run npm install --save-dev localtunnel"
}

$tunnelProcess = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "`"$localTunnelBin`" --port $serverPort --subdomain $subdomain" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $tunnelLog `
    -RedirectStandardError $tunnelErrLog `
    -WindowStyle Minimized `
    -PassThru

$publicUrl = "https://$subdomain.loca.lt"
$tunnelReady = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -UseBasicParsing $publicUrl
        if ($response.StatusCode -eq 200) {
            $tunnelReady = $true
            break
        }
    } catch {
    }
}

if (-not $tunnelReady) {
    throw "HTTPS tunnel failed to start. Check $tunnelLog and $tunnelErrLog"
}

$wifiIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -like "192.168.*" -and $_.InterfaceAlias -notmatch "vEthernet|Bluetooth|Loopback"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress)

Write-Host ""
Write-Host "FreshCheck mobile dev is ready."
Write-Host "Local URL : http://127.0.0.1:$serverPort"
if ($wifiIp) {
    Write-Host "LAN URL   : http://$wifiIp`:$serverPort"
}
Write-Host "HTTPS URL : $publicUrl"
Write-Host "Server PID: $($serverProcess.Id)"
Write-Host "Tunnel PID: $($tunnelProcess.Id)"
Write-Host ""
Write-Host "Use the HTTPS URL on your phone for camera/microphone permissions."
