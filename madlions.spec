# PyInstaller spec for the MADLIONS 60 Configurator (Windows, one-file).
# Build with:  pyinstaller madlions.spec
# Requires the Edge WebView2 runtime on the target machine (preinstalled on Windows 10/11).

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# pywebview pulls in a platform backend (Edge WebView2 via pythonnet/clr on Windows).
# collect_all grabs its submodules/data so the frozen app can create the window.
webview_datas, webview_bins, webview_hidden = collect_all("webview")
# pystray selects its backend (e.g. pystray._win32) dynamically — collect it so the
# tray icon works in the frozen build.
pystray_datas, pystray_bins, pystray_hidden = collect_all("pystray")

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=webview_bins + pystray_bins,
    datas=[("ui", "ui")] + webview_datas + pystray_datas,   # bundle the web frontend
    hiddenimports=["hid", "clr", "PIL", "pystray._win32"] + webview_hidden + pystray_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],                    # old GUI dep; not used by this app
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MADLIONS60",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # do not depend on UPX being installed
    runtime_tmpdir=None,
    console=False,            # GUI app: no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="ui/icon.ico",     # add an .ico here when one exists
)
