# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for VideoCut v2
# Usage: pyinstaller videocut.spec --noconfirm

import sys
import os

block_cipher = None

# Check for icon
icon_path = os.path.join('assets', 'icons', 'app.ico')
if not os.path.exists(icon_path):
    icon_path = None   # PyInstaller will use default

hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtMultimedia',
    'PyQt6.sip',
    'cv2',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib.format',
    'numpy.random',
    'src',
    'src.core',
    'src.core.project',
    'src.core.video_player',
    'src.ui',
    'src.ui.main_window',
    'src.ui.media_panel',
    'src.ui.properties_panel',
    'src.ui.preview_panel',
    'src.ui.timeline_panel',
    'src.ui.toolbar_panel',
    'src.ui.text_dialog',
    'src.ui.export_dialog',
    # AI features
    'src.core.ai_background',
    'src.ui.background_panel',
    'src.core.auto_caption',
    'src.ui.subtitle_dialog',
    'src.core.beat_sync',
    'src.core.keyframe_engine',
    'src.ui.keyframe_panel',
    'src.core.audio_fx',
    'src.ui.audio_fx_panel',
    'src.ui.effects_panel',
    # Optional heavy AI libs (soft-imported)
    'rembg',
    'whisper',
    'librosa',
    'scipy',
    'scipy.fft',
    'scipy.signal',
    'scipy.io',
    'scipy.io.wavfile',
]

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={
        'PyQt6': {
            'plugins': [
                'platforms',
                'styles',
                'imageformats',
                'iconengines',
            ]
        }
    },
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
        'matplotlib',
        'pandas',
        'IPython',
        'jupyter',
        'PIL',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoCut',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'msvcp140.dll',
        'python3*.dll',
    ],
    name='VideoCut',
)
