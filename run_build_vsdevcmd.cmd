@echo off
REM Initialize Visual Studio dev environment (x64)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=amd64
REM Prepend vcpkg cmake path for this process
set "PATH=C:\dev\vcpkg\downloads\tools\cmake-3.30.1-windows\cmake-3.30.1-windows-i386\bin;%PATH%"
pwsh -NoProfile -ExecutionPolicy Bypass -File .\app\build_windows.ps1 -Configuration Release -VcpkgRoot C:\dev\vcpkg > logs\build_app_new_path.log 2>&1