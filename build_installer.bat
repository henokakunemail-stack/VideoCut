@echo off
title VideoCut — Build Installer
color 0A
echo.
echo  ============================================
echo   VideoCut v2 — Windows Installer Builder
echo  ============================================
echo.

REM ── Step 0: Check Python ─────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Install Python 3.10+ from https://python.org
    echo         Make sure "Add to PATH" is checked during install.
    pause & exit /b 1
)

REM ── Step 1: Install / verify dependencies ────────────────────
echo [1/5] Installing Python dependencies...
echo       Core packages...
pip install PyQt6 opencv-python numpy pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo       AI runtime and bundled models...
pip install onnxruntime imageio-ffmpeg --quiet
python toolsetch_models.py
if errorlevel 1 echo       [WARN] some models were not fetched; those features will show "model not installed".
echo       (set VIDEOCUT_MODELS=all to also bundle the large High-quality models)

REM ── Step 2: Create app icon if missing ───────────────────────
echo [2/5] Checking assets...
if not exist "assets\icons" mkdir "assets\icons"
if not exist "assets\icons\app.ico" (
    echo       Generating VideoCut icon from SVG...
    python -c "
import struct, math

def make_ico():
    size = 64
    pixels = []
    cx2, cy2 = size // 2, size // 2
    r_outer = size // 2 - 1
    r_inner = size // 2 - 8

    for y in range(size):
        for x in range(size):
            dx, dy = x - cx2, y - cy2
            dist = math.sqrt(dx*dx + dy*dy)

            # Dark background circle
            if dist > r_outer:
                pixels.extend([0, 0, 0, 0])  # transparent
            elif dist > r_inner:
                # Red ring border
                t = (dist - r_inner) / (r_outer - r_inner)
                r = int(0xFE * (1 - t * 0.2))
                g = int(0x2C * (1 - t * 0.3))
                b = int(0x55 * (1 - t * 0.3))
                pixels.extend([b, g, r, 255])
            else:
                # Inside: dark with play triangle
                # Play triangle: vertices at roughly (cx-10,cy-14),(cx-10,cy+14),(cx+14,cy)
                # Point-in-triangle test
                x1, y1 = cx2 - 10, cy2 - 14
                x2, y2 = cx2 - 10, cy2 + 14
                x3, y3 = cx2 + 16, cy2

                def sign(px,py,ax,ay,bx,by):
                    return (px-bx)*(ay-by) - (ax-bx)*(py-by)

                d1 = sign(x, y, x1, y1, x2, y2)
                d2 = sign(x, y, x2, y2, x3, y3)
                d3 = sign(x, y, x3, y3, x1, y1)

                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                in_tri = not (has_neg and has_pos)

                if in_tri:
                    pixels.extend([0xFF, 0xFF, 0xFF, 255])  # white play arrow
                else:
                    pixels.extend([0x1a, 0x1a, 0x2e, 220])  # dark blue bg

    # BMP DIB header
    bmp = struct.pack('<IiiHHIIiiII',
        40, size, -size, 1, 32, 0, size*size*4, 0, 0, 0, 0)
    bmp += bytes(pixels)

    ico = struct.pack('<HHH', 0, 1, 1)
    ico += struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(bmp), 22)
    ico += bmp

    with open('assets/icons/app.ico', 'wb') as f:
        f.write(ico)
    print('VideoCut icon created (64x64).')

make_ico()
"
)
echo       OK.

REM ── Step 3: Run PyInstaller ───────────────────────────────────
echo [3/5] Bundling with PyInstaller (this takes 1-3 minutes)...
echo.

REM Clean previous build
if exist "dist\VideoCut" rmdir /s /q "dist\VideoCut"
if exist "build\VideoCut" rmdir /s /q "build\VideoCut"

pyinstaller videocut.spec --noconfirm 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See output above.
    pause & exit /b 1
)

echo.
echo [3/5] PyInstaller done. Checking output...
if not exist "dist\VideoCut\VideoCut.exe" (
    echo [ERROR] VideoCut.exe not found in dist folder.
    pause & exit /b 1
)
echo       OK — dist\VideoCut\VideoCut.exe created.

REM ── Step 4: Write README for installer ───────────────────────
echo [4/5] Writing README...
(
echo VideoCut v2.0
echo =================
echo.
echo A feature-rich video editor professional video editor.
echo.
echo Features:
echo - 37 video filters
echo - Beauty retouch tools
echo - Chroma key ^(green screen^)
echo - Color grading with LUTs
echo - Shape masking
echo - Multi-track timeline
echo - Text, stickers, effects
echo - Audio beat sync
echo - Keyframe animation
echo - Export to MP4/AVI/MOV
echo.
echo Requirements: Windows 10/11 x64
echo.
echo To report issues, check the project folder.
) > "dist\VideoCut\README.txt"

REM ── Step 5: Build NSIS installer ─────────────────────────────
echo [5/5] Building installer .exe with NSIS...
echo.

REM Check if NSIS is installed
where makensis >nul 2>&1
if errorlevel 1 (
    REM Try common install paths
    set NSIS_PATH=
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" set NSIS_PATH=C:\Program Files (x86)\NSIS\makensis.exe
    if exist "C:\Program Files\NSIS\makensis.exe"       set NSIS_PATH=C:\Program Files\NSIS\makensis.exe

    if "!NSIS_PATH!"=="" (
        echo [WARNING] NSIS not found.
        echo.
        echo  To build the full Setup.exe installer:
        echo  1. Download NSIS from https://nsis.sourceforge.io/Download
        echo  2. Install it
        echo  3. Run this script again
        echo.
        echo  For now, the app is ready in: dist\VideoCut\
        echo  You can run it directly:     dist\VideoCut\VideoCut.exe
        echo.
        goto :done_no_nsis
    )
    set "MAKENSIS=!NSIS_PATH!"
) else (
    set MAKENSIS=makensis
)

setlocal enabledelayedexpansion
"!MAKENSIS!" installer\setup.nsi
if errorlevel 1 (
    echo [ERROR] NSIS failed. See output above.
    pause & exit /b 1
)

echo.
echo  ============================================
echo   BUILD COMPLETE!
echo  ============================================
echo.
echo   Installer:  installer\VideoCut_Setup.exe
echo   Portable:   dist\VideoCut\VideoCut.exe
echo.
echo  Distribute either one. The Setup.exe installs
echo  to Program Files and adds Start Menu shortcuts.
echo.
pause
exit /b 0

:done_no_nsis
echo  ============================================
echo   BUILD COMPLETE (portable only — no NSIS)
echo  ============================================
echo.
echo   Portable app: dist\VideoCut\VideoCut.exe
echo.
echo  Install NSIS and re-run to also get Setup.exe
echo.
pause
