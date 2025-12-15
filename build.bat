taskkill /F /IM houdini.exe >nul 2>&1

set HFS=C:\Program Files\Side Effects Software\Houdini 21.0.512

python scripts/build.py Release "%HFS%"

@REM if %ERRORLEVEL% == 0 (
@REM     start "" "%HFS%\bin\houdini.exe"
@REM )
