@echo off
setlocal enabledelayedexpansion

echo ========================================
echo VScope Build Script
echo ========================================

::: Save current directory and move to project root
set BUILD_DIR=%~dp0
echo Build script directory: %BUILD_DIR%
echo Initial working directory: %CD%
cd /d "%BUILD_DIR%\.."
echo Project root directory: %CD%

::: Get version from git tags
set VERSION=1.0.1
set FOUND_GIT_TAG=false

echo Checking for git tags from project root...
echo Current directory: %CD%

::: List all available tags for debugging
echo Available git tags:
git tag -l

::: Try simple git tag list first
echo Testing basic git tag command...
git tag -l >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Git tag command works
    
    :: Get the last tag from the list (assuming it's the latest)
    for /f %%i in ('git tag -l') do (
        set LATEST_TAG=%%i
    )
    
    if defined LATEST_TAG (
        set VERSION=!LATEST_TAG!
        :: Remove 'v' prefix if present
        if "!VERSION:~0,1!"=="v" set VERSION=!VERSION:~1!
        echo Found git tag: !LATEST_TAG!
        set FOUND_GIT_TAG=true
    ) else (
        echo No tags found in git tag list
    )
) else (
    echo Git tag command failed
)

if "!FOUND_GIT_TAG!"=="false" (
    echo Using default version: %VERSION%
)

echo Building version: %VERSION%

::: Clean previous builds
echo Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build_temp" rmdir /s /q "build_temp"

:: Skipping version bump steps; version is managed via project metadata
cd "%BUILD_DIR%"

::: Build with PyInstaller from project root
echo Building executable...
echo Changing back to project root for PyInstaller...
cd /d "%BUILD_DIR%\.."
echo Current directory for PyInstaller: %CD%

::: Verify main.py exists
if exist "main.py" (
    echo Found main.py
) else (
    echo main.py not found in current directory
    echo Files in current directory:
    dir *.py
    echo Build failed - main.py not found!
    pause
    exit /b 1
)

::: Run PyInstaller with full paths to avoid confusion
echo Running PyInstaller...
pyinstaller "%BUILD_DIR%/build.spec" --clean --noconfirm --distpath "dist" --workpath "build_temp"

if %ERRORLEVEL% neq 0 (
    echo Build failed!
    echo.
    echo Debugging info:
    echo - Build script: %BUILD_DIR%
    echo - Project root: %CD%
    echo - Spec file: %BUILD_DIR%build.spec
    pause
    exit /b 1
)

echo ========================================
echo Build completed successfully!
echo Version: %VERSION%
echo Executable: %CD%\..\dist\VScope.exe
echo ========================================
pause

endlocal 