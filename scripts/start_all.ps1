$ErrorActionPreference = 'Stop'

& (Join-Path $PSScriptRoot 'start_milvus.ps1')
& (Join-Path $PSScriptRoot 'start_rag_api.ps1')
& (Join-Path $PSScriptRoot 'start_whatsapp_web.ps1')

Start-Sleep -Seconds 3
Write-Host 'Health checks:'
try {
    (Invoke-WebRequest -Uri 'http://127.0.0.1:18080/health' -UseBasicParsing -TimeoutSec 5).Content | Write-Host
} catch {
    Write-Host "RAG health failed: $($_.Exception.Message)"
}
try {
    (Invoke-WebRequest -Uri 'http://127.0.0.1:3000/api/account/status' -UseBasicParsing -TimeoutSec 5).StatusCode | ForEach-Object { Write-Host "Webhook status API: $_" }
} catch {
    Write-Host "Webhook health failed: $($_.Exception.Message)"
}

Write-Host 'Done.'
