$log = Join-Path (Get-Location) 'logs\env_check_vs_nvcc.txt'
New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
"=== Timestamp: $(Get-Date -Format o)" | Out-File -FilePath $log -Encoding utf8
"=== Get-Command cl.exe" | Add-Content $log
try { Get-Command cl.exe -ErrorAction Stop | Out-String | Add-Content $log } catch { "cl.exe not found" | Add-Content $log }
"=== where cl.exe" | Add-Content $log
try { & where.exe cl.exe 2>&1 | Out-String | Add-Content $log } catch { "where.exe failed" | Add-Content $log }
"=== vswhere" | Add-Content $log
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
  & $vswhere -all -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath,installationVersion | Out-String | Add-Content $log
} else {
  "vswhere not found at expected path ($vswhere)" | Add-Content $log
}
"=== nvcc" | Add-Content $log
try { Get-Command nvcc -ErrorAction Stop | Out-String | Add-Content $log; (& nvcc --version) 2>&1 | Out-String | Add-Content $log } catch { "nvcc not found" | Add-Content $log }
"=== CUDA install dirs" | Add-Content $log
$cudaRoot = 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA'
if (Test-Path $cudaRoot) { Get-ChildItem $cudaRoot -ErrorAction SilentlyContinue | Select-Object FullName,Name | Out-String | Add-Content $log } else { "CUDA folder not found at $cudaRoot" | Add-Content $log }
"=== vcpkg checks (common locations)" | Add-Content $log
# compute repository vcpkg path separately to avoid parser issues when using expressions inside array literals
$repoVcpkg = Join-Path (Get-Location) 'vcpkg'
$paths = @('C:\dev\vcpkg','D:\tools\vcpkg',$repoVcpkg)
foreach ($p in $paths) {
  ("Checking " + $p) | Add-Content $log
  if (Test-Path $p) {
    Get-ChildItem $p -Force | Select-Object FullName | Out-String | Add-Content $log
  } else {
    ("Not found: " + $p) | Add-Content $log
  }
}
"=== End of checks" | Add-Content $log
Write-Output "Wrote environment check to $log"