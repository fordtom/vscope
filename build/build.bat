@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo VScope Nuitka Build
echo ========================================

set "BUILD_DIR=%~dp0"
set "PROJECT_ROOT=%BUILD_DIR%.."
pushd "%PROJECT_ROOT%" >nul

echo Build script directory: %BUILD_DIR%
echo Project root directory: %CD%

:: Resolve version from git (fall back to pyproject)
set "VERSION="
for /f "usebackq tokens=*" %%i in (`git describe --tags --abbrev=0 2^>nul`) do (
    set "VERSION=%%i"
    goto :version_ok
)

:version_ok
if not defined VERSION (
    for /f "tokens=2 delims==" %%i in ('findstr /b /c:"version =" pyproject.toml') do (
        set "VERSION=%%~i"
    )
)

set "VERSION=%VERSION: =%"
if defined VERSION if "%VERSION:~0,1%"=="v" set "VERSION=%VERSION:~1%"
if not defined VERSION set "VERSION=0.0.0"

echo Building version: %VERSION%

:: Prepare output directories
set "DIST_DIR=%PROJECT_ROOT%\dist"
set "CACHE_DIR=%PROJECT_ROOT%\.nuitka"
if exist "%DIST_DIR%" (
    echo Removing previous dist directory...
    rmdir /s /q "%DIST_DIR%"
)
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"
set "NUITKA_CACHE_DIR=%CACHE_DIR%"

:: Ensure entry point exists
if not exist "%PROJECT_ROOT%\main.py" (
    echo Error: main.py not found at project root.
    popd
    exit /b 1
)

echo Running Nuitka...
python -m nuitka ^
    --standalone ^
    --onefile ^
    --assume-yes-for-downloads ^
    --enable-plugin=pyqt6 ^
    --enable-plugin=numpy ^
    --include-qt-plugins=sensible,styles,platforms,iconengines ^
    --include-package=app ^
    --include-package=core ^
    --nofollow-import-to=PyQt6.QtOpenGL ^
    --remove-output ^
    --output-dir="%DIST_DIR%" ^
    --product-name="VScope" ^
    --file-version="%VERSION%" ^
    --product-version="%VERSION%" ^
    --company-name="VScope" ^
    --windows-console-mode=disable ^
    main.py

if errorlevel 1 (
    echo Nuitka build failed.
    popd
    exit /b 1
)

echo ========================================
echo Nuitka build completed successfully!
for %%f in ("%DIST_DIR%\main.exe" "%DIST_DIR%\main.cmd" "%DIST_DIR%\main.bin") do (
    if exist %%f (
        ren %%f VScope.exe
    )
)
if exist "%DIST_DIR%\VScope.exe" (
    echo Output: %DIST_DIR%\VScope.exe
) else (
    echo Warning: Expected VScope.exe not found. Actual dist contents:
    dir "%DIST_DIR%"
)
echo ========================================

popd >nul
endlocal
exit /b 0