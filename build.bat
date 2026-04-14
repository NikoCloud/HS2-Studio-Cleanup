@echo off
setlocal

echo ============================================================
echo  HS2 Studio Cleanup — Build Script
echo ============================================================
echo.

:: ── Step 1: PyInstaller portable EXE ────────────────────────────────────
echo [1/2] Building portable EXE with PyInstaller...
pyinstaller HS2_Studio_Cleanup.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)
echo       Done: dist\HS2_Studio_Cleanup.exe
echo.

:: ── Step 2: Inno Setup installer ────────────────────────────────────────
echo [2/2] Building installer with Inno Setup...
set ISCC=
for %%p in (
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe"
    "C:\Program Files\Inno Setup 6\iscc.exe"
    "C:\Program Files (x86)\Inno Setup 5\iscc.exe"
    "C:\Program Files\Inno Setup 5\iscc.exe"
) do (
    if exist %%p set ISCC=%%p
)

if "%ISCC%"=="" (
    echo WARNING: Inno Setup not found. Skipping installer build.
    echo          Install from https://jrsoftware.org/isinfo.php to generate the installer.
) else (
    %ISCC% installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed.
        exit /b 1
    )
    echo       Done: dist\HS2StudioCleanup_Setup.exe
)

echo.
echo ============================================================
echo  Build complete!
echo ============================================================
