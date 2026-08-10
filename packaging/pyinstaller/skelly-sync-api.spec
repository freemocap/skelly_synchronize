# -*- mode: python ; coding: utf-8 -*-
#
# Freezes the `skelly-sync-api` console script into a standalone (onefile)
# binary for use as a Tauri sidecar. See docs/architecture/06-tauri-desktop.md.
#
# Onefile (not onedir): Tauri's `externalBin` convention expects a single
# executable at `binaries/skelly-sync-api-<target-triple>` — onedir's
# directory-plus-_internal/-payload output doesn't fit that convention
# cleanly. The Milestone-0 spike proved multiprocessing.Process/Manager work
# correctly under a frozen PyInstaller build on macOS in onedir mode; onefile
# uses the same freeze_support()-guarded entry point, so that result carries
# over (verify empirically after switching modes — see spike test procedure
# in docs/architecture/06-tauri-desktop.md's implementation plan).
#
# Build:  pyinstaller packaging/pyinstaller/skelly-sync-api.spec
# Output: dist/skelly-sync-api (single binary)
#
# Must be renamed to match Tauri's sidecar target-triple convention (e.g.
# skelly-sync-api-aarch64-apple-darwin) and placed under src-tauri/binaries/
# before `tauri build` — manual step for now.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

entry_script = str(Path(SPECPATH) / "entrypoint.py")

a = Analysis(
    [entry_script],
    pathex=[],
    binaries=[],
    datas=[
        *collect_data_files("librosa"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name="skelly-sync-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
