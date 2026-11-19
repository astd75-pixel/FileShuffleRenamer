
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('PySide6')

a = Analysis(
    ['SRC/main.py'],
    pathex=['SRC'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['SRC.renamer_core'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FileShuffleRenamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False
)

