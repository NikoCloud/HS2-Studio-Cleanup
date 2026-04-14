# -*- mode: python ; coding: utf-8 -*-
# HS2 Studio Cleanup — PyInstaller build spec

import sys
from pathlib import Path

PROJ = Path(SPECPATH)

a = Analysis(
    [str(PROJ / 'main.py')],
    pathex=[str(PROJ)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyQt6 modules that PyInstaller sometimes misses
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # Our own packages
        'core',
        'core.index_db',
        'core.settings',
        'core.hasher',
        'core.scanner',
        'core.dedup_engine',
        'core.org_engine',
        'core.movement_engine',
        'handlers',
        'handlers.zipmod_handler',
        'handlers.characard_handler',
        'handlers.scene_handler',
        'handlers.generic_handler',
        'gui',
        'gui.main_window',
        'gui.scan_worker',
        'gui.results_panel',
        'gui.styles',
        # Third-party
        'xxhash',
        'natsort',
        'sqlite3',
        'xml.etree.ElementTree',
        'zipfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
        'test',
        'unittest',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HS2_Studio_Cleanup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # No console window — pure GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # Uncomment and add icon.ico to add a custom icon
)
