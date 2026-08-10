# Contributing

This covers setting up a dev environment and running/building the project's pieces:
the `core` library, the `api` server, the `frontend`, and the Tauri desktop app. For
architecture background, see [`docs/architecture/`](docs/architecture/README.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/), Node.js/npm, and (for the desktop app) the
Rust toolchain (`rustup`). FFmpeg must also be installed and on `PATH` — see the
[README](README.md).

```bash
uv venv
uv pip install -e ".[api,dev,packaging]"

cd frontend && npm install && cd ..
```

`packaging` pulls in PyInstaller, needed only for building the desktop app's sidecar
binary (see below) — omit it if you're just working on `core`/`api`/`cli`.

## Running the pieces

Run Python commands via `uv run <command>` (or activate the venv with
`source .venv/bin/activate` first, if you'd rather not prefix every command).

```bash
# Tests
uv run poe test          # fast unit + integration tests
uv run poe test-slow      # opt-in slow tier (real dataset, network + ffmpeg/deffcode)

# Formatting (CI runs black --check on PRs)
uv run poe format

# CLI
uv run skelly-synchronize <raw_video_folder_path> [-o OUTPUT] [-m audio|brightness]

# API server (http://127.0.0.1:8000)
uv run skelly-sync-api
```

`test`, `test-slow`, and `format` are [poe](https://poethepoet.natn.io/) tasks defined
in `pyproject.toml`'s `[tool.poe.tasks]` — run `uv run poe --help` to list all of them.

For the frontend dev server (talks to the API server above — run both):

```bash
cd frontend && npm run dev
```

## Desktop app (Tauri)

The desktop app wraps `frontend` in a Tauri shell that spawns `api` as a managed
sidecar process. Design details: [`docs/architecture/06-tauri-desktop.md`](docs/architecture/06-tauri-desktop.md).
Currently macOS-only.

### Dev mode

The venv must be **activated** (not just `uv run`) so the Rust shell can find
`skelly-sync-api` on `PATH` when it spawns it, and the command must run from the
**repo root**, not `frontend/` — Tauri's CLI only finds `src-tauri/` by searching
subdirectories of the current directory, and `src-tauri/` is a sibling of `frontend/`,
not nested inside it.

```bash
source .venv/bin/activate
npx --prefix frontend tauri dev
```

This runs the Vite dev server and `cargo run` together, spawns `skelly-sync-api` from
the activated venv's `PATH`, and opens the app window. The first run compiles the Rust
dependency graph from scratch (a few minutes); subsequent runs are fast.

### Building the release app

The release build uses a PyInstaller-frozen `skelly-sync-api` binary as its sidecar.
Freezing isn't wired into `tauri build` itself yet, so it's a separate step first:

```bash
uv run poe freeze-api
```

This freezes `skelly-sync-api` with PyInstaller and places the binary at
`src-tauri/binaries/skelly-sync-api-<target-triple>`, matching Tauri's sidecar naming
convention (see the task's shell script in `pyproject.toml` if you want the manual
equivalent). Rerun it any time the Python side changes; if you're only touching Rust
or frontend code, the previously-frozen binary is reused.

Then build the bundle:

```bash
npx --prefix frontend tauri build
```

Output:
- `src-tauri/target/release/bundle/macos/Skelly Synchronize.app`
- `src-tauri/target/release/bundle/dmg/Skelly Synchronize_0.1.0_aarch64.dmg`

### Testing the built app

```bash
open "src-tauri/target/release/bundle/macos/Skelly Synchronize.app"

# give the onefile sidecar a few seconds to self-extract and bind, then:
curl http://127.0.0.1:8000/health   # expect {"status":"ok"}
```

From there, use the app normally: pick a raw video folder (or paste a path), submit a
job, watch it complete. Quit the app normally (Cmd+Q or the menu) rather than `kill`ing
the process directly — a raw `kill` bypasses Tauri's exit-cleanup hook and isn't
representative of real usage.

To confirm the sidecar didn't leak a process after quitting:

```bash
ps -ef | grep skelly-sync-api | grep -v grep   # should print nothing
```
