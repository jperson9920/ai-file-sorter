$repoRoot = Get-Location
$log = Join-Path $repoRoot 'logs\vs_install.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"=== Download check started at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
$bootstrap = 'C:\Temp\vs_Community.exe'
$uri = 'https://aka.ms/vs/17/release/vs_Community.exe'
if (-Not (Test-Path $bootstrap)) {
  "Bootstrapper not found; downloading $uri" | Tee-Object -FilePath $log -Append
  try {
    Invoke-WebRequest -Uri $uri -OutFile $bootstrap -ErrorAction Stop | Tee-Object -FilePath $log -Append
    "Download succeeded" | Tee-Object -FilePath $log -Append
  } catch {
    "Download failed: $($_.Exception.Message)" | Tee-Object -FilePath $log -Append
  }
} else {
  "Bootstrapper exists at $bootstrap" | Tee-Object -FilePath $log -Append
}
try {
  Get-FileHash -Path $bootstrap -Algorithm SHA256 | Out-String | Tee-Object -FilePath $log -Append
} catch {
  "Get-FileHash failed: $($_.Exception.Message)" | Tee-Object -FilePath $log -Append
}
"=== Download check finished at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append