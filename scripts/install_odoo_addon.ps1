param(
    [string]$OdooRoot = 'D:\code\programs\odoo',
    [string]$TargetAddonsDir = 'custom_addons',
    [switch]$UpgradeModule,
    [string]$Database = 'odoo_social_auto_upload',
    [string]$DbHost = '127.0.0.1',
    [int]$DbPort = 5433,
    [string]$DbUser = 'odoo',
    [string]$DbPassword = 'odoo'
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '..\odoo_addon\whatsapp_workspace'
$target = Join-Path $OdooRoot $TargetAddonsDir
$targetModule = Join-Path $target 'whatsapp_workspace'

if (!(Test-Path $source)) { throw "Source addon not found: $source" }
if (!(Test-Path $target)) { throw "Target addons dir not found: $target" }

Write-Host "[1/2] Copy addon to $targetModule"
robocopy $source $targetModule /E /XD .git __pycache__ /XF *.pyc | Out-Null

if ($UpgradeModule) {
    Write-Host "[2/2] Upgrade module whatsapp_workspace"
    $cmd = "conda run -n odoo python $OdooRoot/odoo_entrypoint.py -d $Database --db_host=$DbHost --db_port=$DbPort --db_user=$DbUser --db_password=$DbPassword --addons-path=custom_addons,addons,odoo/addons -u whatsapp_workspace --stop-after-init"
    cmd /c $cmd
}

Write-Host "Done."
