# install_vcpkg.ps1
# Attempts non-elevated clone and bootstrap of vcpkg to common locations:
#  - C:\dev\vcpkg
#  - D:\tools\vcpkg
#  - ./vcpkg (repo local)
$log = Join-Path (Get-Location) 'logs\vcpkg_install.log'
New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
"=== Timestamp: $(Get-Date -Format o)" | Out-File -FilePath $log -Encoding utf8
"=== git --version" | Add-Content $log
try { git --version 2>&1 | Out-String | Add-Content $log } catch { "git not found" | Add-Content $log; Write-Output 'git-missing'; exit 0 }
$tryPaths = @('C:\dev\vcpkg','D:\tools\vcpkg', (Join-Path (Get-Location) 'vcpkg'))
$cloned = $false
$vcpkgPath = $null
foreach ($p in $tryPaths) {
  ("--- Trying path: " + $p) | Add-Content $log
  if (Test-Path $p) {
    ("Exists: " + $p) | Add-Content $log
    $cloned = $true
    $vcpkgPath = $p
    break
  }
  try {
    ("Cloning into " + $p) | Add-Content $log
    git clone --depth 1 https://github.com/microsoft/vcpkg.git "$p" 2>&1 | Out-String | Add-Content $log
    if (Test-Path $p) {
      ("Cloned to " + $p) | Add-Content $log
      $cloned = $true
      $vcpkgPath = $p
      break
    }
  } catch {
    ("Clone error for " + $p + ": " + $_.Exception.Message) | Add-Content $log
  }
}
if (-not $cloned) {
  "Failed to clone vcpkg to any preferred location" | Add-Content $log
  Write-Output 'vcpkg-clone-failed'
  exit 0
}
"Bootstrapping vcpkg at $vcpkgPath" | Add-Content $log
$bootstrap = Join-Path $vcpkgPath 'bootstrap-vcpkg.bat'
if (Test-Path $bootstrap) {
  try {
    ("Running bootstrap: " + $bootstrap) | Add-Content $log
    & cmd /c "`"$bootstrap`"" 2>&1 | Out-String | Add-Content $log
  } catch {
    ("Bootstrap failed: " + $_.Exception.Message) | Add-Content $log
  }
} else {
  ("Bootstrap script not found at " + $bootstrap) | Add-Content $log
}
$vexe = Join-Path $vcpkgPath 'vcpkg.exe'
if (Test-Path $vexe) {
  ("vcpkg.exe found at " + $vexe) | Add-Content $log
  try { & $vexe version 2>&1 | Out-String | Add-Content $log } catch { "vcpkg version check failed" | Add-Content $log }
} else {
  "vcpkg.exe not present after bootstrap" | Add-Content $log
}
("VCPKG_ROOT=" + $vcpkgPath) | Add-Content $log
Write-Output ("Wrote vcpkg log to " + $log)