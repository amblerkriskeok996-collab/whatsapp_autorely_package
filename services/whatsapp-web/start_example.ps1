$ErrorActionPreference = "Stop"
Set-Location "D:\code\programs\Whatsapp\whatsapp-web"
$logOut = "example.runtime.out.log"
$logErr = "example.runtime.err.log"
$pidFile = "example.runtime.pid"
if (Test-Path $logOut) { Remove-Item $logOut -Force }
if (Test-Path $logErr) { Remove-Item $logErr -Force }
$proc = Start-Process -FilePath "conda" -ArgumentList @("run","-n","whatsapp-web","node","example.js") -WorkingDirectory (Get-Location).Path -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
"PID=$($proc.Id)"
