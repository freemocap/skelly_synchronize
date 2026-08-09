# Target Package Layout

## Purpose

This document defines the target repo/module structure and packaging decisions for the rewrite, so that a repo skeleton can be scaffolded before any subsystem code is written.

## Monorepo, not multi-repo

`skelly_synchronize` stays a single GitHub repository, with the new React app living in a `frontend/` subfolder. This is a local, single-user tool with one release cadence — splitting into separate repos would add release-coordination overhead (versioning, cross-repo CI, cross-repo issue tracking) with no real benefit at this scale.

## Target tree

One Python package, `skelly_synchronize`, published as a single PyPI distribution. `core` and `api` are subpackages within it, not separate distributions — see "Single package, `api` as an optional extra" below for why.

```
skelly_synchronize/
├── pyproject.toml                   # single package; "api" extra pulls in fastapi/uvicorn
├── skelly_synchronize/
│   ├── core/                        # sync engine — zero FastAPI/PySide6 deps
│   │   ├── models.py                # Pydantic data models (VideoInfo, AudioInfo, LagResult, ...)
│   │   ├── backends/
│   │   │   ├── base.py              # VideoBackend Protocol
│   │   │   ├── ffmpeg.py            # FfmpegBackend
│   │   │   └── deffcode.py          # DeffcodeBackend
│   │   ├── pipeline/
│   │   │   ├── stages.py            # PipelineStage implementations
│   │   │   └── runner.py            # SyncPipeline
│   │   ├── audio.py
│   │   ├── brightness.py
│   │   ├── debug.py
│   │   ├── config.py                # all constants: folder/file names, naming conventions, defaults
│   │   └── logging_setup.py         # opt-in only; never called from inside core itself
│   ├── api/                         # FastAPI app — only importable when the "api" extra is installed
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── jobs.py                  # in-memory job store + per-job process orchestration
│   │   └── schemas.py               # API-only wrapper models (e.g. JobCreateResponse)
│   └── cli/                         # thin argparse/typer wrapper over core, replaces __main__.py
├── frontend/                        # React app (Vite + TypeScript), talks to api/ over HTTP only
└── docs/
    └── architecture/
```

## Dependency direction

- `core` has zero knowledge of FastAPI, uvicorn, or PySide6. It only depends on the algorithm libraries it actually needs (numpy, scipy, librosa, opencv, deffcode, pydantic).
- `api` depends on `core` (an internal import within the same package — no separate dependency declaration needed).
- `cli` depends only on `core` (not `api`).
- `frontend` depends on nothing Python — it talks to `api` over HTTP only.

## Single package, `api` as an optional extra

`core` and `api` ship in one PyPI distribution (`skelly_synchronize`), not as two separately published packages. `fastapi`/`uvicorn` are declared under an optional extra — `pip install skelly_synchronize[api]` — so a consumer who only wants the sync engine (`pip install skelly_synchronize`) doesn't pull in the web-server dependencies, without requiring a second PyPI distribution, a second version number, or a second release process.

This intentionally defers the earlier idea of publishing `core` as its own separately-versioned package. That split only pays for itself once something *outside this repo* — e.g. the main FreeMoCap pipeline — actually wants to `import` the sync engine in-process instead of calling the API over HTTP. There's no such consumer today, so the extra release/versioning overhead of a second distribution isn't justified yet. If that need materializes later, splitting `core` out into its own package is a mechanical refactor at that point — the module boundary already exists internally (see "Dependency direction" above) — not a redesign.

## Build backend

`flit_core` remains sufficient for a single-package distribution with an optional extra — no need to move to a workspace-oriented build backend now that there's only one package to build. Revisit only if the repo later grows back into multiple installable packages (see above).

## Naming

- One PyPI distribution: `skelly_synchronize`, continuing the existing published name.
- Console scripts: `skelly-sync` (CLI, replaces `python -m skelly_synchronize`/`__main__.py`) and `skelly-sync-api` (launches the FastAPI server via `uvicorn`; only functional if the `[api]` extra is installed).

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
