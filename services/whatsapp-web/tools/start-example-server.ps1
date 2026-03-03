param(
    [int]$Port = 8080,
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Ensure single instance: stop existing node processes running example.js
$existing = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -match "example\.js" }
if ($existing) {
    foreach ($proc in $existing) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Warning ("Failed to stop existing process PID {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
        }
    }
}

$selectedPort = $null
$usedPorts = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    ForEach-Object { $_.Port }

for ($p = $Port; $p -le 65535; $p++) {
    if ($usedPorts -notcontains $p) {
        $selectedPort = $p
        break
    }
}

if (-not $selectedPort) {
    throw "No available TCP port from $Port to 65535"
}

$logsDir = Join-Path $projectRoot "logs"
$stdout = Join-Path $logsDir ("example-{0}.out.log" -f $selectedPort)
$stderr = Join-Path $logsDir ("example-{0}.err.log" -f $selectedPort)

if (!(Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

if (Test-Path $stdout) { Remove-Item $stdout -Force }
if (Test-Path $stderr) { Remove-Item $stderr -Force }

$cmd = "/c call D:\apps\miniconda3\Scripts\activate.bat whatsapp-web && set SERVER_PORT=$selectedPort && node example.js"

if ($Foreground) {
    Write-Output ("Starting example.js in foreground on port {0}" -f $selectedPort)
    Write-Output ("Live logs will be printed below. URL: http://localhost:{0}/webhook/reply" -f $selectedPort)
    cmd.exe $cmd
    exit $LASTEXITCODE
}

$proc = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList $cmd `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

Start-Sleep -Seconds 6
$listener = Get-NetTCPConnection -State Listen -LocalPort $selectedPort -ErrorAction SilentlyContinue

if ($listener) {
    [pscustomobject]@{
        status = "ok"
        port = $selectedPort
        pid = $proc.Id
        stdout = $stdout
        stderr = $stderr
    } | ConvertTo-Json -Compress
    exit 0
}

[pscustomobject]@{
    status = "failed"
    port = $selectedPort
    pid = $proc.Id
    stdout = $stdout
    stderr = $stderr
} | ConvertTo-Json -Compress

if (Test-Path $stdout) {
    Write-Output "---- STDOUT ----"
    Get-Content $stdout -Tail 80
}
if (Test-Path $stderr) {
    Write-Output "---- STDERR ----"
    Get-Content $stderr -Tail 80
}

exit 1
