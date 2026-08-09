# FastAPI Service Design (`skelly_sync_api`)

## Deployment model

Localhost-only, single-user. The API is launched locally via the `skelly-sync-api` console script (wrapping `uvicorn app:app --host 127.0.0.1`) and is meant to run on the same machine as the browser tab serving the React frontend. There is no authentication, no multi-tenancy, and no need for hardened CORS — CORS is configured permissively for `http://localhost:*` origins purely to support local development where the Vite dev server and the API run on different ports.

## Job model and storage

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class Job(BaseModel):
    id: UUID
    status: JobStatus
    progress: float = 0.0            # 0.0 - 1.0
    progress_message: str | None = None
    created_at: datetime
    updated_at: datetime
    request: SyncRequest             # reused directly from skelly_sync_core
    result: SyncResult | None = None
    error: str | None = None
```

**Storage: in-memory `dict[UUID, Job]` guarded by a lock — not SQLite.** This is a deliberate choice for a local single-user app: jobs are ephemeral coordination state, and the actual durable output of a sync run is the files it writes to disk. There is no requirement to recover job history across a server restart. Adding SQLite (schema, migrations) would be overhead with no corresponding benefit here. Trade-off, stated explicitly: restarting the API process loses in-flight and historical job records — acceptable, since the user can simply re-run a sync against the same input folder.

**Job execution**: each job runs in its own OS process (not just a thread), launched from the job-creation endpoint. This gives two things: a crashed or hung sync job can't take down the API process itself, and `core`'s own `ProcessPoolExecutor` (used internally for parallel trimming) isn't nested awkwardly inside a thread running an asyncio event loop.

### Progress bridge

For each job, `api` creates a `multiprocessing.Manager().dict()` and passes a callback into `SyncPipeline.run(request, progress_callback=callback)` (see [02-core-library.md](02-core-library.md#concurrency-model-for-trimming)) that writes `{stage_name, fraction_complete}` updates into that shared dict. A lightweight read path (either a background poller updating the in-memory `Job`, or the `GET /jobs/{id}` handler reading the Manager dict directly) surfaces this as `Job.progress`/`Job.progress_message`. This keeps `core` itself unaware of "jobs" — it only ever sees a generic callback.

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness check, `{"status": "ok"}`. |
| `GET /cameras?folder_path=...` | Validates a folder path and returns the discovered video files/camera names, using `core`'s discovery stage standalone — lets the frontend show a preview before a job is started. |
| `POST /jobs` | Body: `SyncRequest`. Starts a job in a new process, returns `201 {job_id, status: "pending"}` immediately. |
| `GET /jobs/{job_id}` | Returns the full `Job` — status, progress, progress_message, `result` if succeeded, `error` if failed. |
| `GET /jobs` | Lists recent jobs (in-memory, capped at e.g. the last 20) — powers a simple job-history panel. |
| `DELETE /jobs/{job_id}` | Best-effort cancellation: terminates the job's OS process and marks it `CANCELLED` (add to `JobStatus`) if implemented in this pass; otherwise explicitly out of scope for v1 and documented as returning `501`. |
| `GET /jobs/{job_id}/debug-plot` | Serves the `debug_plot.png` artifact directly, so the frontend can embed it via `<img src="...">`. Only meaningful if the job's `SyncRequest.create_debug_artifacts` was true. |

## Request/response schemas

`SyncRequest`, `Job`, and `SyncResult` are the `core` Pydantic models used directly as FastAPI request/response schemas — no separate duplicate schema layer. `skelly_sync_api/schemas.py` only defines API-specific wrapper types that have no equivalent in `core`, such as `JobCreateResponse`.

## Error handling

A FastAPI exception handler maps `core`'s exception hierarchy (see [02-core-library.md](02-core-library.md#error-handling-resolves-ki-19)) to HTTP status codes:

| `core` exception | HTTP status |
|---|---|
| Folder not found / invalid input path | 404 |
| `VideoProbeError` | 422 |
| `BackendSubprocessError` | 500, with `stderr` included in the response `detail` |
| Any other unhandled `SkellySyncError` | 500 |

## Polling contract (for the frontend)

The frontend polls `GET /jobs/{id}` on a fixed interval — recommend **1 second** — while `status` is `pending` or `running`, and stops polling once a terminal status (`succeeded`, `failed`, or `cancelled`) is reached. This contract is defined here once and simply referenced from [04-frontend.md](04-frontend.md) rather than re-derived there.

## Manual testing during development

FastAPI's auto-generated `/docs` (Swagger UI) is sufficient for manually exercising every endpoint during the phase where the API exists but the React frontend does not yet (see the phased plan in [README.md](README.md)) — no separate manual-testing tooling is needed for that phase.

## Known issues resolved by this document

KI-22 (GUI-thread-blocking sync replaced by an async job model), KI-24 (no API/service boundary — this is the boundary), and (with [02-core-library.md](02-core-library.md)) KI-14 (confidence surfaced through the job result).
