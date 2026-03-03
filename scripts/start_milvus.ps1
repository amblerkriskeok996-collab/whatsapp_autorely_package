$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$milvusDir = Join-Path $root 'services\milvus'
if (!(Test-Path $milvusDir)) { throw "Milvus dir not found: $milvusDir" }

Write-Host 'Starting Milvus docker services...'
Push-Location $milvusDir
try {
    docker compose up -d
} finally {
    Pop-Location
}
Write-Host 'Milvus started.'
