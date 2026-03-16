$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$fallbackEnv = Join-Path (Split-Path $projectRoot -Parent) "gemini-live-ephemeral-tokens-websocket\.env"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found: $pythonExe"
}

if (-not $env:GEMINI_API_KEY -and (Test-Path $fallbackEnv)) {
    $apiKeyLine = Get-Content $fallbackEnv | Select-String '^GEMINI_API_KEY=' | Select-Object -First 1
    if ($apiKeyLine) {
        $env:GEMINI_API_KEY = ($apiKeyLine.Line -split '=', 2)[1]
    }
}

if (-not $env:GEMINI_API_KEY) {
    throw "GEMINI_API_KEY is not set. Add it to this shell or to $fallbackEnv"
}

$env:HOST = "0.0.0.0"
$env:PORT = "8001"
$env:LOG_LEVEL = "DEBUG"

Write-Host ""
Write-Host "FreshCheck Debug Server"
Write-Host "Path : $projectRoot"
Write-Host "URL  : http://127.0.0.1:8001"
Write-Host "Logs : DEBUG"
Write-Host ""
Write-Host "If port 8001 is busy, stop the old process first."
Write-Host ""

Push-Location $projectRoot
try {
    & $pythonExe "main.py"
}
finally {
    Pop-Location
}
