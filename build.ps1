# Build Script for Claudias Spezifikationen Assistent (PowerShell)
# Usage: .\build.ps1 [-Clean] [-SkipTest] [-Verbose]

param(
    [switch]$Clean,
    [switch]$SkipTest,
    [switch]$Verbose
)

# Colors
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorInfo = "Cyan"
$ColorHeader = "Magenta"

function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $ColorHeader
    Write-Host $text -ForegroundColor $ColorHeader
    Write-Host ("=" * 60) -ForegroundColor $ColorHeader
    Write-Host ""
}

function Write-Step($text) {
    Write-Host "[*] $text" -ForegroundColor $ColorInfo
}

function Write-Success($text) {
    Write-Host "[OK] $text" -ForegroundColor $ColorSuccess
}

function Write-Error($text) {
    Write-Host "[ERROR] $text" -ForegroundColor $ColorError
}

function Write-Warning($text) {
    Write-Host "[WARNING] $text" -ForegroundColor $ColorWarning
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Header "Build Script for SpecHTMLGenerator"

# Check Python
Write-Step "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error "Python not found. Please install Python 3.9+"
    exit 1
}

# Check PyInstaller
Write-Step "Checking PyInstaller..."
try {
    $pyiVersion = python -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
    Write-Success "PyInstaller found: v$pyiVersion"
} catch {
    Write-Warning "PyInstaller not found. Installing..."
    pip install pyinstaller
}

# Clean build directories if requested
if ($Clean) {
    Write-Step "Cleaning build directories..."
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    Write-Success "Clean complete"
}

# Test resources
if (-not $SkipTest) {
    Write-Step "Testing resource paths..."
    try {
        python test_resources.py
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Resource test failed!"
            exit 1
        }
        Write-Success "Resource test passed"
    } catch {
        Write-Warning "test_resources.py not found, skipping test"
    }
}

# Build executable
Write-Header "Building Executable"

Write-Step "Running PyInstaller..."
$buildArgs = @("SpecHTMLGenerator.spec")
if ($Verbose) {
    $buildArgs += "--log-level=DEBUG"
}

pyinstaller @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed!"
    exit 1
}

Write-Success "PyInstaller build complete"

# Verify output
Write-Header "Verifying Build Output"

$distDir = "dist\SpecHTMLGenerator"
$exePath = "$distDir\SpecHTMLGenerator.exe"

# Check for PyInstaller 6.x _internal directory structure
$internalDir = "$distDir\_internal"
$hasInternalDir = Test-Path $internalDir

if (Test-Path $exePath) {
    $exeInfo = Get-Item $exePath
    Write-Success "Executable created: $exePath"
    Write-Host "        Size: $([math]::Round($exeInfo.Length / 1MB, 2)) MB" -ForegroundColor $ColorInfo

    if ($hasInternalDir) {
        Write-Success "PyInstaller 6.x structure detected (_internal/ directory)"
    } else {
        Write-Success "PyInstaller classic structure detected"
    }
} else {
    Write-Error "Executable not found: $exePath"
    exit 1
}

# Verify icons are included
$iconsDir = "$distDir\icons"
$iconsInternalDir = "$distDir\_internal\icons"

if (Test-Path $iconsDir) {
    $iconCount = (Get-ChildItem $iconsDir -File).Count
    Write-Success "Icons directory found: $iconCount files"
} elseif (Test-Path $iconsInternalDir) {
    $iconCount = (Get-ChildItem $iconsInternalDir -File).Count
    Write-Success "Icons directory found in _internal: $iconCount files"
} else {
    Write-Warning "Icons directory not found in dist - they may be embedded"
}

# Summary
Write-Header "Build Summary"

Write-Host "Executable: $exePath" -ForegroundColor $ColorSuccess
Write-Host ""
Write-Host "Next steps:" -ForegroundColor $ColorInfo
Write-Host "  1. Test the executable: .\$exePath"
Write-Host "  2. Create installer: Run Inno Setup with installer.iss"
Write-Host "  3. Test the installer"
Write-Host "  4. Upload release: python upload_release.py"
Write-Host ""

Write-Success "Build completed successfully!"
