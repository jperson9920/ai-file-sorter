@echo off
REM Set repo root (folder containing this script)
set REPO_DIR=%~dp0
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=amd64
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%app\build_windows.ps1" -Configuration Release -VcpkgRoot "C:\dev\vcpkg" > "%REPO_DIR%logs\build_app_new_path.log" 2>&1
exit /b %ERRORLEVEL%