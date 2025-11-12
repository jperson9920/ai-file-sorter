$repoRoot = Get-Location
$log = Join-Path $repoRoot 'logs\vs_install.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"=== Installer run started at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
$exe = 'C:\Temp\vs_Community.exe'
if (-not (Test-Path $exe)) {
  "Installer not found at $exe" | Tee-Object -FilePath $log -Append
  exit 3
}
$args = @('--add','Microsoft.VisualStudio.Workload.NativeDesktop','--includeRecommended','--quiet','--wait','--norestart')
try {
  & $exe @args 2>&1 | Tee-Object -FilePath $log -Append
  $ecode = $LASTEXITCODE
  "=== Installer exitcode: $ecode" | Tee-Object -FilePath $log -Append
} catch {
  "Installer invocation failed: $($_.Exception.Message)" | Tee-Object -FilePath $log -Append
  $_ | Out-String | Tee-Object -FilePath $log -Append
  exit 4
}
"=== Installer run finished at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append