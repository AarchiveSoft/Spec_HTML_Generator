@echo off
REM Build Script for Claudias Spezifikationen Assistent (Batch)
REM Usage: build.bat

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Build Script for SpecHTMLGenerator
echo ============================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check Python
echo [*] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [OK] %PYTHON_VER%

REM Check PyInstaller
echo [*] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PyInstaller not found. Installing...
    pip install pyinstaller
)
echo [OK] PyInstaller available

REM Test resources
echo [*] Testing resource paths...
if exist test_resources.py (
    python test_resources.py
    if errorlevel 1 (
        echo [ERROR] Resource test failed!
        exit /b 1
    )
    echo [OK] Resource test passed
) else (
    echo [WARNING] test_resources.py not found, skipping test
)

REM Build
echo.
echo ============================================================
echo Building Executable
echo ============================================================
echo.

echo [*] Running PyInstaller...
pyinstaller SpecHTMLGenerator.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    exit /b 1
)
echo [OK] PyInstaller build complete

REM Verify output
echo.
echo ============================================================
echo Verifying Build Output
echo ============================================================
echo.

set "DIST_DIR=dist\SpecHTMLGenerator"
set "EXE_PATH=%DIST_DIR%\SpecHTMLGenerator.exe"

if exist "%EXE_PATH%" (
    echo [OK] Executable created: %EXE_PATH%

    REM Check for PyInstaller 6.x structure
    if exist "%DIST_DIR%\_internal" (
        echo [OK] PyInstaller 6.x structure detected (_internal/ directory^)
    ) else (
        echo [OK] PyInstaller classic structure detected
    )
) else (
    echo [ERROR] Executable not found: %EXE_PATH%
    exit /b 1
)

REM Verify icons
if exist "%DIST_DIR%\icons" (
    echo [OK] Icons directory found
) else if exist "%DIST_DIR%\_internal\icons" (
    echo [OK] Icons directory found in _internal
) else (
    echo [WARNING] Icons directory not found - may be embedded
)

REM Summary
echo.
echo ============================================================
echo Build Summary
echo ============================================================
echo.
echo Executable: %EXE_PATH%
echo.
echo Next steps:
echo   1. Test the executable: %EXE_PATH%
echo   2. Create installer: Run Inno Setup with installer.iss
echo   3. Test the installer
echo   4. Upload release: python upload_release.py
echo.
echo [OK] Build completed successfully!

endlocal
