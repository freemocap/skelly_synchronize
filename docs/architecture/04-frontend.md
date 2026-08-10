# Frontend Design (React)

## Purpose

Design for the React app that replaces the PySide6 desktop GUI. Kept deliberately simple, matching the project's own framing of "a simple react one" and the small number of screens the tool actually needs.

## Tech choices

- **Vite + React + TypeScript.** No Next.js or other SSR/routing framework — there's no server-rendering or routing complexity that justifies it for a 2–4 screen local tool.
- **API client**: a small, hand-written `src/api/client.ts` with TypeScript interfaces mirroring the Pydantic models defined in [03-api-design.md](03-api-design.md) (`SyncRequest`, `Job`, `SyncResult`, ...), wrapping plain `fetch`. The API surface is small enough that generated-client tooling (e.g. `openapi-typescript`) is a nice-to-have for later, not required for v1.

## State management

**No Redux, Zustand, or other state library.** Plain React state (`useState`/`useReducer`) plus one custom hook, `useJobPolling(jobId)`, that polls `GET /jobs/{id}` on the interval defined in [03-api-design.md](03-api-design.md#polling-contract-for-the-frontend) (1s) and exposes `{status, progress, progressMessage, result, error}`, stopping automatically once a terminal status is reached. This matches the app's small size — a state library would be pure overhead here.

## Screens

### Setup screen

Replaces today's GUI, which only exposes 2 of the several parameters `core` actually supports. The new setup screen exposes all of them:

- Raw video folder path — a plain text input for an absolute path, not a browser file picker. (Browsers cannot reliably expose real filesystem *paths* from a picker due to the File System Access API's security model, and since the API and browser run on the same machine here, a plain path field is simpler and fully sufficient — documented explicitly as the reason, not an oversight.)
- Sync method selector (audio / brightness).
- Backend selector (ffmpeg / deffcode) — newly exposed; today's GUI has no way to choose this.
- Brightness ratio threshold field — shown only when brightness is selected (matches today's one exposed parameter).
- Debug-artifacts toggle — newly exposed.
- Optional custom output folder path — newly exposed (`core` already supports overriding `synchronized_video_folder_path`; the GUI never surfaced it).
- "Start sync" button — `POST /jobs`, then navigates to the Job Progress screen with the returned `job_id`.

### Job Progress screen

- Progress bar and status text driven by `useJobPolling`.
- Cancel button, wired to `DELETE /jobs/{id}` if implemented server-side; otherwise omitted/disabled with a tooltip noting it's not yet supported (mirrors the "may be out of scope for v1" note in [03-api-design.md](03-api-design.md)).
- On `succeeded`, navigates to the Result screen; on `failed`, shows the error inline (see Error display below) with an option to return to Setup.

### Result screen

- Per-video lag summary table (`video_name`, `lag_seconds`, `confidence`) from `SyncResult.lags`.
- Debug plot image, `<img src="/jobs/{id}/debug-plot">`, shown only if debug artifacts were requested.
- Output folder path, shown as selectable text (a browser page cannot open a native file-manager window — documented as a known limitation rather than attempted).
- "Run another sync" button, returns to Setup.

### History screen (optional / stretch)

Lists recent jobs from `GET /jobs`; clicking one re-displays its Result screen. Explicitly marked optional — not required for feature parity with the current GUI, which has no history at all.

## Error display (resolves part of KI-22)

Today, sync errors are only visible in logs/stdout — the GUI has no error dialog. The new frontend shows inline error banners on the relevant screen, reading either `Job.error` (job-level failures) or the HTTP response's `detail` field (request-level failures, e.g. an invalid folder path from `GET /videos` or `POST /jobs`).

## Styling

Minimal, plain CSS (or CSS Modules) — no heavyweight design system or component library. This is a small internal tool, and adding a design system would be effort disproportionate to its scope.

## Dev / run model

**v1**: two processes — `skelly-sync-api` (FastAPI/uvicorn on `127.0.0.1:8000`) and `npm run dev` (Vite dev server, proxying API calls to the FastAPI port). The user runs both and opens the Vite dev server URL in a browser.

Bundling the frontend as static files served directly by FastAPI (a single-process app, closer to the original desktop-app feel) is deferred to a later polish phase, once the API/frontend split has proven itself — not attempted in the initial rewrite.

## Location

Lives in-repo under `frontend/`, per the monorepo decision in [01-package-layout.md](01-package-layout.md).

## Known issues resolved by this document

KI-22 (blocking, feedback-less sync UI replaced by an async progress screen with error display), and the parameter-exposure gap noted in the current GUI (only 2 of several `core` parameters were ever surfaced).
