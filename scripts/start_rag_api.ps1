$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$svcDir = Join-Path $root 'services\milvus'
$logDir = Join-Path $root 'runtime\logs'
$pidDir = Join-Path $root 'runtime\pids'
New-Item -ItemType Directory -Force -Path $logDir,$pidDir | Out-Null

$outLog = Join-Path $logDir 'rag_api.out.log'
$errLog = Join-Path $logDir 'rag_api.err.log'
$pidFile = Join-Path $pidDir 'rag_api.pid'

if (Test-Path $pidFile) {
    $oldPid = Get-Content -Path $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "RAG API already running, pid=$oldPid"
        exit 0
    }
}

$cmd = "conda run -n milvus uvicorn scripts.serve_rag_api:app --host 0.0.0.0 --port 18080"
$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmd -WorkingDirectory $svcDir -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
$p.Id | Set-Content -Path $pidFile
Write-Host "RAG API started, pid=$($p.Id)"
