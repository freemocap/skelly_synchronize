# skelly_synchronize Rearchitecture — Target Architecture

This directory describes the **target** architecture for the `skelly_synchronize` rewrite. It exists to guide implementation, not to document the system as it is today — the current architecture is referenced only for contrast or rationale where useful. See [00-known-issues.md](00-known-issues.md) for the full list of current bugs/smells and where each is resolved.

## Goals

1. Improve the code quality of the core synchronization library — typed data models, a proper backend abstraction, unified pipeline orchestration, and fixes to the concurrency/correctness smells listed in [00-known-issues.md](00-known-issues.md).
2. Add a FastAPI server exposing sync functionality over HTTP.
3. Replace the PySide6 desktop GUI with a simple React frontend.

**Done** looks like: a `core` library with typed models and no known-issue regressions, a FastAPI server backing all the functionality the old GUI exposed (plus previously-hidden parameters it never surfaced), and a React frontend at feature parity with the old GUI — after which the PySide6 GUI package is deleted.

## Document map

| Doc | Purpose |
|---|---|
| [00-known-issues.md](00-known-issues.md) | Numbered `KI-##` list of current bugs/smells and where each is resolved — the checklist nothing should silently reproduce. |
| [01-package-layout.md](01-package-layout.md) | Target repo/module structure, monorepo layout, packaging and build decisions. |
| [02-core-library.md](02-core-library.md) | `skelly_sync_core` design: typed data models, `VideoBackend` interface, pipeline abstraction, concurrency model. |
| [03-api-design.md](03-api-design.md) | `skelly_sync_api` design: FastAPI endpoints, schemas, job model, progress bridge. |
| [04-frontend.md](04-frontend.md) | React app: screens, API client, state management approach. |
| [05-testing-strategy.md](05-testing-strategy.md) | Test pyramid across `core`/`api`/frontend, fixture redesign, CI plan. |

Read in the numbered order above — each later doc assumes the decisions made in the earlier ones (package boundaries before core design, core design before the API that wraps it, API before the frontend that consumes it).

## Target architecture at a glance

```
        ┌────────────┐
        │  frontend  │  React (Vite + TS) — talks HTTP only
        └─────┬──────┘
              │ HTTP (polling)
        ┌─────▼──────┐
        │    api     │  FastAPI (skelly_sync_api) — job orchestration, HTTP boundary
        └─────┬──────┘
              │ Python calls
        ┌─────▼──────┐       ┌────────────┐
        │    core    │◄──────┤    cli     │  both depend only on core
        │(skelly_sync_core)  └────────────┘
        └────────────┘
```

`core` has no knowledge of `api` or `frontend`. `api` and `cli` are both thin consumers of `core`, so the sync engine is usable standalone (scriptable, embeddable in other tools) independent of whether the API/frontend exist at all. See [01-package-layout.md](01-package-layout.md) for the full package tree.

## Non-goals

- No authentication or multi-user support — this is a local, single-user tool (see the deployment model in [03-api-design.md](03-api-design.md)).
- No cloud/object storage — plain local filesystem paths, same usage model as today.
- No mobile support.
- No plugin/extension system.

## Phased migration plan

The rewrite proceeds in phases. **Each phase ends with the tool still fully usable end-to-end** — never a broken intermediate state — so the team (or a single developer) can pause between phases without leaving the tool unusable.

1. **Phase 0 — scaffold `core`.** Stand up the new package layout, typed models, and the `VideoBackend` protocol with only the `FfmpegBackend` implementation. Port logic incrementally with unit tests. Keep the *old* `skelly_synchronize.py` entry points working by delegating internally to the new pipeline where practical, so the existing PySide6 GUI keeps functioning throughout this phase.
2. **Phase 1 — finish the `core` rewrite.** Complete the pipeline abstraction, the brightness path, the `DeffcodeBackend`, the audio subsystem, and debug artifacts. The old GUI now runs entirely against the new `core` library — this phase proves `core`'s public surface is sufficient before any API work begins.
3. **Phase 2 — FastAPI layer.** Build `skelly_sync_api` wrapping the now-finished `core`, starting with an in-memory job store. Test manually via the FastAPI-generated `/docs` UI — no frontend exists yet.
4. **Phase 3 — React frontend.** Build the frontend against the FastAPI layer from Phase 2. Once it reaches feature parity with the old GUI, delete the PySide6 GUI package entirely.
5. **Phase 4 — cleanup.** Remove any remaining old dict-based code paths, finalize packaging/CI per [01-package-layout.md](01-package-layout.md) and [05-testing-strategy.md](05-testing-strategy.md), update the top-level README, and tag a release.

## Key decisions at a glance

| Decision | Choice | Rationale (detail in linked doc) |
|---|---|---|
| Job storage | In-memory dict + lock, no SQLite | Jobs are ephemeral; durable output is the files on disk. [03-api-design.md](03-api-design.md) |
| `core` as a separate installable package | Yes — `skelly_sync_core` | Reusable independent of FastAPI/PySide6. [01-package-layout.md](01-package-layout.md) |
| Repo structure | Monorepo: `packages/core`, `packages/api`, `cli/`, `frontend/` | Single release cadence, no cross-repo coordination overhead. [01-package-layout.md](01-package-layout.md) |
| Frontend location | Same repo, `frontend/` | See above. [01-package-layout.md](01-package-layout.md) |
| Progress reporting | `core` exposes a generic callback hook; `api` supplies the actual mechanism | Keeps `core` deployment-agnostic. [02-core-library.md](02-core-library.md), [03-api-design.md](03-api-design.md) |
| Typed data model approach | Pydantic throughout `core`/`api` (raw audio arrays excluded) | Avoids a dataclass↔Pydantic translation layer since FastAPI already requires Pydantic. [02-core-library.md](02-core-library.md) |
| Long-running job UX | Async job + polling (not WebSockets) | Simple, sufficient for a local single-user app. [03-api-design.md](03-api-design.md) |
