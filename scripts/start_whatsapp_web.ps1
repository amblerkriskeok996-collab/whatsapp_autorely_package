$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$svcDir = Join-Path $root 'services\whatsapp-web'
$logDir = Join-Path $root 'runtime\logs'
$pidDir = Join-Path $root 'runtime\pids'
New-Item -ItemType Directory -Force -Path $logDir,$pidDir | Out-Null

$outLog = Join-Path $logDir 'whatsapp_web.out.log'
$errLog = Join-Path $logDir 'whatsapp_web.err.log'
$pidFile = Join-Path $pidDir 'whatsapp_web.pid'

if (Test-Path $pidFile) {
    $oldPid = Get-Content -Path $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "WhatsApp webhook already running, pid=$oldPid"
        exit 0
    }
}

$cmd = "conda run -n whatsapp-web node example.js"
$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmd -WorkingDirectory $svcDir -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$p.Id | Set-Content -Path $pidFile
Write-Host "WhatsApp webhook started, pid=$($p.Id)"
