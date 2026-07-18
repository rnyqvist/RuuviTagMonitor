# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


python_root = Path(sys.base_prefix)
tcl_root = python_root / "tcl"
dll_root = python_root / "DLLs"

hiddenimports = collect_submodules("bleak") + ["tkinter", "tkinter.ttk", "tkinter.messagebox"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[
        (str(dll_root / "_tkinter.pyd"), "."),
        (str(dll_root / "tcl86t.dll"), "."),
        (str(dll_root / "tk86t.dll"), "."),
        (str(Path(sys._base_executable)), "."),
    ],
    datas=[
        (str(tcl_root / "tcl8.6"), "_tcl_data"),
        (str(tcl_root / "tk8.6"), "_tk_data"),
        (str(tcl_root / "tcl8.6"), "tcl/tcl8.6"),
        (str(tcl_root / "tk8.6"), "tcl/tk8.6"),
    ],
    hiddenimports=hiddenimports,
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=["pyi_rth_tkinter_fix.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RuuviTagMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
