# -*- mode: python ; coding: utf-8 -*-
#
# Freezes the `skelly-sync-api` console script into a standalone (onedir)
# binary, bundled into the Tauri app as a plain resource (not a
# `externalBin` sidecar). See docs/architecture/06-tauri-desktop.md.
#
# Onedir (not onefile): the trimming stage parallelizes across several
# `ProcessPoolExecutor` workers (skelly_synchronize/core/pipeline/stages.py),
# and each worker re-executes this frozen binary via `multiprocessing`'s
# spawn method. Under onefile, every single worker re-pays the ~150MB
# self-extraction cost on top of the heavy numpy/scipy/librosa/cv2 imports —
# with several workers spawning in parallel on real (larger, more numerous)
# video sets, this made sync jobs pathologically slow / appear to hang.
# Onedir avoids re-extraction per worker (workers just re-exec the
# already-unpacked directory's binary directly).
#
# Because onedir's output is a directory (exe + `_internal/` payload), not a
# single executable, it doesn't fit Tauri's `externalBin` sidecar convention
# (which expects one file named `<name>-<target-triple>`). Instead it's
# bundled as a plain `bundle.resources` entry (preserving directory
# structure) and spawned directly from Rust via a resolved resource path —
# see `spawn_api()` in src-tauri/src/lib.rs.
#
# Build:  pyinstaller packaging/pyinstaller/skelly-sync-api.spec
# Output: dist/skelly-sync-api/ (directory: skelly-sync-api exe + _internal/)
#
# Must be copied to src-tauri/resources/skelly-sync-api/ before `tauri
# build` — manual step for now (see the `freeze-api` poe task).

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
    [],
    exclude_binaries=True,
    name="skelly-sync-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="skelly-sync-api",
)
