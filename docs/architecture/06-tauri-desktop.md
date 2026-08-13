# Tauri Desktop Packaging

## Purpose

Design for wrapping the React frontend ([04-frontend.md](04-frontend.md)) and the FastAPI server ([03-api-design.md](03-api-design.md)) into a single distributable desktop app, using [Tauri](https://tauri.app/) 2 as the native shell. This replaces the "run two processes, open a browser tab" dev/run model with one packaged app a user can launch directly, and gives the frontend a real native OS folder picker in the process.

## Tech choices

- **Tauri 2** (Rust shell + the OS's system webview — no bundled Chromium/Node runtime, unlike Electron).
- **`tauri-plugin-dialog`** for the native folder-picker dialog.
- **`tauri-plugin-shell`** for spawning and managing the API as a child process (a "sidecar").
- **PyInstaller** to freeze the Python API into a standalone binary — see "Packaging" below.

## Process architecture

The Tauri Rust shell owns the API process's lifecycle instead of a developer/user starting it by hand:

- On app startup, Rust spawns the API. Release builds use the bundled PyInstaller sidecar binary via `tauri-plugin-shell`'s `Command::sidecar`; dev builds spawn `skelly-sync-api` directly from `PATH` (relying on the activated Python venv), selected via `cfg!(debug_assertions)`. This avoids needing a frozen binary on every dev iteration.
- The API keeps binding `127.0.0.1:8000`, unchanged from today. **Documented v1 simplification**: no dynamic port negotiation between Rust and the API — if port 8000 is already in use on a user's machine, startup fails. Revisit with a random free port passed to the sidecar's args and forwarded to the frontend via Tauri IPC if this becomes a real problem.
- The frontend polls `GET /health` on mount with retry/backoff and shows a "Starting sync engine…" loading state until it responds, before rendering the Setup screen. This reuses the same polling pattern already established by `useJobPolling` ([04-frontend.md](04-frontend.md)) rather than introducing a separate Rust↔JS readiness signal.
- Shutdown: Rust kills the child process handle when the app exits. A hard kill is acceptable here — the job store is in-memory/ephemeral by design ([03-api-design.md](03-api-design.md)), and each sync job already runs in its own isolated `multiprocessing.Process` ([`skelly_synchronize/api/jobs.py`](../../skelly_synchronize/api/jobs.py)), so there's no shared state to corrupt on an abrupt exit.

## Folder selection

`SetupScreen` gets a "Browse…" button using `@tauri-apps/plugin-dialog`'s `open({ directory: true })`, which returns a real OS-native absolute path directly. The text field stays editable alongside the button, for manual entry/power users.

This resolves the file-picker limitation [04-frontend.md](04-frontend.md) previously documented as an accepted limitation of running in a plain browser (browsers cannot reliably expose real filesystem paths from a picker, per the File System Access API's security model) — that constraint doesn't apply once the frontend only runs inside the Tauri shell. It also retires an earlier idea of adding a server-side `/browse` endpoint that would let the frontend walk the filesystem itself; unnecessary once a native dialog is available.

## Packaging (PyInstaller sidecar)

A new `packaging/pyinstaller/skelly-sync-api.spec` freezes the `skelly-sync-api` entry point — and its heavy dependencies (numpy, scipy, librosa, opencv-contrib, deffcode) — into a standalone build, in **onedir** mode (not onefile). The output directory (the `skelly-sync-api` executable plus its `_internal/` payload) is copied to `src-tauri/resources/skelly-sync-api/`, referenced by `tauri.conf.json`'s `bundle.resources` (not `bundle.externalBin`) so `tauri build` bundles it into the app's `Contents/Resources/`; Rust spawns it directly via a resolved resource path (`app.path().resource_dir()`) rather than `ShellExt::sidecar`.

Onefile was tried first (single executable, fits `externalBin`'s convention cleanly) but caused a real regression: the trimming stage parallelizes across several `ProcessPoolExecutor` workers (`skelly_synchronize/core/pipeline/stages.py`), and each worker re-executes the frozen binary via `multiprocessing`'s spawn method. Under onefile, every worker re-pays the full self-extraction cost on top of the heavy imports, which made real (multi-video) sync jobs pathologically slow — reported as the app "hanging while synchronizing" even though small 2-video test fixtures completed fine. Onedir avoids re-extraction per worker since workers just re-exec the already-unpacked directory's binary directly. The tradeoff is losing `externalBin`'s single-file convention and target-triple resolution, worked around by bundling as a plain resource and spawning manually.

**Primary technical risk**: the job execution model in `skelly_synchronize/api/jobs.py` depends on `multiprocessing.Process` and `multiprocessing.Manager()` for per-job isolation and progress bridging. Frozen executables have well-known multiprocessing wrinkles — the entry point needs `multiprocessing.freeze_support()` guarding (added to `skelly_synchronize/api/main.py`'s `run()`). Confirmed working via a real sync job spike before investing in the rest of the Tauri shell.

**FFmpeg** stays an external system dependency for v1 — it is not bundled into the app or the sidecar binary. This is consistent with the project's existing FFmpeg requirement (see the root `README.md`) and is a deliberate, documented v1 limitation in the same style as other accepted-for-now decisions in this rewrite (e.g. KI-11, KI-16 in [00-known-issues.md](00-known-issues.md)). Revisit bundling a static ffmpeg binary as an app resource in a later pass if the external-dependency requirement proves to be a real adoption blocker.

## Repo layout addition

```
src-tauri/
├── Cargo.toml
├── tauri.conf.json
├── capabilities/          # Tauri 2 permission grants (dialog, shell)
├── icons/
├── resources/              # frozen sidecar (onedir) lands here; git-ignored, built via packaging/pyinstaller
└── src/
    ├── main.rs
    └── lib.rs               # app setup: spawn/track/kill the API child process
packaging/
└── pyinstaller/
    └── skelly-sync-api.spec
```

`frontend/package.json` gains `@tauri-apps/cli` (dev dependency, provides `npm run tauri ...`), plus runtime dependencies `@tauri-apps/api`, `@tauri-apps/plugin-dialog`, `@tauri-apps/plugin-shell`.

## Dev vs release workflow

- **Dev**: `npm run tauri dev` (via `@tauri-apps/cli`). Tauri's `devUrl` points at the Vite dev server; `beforeDevCommand` runs `npm run dev` inside `frontend/`. Rust spawns `skelly-sync-api` from the activated venv's `PATH` rather than a frozen binary, so dev iteration doesn't require re-running PyInstaller.
- **Release**: `npm run tauri build`. `beforeBuildCommand` runs `npm run build` inside `frontend/`. The PyInstaller sidecar must be frozen first — a separate, manual step for now (not yet wired into `tauri build` itself), via the `freeze-api` poe task — and placed in `src-tauri/resources/skelly-sync-api/` before `tauri build` bundles it via `bundle.resources`. Automating this handoff (e.g. a `beforeBundleCommand` or a wrapper script) is a reasonable follow-up once the manual flow is proven to work.

This retires the "two-process, opened in a plain browser tab" dev/run model documented in [04-frontend.md](04-frontend.md) — that model is superseded by `tauri dev`.

## Platform scope

Initial development target was macOS, the primary dev machine. Windows, Linux, and
Intel macOS each need their own natively-built PyInstaller-frozen sidecar binary and
Tauri bundle — PyInstaller and the Rust/Tauri build both require a native runner per
target triple, no cross-compiling either side. This is now automated: `.github/workflows/build-desktop-app.yml`
runs a 4-way build matrix (`windows-latest`, `ubuntu-22.04`, `macos-14` for Apple
Silicon, `macos-13` for Intel), freezing the sidecar and bundling the app natively on
each runner, triggered by a `desktop-v*` tag push (attaches installers to a draft
GitHub Release) or manually via `workflow_dispatch` (uploads build artifacts for
inspection without cutting a release). Code signing/notarization (Apple, Windows) is
out of scope for now — builds are unsigned and will trigger Gatekeeper/SmartScreen
warnings on install.

## Known issues / limitations resolved by this document

- Resolves the file-picker limitation noted in [04-frontend.md](04-frontend.md) (previously an accepted limitation of the browser-only frontend; now actually fixed via a native dialog).
- Supersedes the two-process browser dev/run model in [04-frontend.md](04-frontend.md).
- No `KI-##` item from [00-known-issues.md](00-known-issues.md) maps directly to this doc — all of those describe the pre-rewrite codebase; desktop packaging is new scope introduced after the rewrite's original plan.
