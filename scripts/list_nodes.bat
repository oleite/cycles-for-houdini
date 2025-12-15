@echo off
setlocal enabledelayedexpansion

set "HFS=C:\Program Files\Side Effects Software\Houdini 21.0.512"

set "HFS_BIN=%HFS%\bin"
set "CYCLES_EXE=%~dp0..\cycles\install\cycles.exe"
set "WRITE_TO=%~dp0cycles_nodes.yaml"


if not exist %CYCLES_EXE% (
    echo Please build Cycles first by running build.bat !
    exit /b 1
)

echo Listing available Cycles nodes...

set "PATH=%HFS_BIN%;%PATH%"
call "%CYCLES_EXE%" --list-nodes "%WRITE_TO%"

if errorlevel 1 (
    echo.
    echo Failed to list nodes!
    exit /b 1
)

echo List of nodes written to "%WRITE_TO%"
echo ----- Done -----