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

- Raw video folder path — a text input for an absolute path, plus a "Browse…" button that opens a native OS folder picker via the Tauri shell (`@tauri-apps/plugin-dialog`, see [06-tauri-desktop.md](06-tauri-desktop.md)), which returns a real absolute path directly. (Earlier versions of this doc specified a plain text-only field, reasoning that a browser-only frontend cannot reliably obtain real filesystem *paths* from a picker due to the File System Access API's security model — that constraint no longer applies now that the frontend only runs inside the Tauri shell, which does have real filesystem access.)
- Sync method selector (audio / brightness).
- Backend selector (ffmpeg / deffcode) — newly exposed; today's GUI has no way to choose this.
- Brightness ratio threshold field — shown only when brightness is selected (matches today's one exposed parameter).
- Debug-artifacts toggle — newly exposed.
- Optional custom output folder path — newly exposed (`core` already supports overriding `synchronized_video_folder_path`; the GUI never surfaced it). Same text input + native-picker "Browse…" pattern as the raw folder path field above.
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

Superseded by [06-tauri-desktop.md](06-tauri-desktop.md): the frontend runs only inside a Tauri desktop shell, which manages the API as a sidecar process, rather than a developer/user starting `skelly-sync-api` and a Vite dev server by hand and opening a browser tab. `npm run tauri dev` (dev) / `npm run tauri build` (release) replace the old two-process model.

## Location

Lives in-repo under `frontend/`, per the monorepo decision in [01-package-layout.md](01-package-layout.md).

## Known issues resolved by this document

KI-22 (blocking, feedback-less sync UI replaced by an async progress screen with error display), and the parameter-exposure gap noted in the current GUI (only 2 of several `core` parameters were ever surfaced). The folder-picker limitation noted earlier in this document is now actually resolved rather than merely accepted, once the frontend runs inside the Tauri shell — see [06-tauri-desktop.md](06-tauri-desktop.md).
