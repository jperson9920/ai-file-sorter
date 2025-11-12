$repo = Get-Location
$log = Join-Path $repo 'logs\vs_install.log'
$envlog = Join-Path $repo 'logs\env_check_vs_nvcc.txt'
"=== Dev shell verification started at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append

$startPaths = @($env:ProgramData + '\Microsoft\Windows\Start Menu\Programs', $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs')
foreach ($p in $startPaths) {
  if (Test-Path $p) {
    Get-ChildItem -Path $p -Recurse -Filter '*Native Tools*' -ErrorAction SilentlyContinue | Select-Object FullName | Out-String | Tee-Object -FilePath $log -Append
  } else {
    ("Not found start path: " + $p) | Tee-Object -FilePath $log -Append
  }
}

$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
  $inst = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  ("vswhere installationPath: " + $inst) | Tee-Object -FilePath $log -Append
} else {
  ("vswhere not found at expected path ($vswhere)") | Tee-Object -FilePath $log -Append
  $inst = $null
}

if ($inst) {
  $vcvars = Join-Path $inst 'VC\Auxiliary\Build\vcvars64.bat'
  ("vcvars path: " + $vcvars) | Tee-Object -FilePath $log -Append
} else {
  ("cannot determine vcvars path since vswhere didn't find installation") | Tee-Object -FilePath $log -Append
  $vcvars = $null
}

if ($vcvars -and (Test-Path $vcvars)) {
  ("Launching Developer shell using vcvars64.bat and running env_check.ps1 at " + (Get-Date -Format o)) | Tee-Object -FilePath $log -Append
  $cmd = "call `"$vcvars`" && powershell -NoProfile -ExecutionPolicy Bypass -File `"$repo\app\scripts\env_check.ps1`" && cl.exe 2>&1 >> `"$envlog`""
  cmd.exe /C $cmd 2>&1 | Tee-Object -FilePath $log -Append
} else {
  ("vcvars64.bat not found; cannot run Developer shell env check") | Tee-Object -FilePath $log -Append
}

"=== Dev shell verification finished at $(Get-Date -Format o)" | Tee-Object -FilePath $log -Append