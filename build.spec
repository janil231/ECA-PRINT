# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for Print Vendo.

Builds ONE self-contained PrintVendo.exe that runs the kiosk with no
install: Python, CustomTkinter, PyMuPDF, Flask and the upload web page
are all packed inside.

Build:  pyinstaller build.spec --noconfirm
Result: dist/PrintVendo.exe
"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []

# CustomTkinter ships theme JSON + assets that must travel with the exe.
try:
    datas += collect_data_files('customtkinter')
except Exception:
    pass

# The phone-upload page is loaded at runtime (not imported), so pack it.
datas += [('wireless/templates', 'wireless/templates')]

# Demo documents travel inside the exe, so a freshly downloaded copy has
# real files to show during a presentation (unpacked into temp/ on first run).
if os.path.isdir('demo_files'):
    datas += [('demo_files', 'demo_files')]

hiddenimports = []
for pkg in ('win32com', 'win32com.client', 'win32print', 'win32ui'):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        hiddenimports.append(pkg)
hiddenimports += ['PIL.ImageWin', 'win32con', 'docx', 'fitz', 'qrcode', 'flask']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'matplotlib', 'tkinter.test'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PrintVendo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
