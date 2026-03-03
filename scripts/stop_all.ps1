param([switch]$StopMilvus)

$ErrorActionPreference = 'Continue'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidDir = Join-Path $root 'runtime\pids'

function Stop-ByPidFile($name) {
    $pidFile = Join-Path $pidDir "$name.pid"
    if (Test-Path $pidFile) {
        $pid = Get-Content -Path $pidFile -ErrorAction SilentlyContinue
        if ($pid) {
            $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($p) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped $name pid=$pid"
            }
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

Stop-ByPidFile 'rag_api'
Stop-ByPidFile 'whatsapp_web'

# Fallback cleanup for orphan cmd/node/python
Get-CimInstance Win32_Process |
Where-Object { $_.Name -match 'cmd|node|python' -and $_.CommandLine -match 'serve_rag_api:app|example.js|conda run -n whatsapp-web node example.js' } |
ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

if ($StopMilvus) {
    $milvusDir = Join-Path $root 'services\milvus'
    if (Test-Path $milvusDir) {
        Push-Location $milvusDir
        try {
            docker compose down
        } finally {
            Pop-Location
        }
        Write-Host 'Milvus docker services stopped.'
    }
}

Write-Host 'Done.'
