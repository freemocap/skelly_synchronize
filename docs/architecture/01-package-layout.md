# Target Package Layout

## Purpose

This document defines the target repo/module structure and packaging decisions for the rewrite, so that a repo skeleton can be scaffolded before any subsystem code is written.

## Monorepo, not multi-repo

`skelly_synchronize` stays a single GitHub repository, with the new React app living in a `frontend/` subfolder. This is a local, single-user tool with one release cadence — splitting into separate repos would add release-coordination overhead (versioning, cross-repo CI, cross-repo issue tracking) with no real benefit at this scale.

## Target tree

```
skelly_synchronize/
├── packages/
│   ├── core/                        # skelly_sync_core — installable, zero FastAPI/PySide6 deps
│   │   ├── pyproject.toml
│   │   └── skelly_sync_core/
│   │       ├── models.py            # Pydantic data models (VideoInfo, AudioInfo, LagResult, ...)
│   │       ├── backends/
│   │       │   ├── base.py          # VideoBackend Protocol
│   │       │   ├── ffmpeg.py        # FfmpegBackend
│   │       │   └── deffcode.py      # DeffcodeBackend
│   │       ├── pipeline/
│   │       │   ├── stages.py        # PipelineStage implementations
│   │       │   └── runner.py        # SyncPipeline
│   │       ├── audio.py
│   │       ├── brightness.py
│   │       ├── debug.py
│   │       ├── config.py            # all constants: folder/file names, naming conventions, defaults
│   │       └── logging_setup.py     # opt-in only; never called from inside core itself
│   └── api/                         # skelly_sync_api — FastAPI app, depends on core
│       ├── pyproject.toml
│       └── skelly_sync_api/
│           ├── main.py
│           ├── routers/
│           ├── jobs.py              # in-memory job store + per-job process orchestration
│           └── schemas.py           # API-only wrapper models (e.g. JobCreateResponse)
├── frontend/                        # React app (Vite + TypeScript), talks to api/ over HTTP only
├── cli/                             # thin argparse/typer wrapper over core, replaces __main__.py
├── docs/
│   └── architecture/
└── pyproject.toml                   # root workspace config
```

## Dependency direction

- `core` has zero knowledge of FastAPI, uvicorn, or PySide6. It only depends on the algorithm libraries it actually needs (numpy, scipy, librosa, opencv, deffcode, pydantic).
- `api` depends on `core` as a regular dependency.
- `cli` depends only on `core` (not `api`).
- `frontend` depends on nothing Python — it talks to `api` over HTTP only.

## Core as its own installable package

`core` ships as its own installable package, `skelly_sync_core`, distributed independently (e.g. on PyPI) so it can be reused by other tools — for example, embedding sync into a larger FreeMoCap pipeline — without pulling in FastAPI, uvicorn, or pydantic-settings as transitive dependencies. `api` declares `skelly_sync_core` as a normal dependency, not a path-based extra of the same package; keeping it as an "extra" of one combined package would force both to share one release cadence and one dependency footprint.

Local development across the monorepo uses a workspace-style setup with path dependencies for `api` → `core` and `cli` → `core`, so changes in `core` are picked up immediately by the other packages during development.

## Build backend

Recommend switching from `flit_core` to **`hatchling`**, since it has better support for multi-package monorepo/workspace layouts. Keep the decision under review — if `hatchling` introduces friction, revisit, but there's no reason to default back to `flit_core`'s single-package assumptions once the repo has three installable Python packages.

## Naming

- `skelly_sync_core` and `skelly_sync_api` for the two installable packages, avoiding a name clash with the existing `skelly_synchronize` PyPI package.
- `skelly_synchronize` continues as the umbrella/meta name for the project and the CLI entry point for continuity with existing users.
- Console scripts: `skelly-sync` (CLI, replaces `python -m skelly_synchronize`/`__main__.py`) and `skelly-sync-api` (launches the FastAPI server, wraps `uvicorn`).

## Constants and configuration (resolves KI-15)

All magic strings and numbers — folder names, debug file names, naming conventions like the synced-video prefix, and defaults like the standard audio sample rate — are consolidated into `core/config.py`. No sync-relevant constant should live outside this module (the current codebase has one, `standard_audio_sample_rate`, defined locally inside `normalize_framerates.py` instead of the shared constants file — this must not recur).

## Logging policy (resolves KI-18)

Library modules (`core`, and `api`'s internal logic) use `logging.getLogger(__name__)` only and never call `logging.basicConfig`, add handlers to the root logger, or otherwise mutate global logging state. Exactly one place per process configures logging: the CLI entry point for `skelly-sync`, and the API entry point (`main.py`) for `skelly-sync-api`.

## Removed in the rewrite

- The entire PySide6 GUI package is deleted once the React frontend reaches feature parity (end of the migration's frontend phase) — not kept behind a flag or maintained in parallel.
- `gui/widgets/run_button_widget.py` (dead, buggy, unused — KI-23) is not ported at all.
- `sys.path.insert` hacks currently in `__init__.py`, `__main__.py`, and test files (KI-20) are removed; all imports rely on a correctly configured installed/editable package.
- The `name_synced_video` hard-coded `filename[4:]` prefix slice (KI-21) is replaced with `str.removeprefix("raw_")` (or equivalent) driven by the naming constants in `core/config.py`.
- `skelly_synchronize/tests/utilities/*` helpers that are imported by production code today (KI-17) are promoted into `core` proper; test code never becomes a runtime dependency of the library again.

## Packaging cleanup (resolves KI-26)

- Fix `pyproject.toml` metadata left over from the template repo (`description`, `keywords`).
- Loosen dependency pins from exact `==` to compatible ranges (e.g. `>=X,<Y`) where there's no known reason for an exact pin.
- Align `requires-python` with whatever Python versions are actually covered by the CI matrix (see [05-testing-strategy.md](05-testing-strategy.md)), rather than claiming a wider range than is tested.
