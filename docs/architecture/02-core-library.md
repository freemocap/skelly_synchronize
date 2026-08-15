# Core Library Design (`skelly_synchronize.core`)

## Goals

- Replace stringly-keyed dicts with typed models.
- Unify the audio and brightness orchestration paths, which today are almost entirely duplicated.
- Fix the concurrency/performance smells in trimming.
- Keep the library deployment-agnostic — it must work identically whether called from the CLI or from the FastAPI job runner, and must satisfy the `multiprocessing` picklability constraint the current codebase already depends on (per `CLAUDE.md`: per-video state passed into worker processes must stay picklable).

## Data models

All models are Pydantic `BaseModel`s, not plain dataclasses. This is a deliberate choice: `api` already requires Pydantic for FastAPI request/response validation, so sharing model definitions between `core` and `api` avoids a duplicate translation layer. The one exception is raw audio signal data (numpy arrays), which is kept **outside** any Pydantic model — large ndarrays don't serialize well and aren't meant to cross the API boundary — and instead passed alongside models as a plain `dict[str, np.ndarray]` keyed by video name.

```python
VideoName = str  # alias for clarity in signatures

class VideoInfo(BaseModel):
    filepath: Path
    video_name: str
    duration_seconds: float
    fps: float
    frame_count: int | None = None

class AudioInfo(BaseModel):
    filepath: Path
    video_name: str
    sample_rate: int
    duration_seconds: float
    # raw signal (np.ndarray) is intentionally NOT a field here

class SyncMethod(str, Enum):
    AUDIO = "audio"
    BRIGHTNESS = "brightness"

class LagResult(BaseModel):
    video_name: str
    lag_seconds: float
    confidence: float | None = None  # resolves KI-14

class SyncRequest(BaseModel):
    raw_video_folder_path: Path
    synchronized_video_folder_path: Path | None = None
    method: SyncMethod
    video_handler: VideoBackendKind = VideoBackendKind.DEFFCODE
    brightness_ratio_threshold: float = 1000.0  # only used when method == BRIGHTNESS
    create_debug_artifacts: bool = True

class SyncResult(BaseModel):
    synchronized_video_folder_path: Path
    videos_before: list[VideoInfo]
    videos_after: list[VideoInfo]
    lags: list[LagResult]
    debug_artifact_paths: list[Path]
    elapsed_seconds: float
```

### `LagResult` contract (resolves KI-02)

Every lag-producing algorithm (audio cross-correlation, brightness-change detection) must return `LagResult` values that share **one contract**: `lag_seconds` is the number of seconds to trim off the front of that specific video so that all videos align, normalized so the minimum lag across all videos is `0`. The current codebase normalizes this way for the audio path only and returns raw un-normalized values for the brightness path — this only "works" today because downstream trimming code happens to treat both the same way. In the rewrite, normalization happens once, centrally, right before `ComputeLagsStage` returns — not duplicated per-algorithm, and not left as an implicit assumption.

## `VideoBackend` interface (resolves KI-03)

```python
class VideoBackend(Protocol):
    def probe(self, filepath: Path) -> VideoInfo: ...
    def trim(self, filepath: Path, start_seconds: float, end_seconds: float | None, output_path: Path) -> Path: ...

class VideoBackendKind(str, Enum):
    FFMPEG = "ffmpeg"
    DEFFCODE = "deffcode"

def get_backend(kind: VideoBackendKind) -> VideoBackend: ...
```

`Protocol` is used instead of `ABC` — it gives structural typing and makes mocking backends in tests trivial (a test double just needs the right method signatures, no inheritance required), while still being fully checkable with mypy.

`FfmpegBackend` and `DeffcodeBackend` are the two concrete implementations. `DeffcodeBackend` preserves the existing rotation-metadata workaround (deffcode/ffmpeg auto-rotation combined with OpenCV's `VideoWriter` can double-apply rotation; the current code counters this with an explicit transpose filter keyed off `Sourcer`-reported orientation — this real-world fix must be carried forward, not rediscovered).

**Explicit policy**: probing always delegates to `FfmpegBackend` internally, regardless of which `VideoBackendKind` was requested for trimming, because ffprobe is more complete/reliable for metadata than deffcode. This was true implicitly in the old code (`create_video_info_dict` hard-coded `video_handler="ffmpeg"` for probing); the rewrite keeps the same behavior but makes it an explicit, documented method on `DeffcodeBackend.probe` (delegates to an internal `FfmpegBackend` instance) rather than an accidental gap in the caller's logic.

**Picklability**: only `VideoBackendKind` (a `str` enum) and the `get_backend` factory function are passed into `multiprocessing` worker processes — never a backend instance itself. This keeps worker task arguments trivially picklable regardless of what internal state a given backend implementation might hold.

## Pipeline abstraction (resolves KI-04, KI-05)

```python
class PipelineContext(BaseModel):
    request: SyncRequest
    videos: list[VideoInfo] = []
    normalized_folder_path: Path | None = None
    lags: list[LagResult] = []
    result: SyncResult | None = None
    # progress_callback is not a model field (not serializable) — threaded separately

class PipelineStage(Protocol):
    def run(self, context: PipelineContext, progress_callback: Callable[[str, float], None] | None) -> PipelineContext: ...
```

Shared stage list, used by **both** sync methods (this is what eliminates the current duplication between `synchronize_videos_from_audio` and `synchronize_videos_from_brightness`):

1. `DiscoverVideosStage` — find input video files.
2. `ProbeStage` — build `VideoInfo` for each (always via the ffmpeg-delegating probe path).
3. `NormalizeFramerateStage` — conditional: runs only if fps (or, for audio, sample rate) diverges across inputs; internally re-runs discovery/probe against its own output before returning, so callers never have to manually re-probe (resolves KI-05).
4. `ComputeLagsStage` — method-specific: `AudioLagStage` or `BrightnessLagStage`, both returning `LagResult`s satisfying the shared contract above.
5. `TrimStage` — parallel trim across videos.
6. `ReattachAudioStage` — audio method only.
7. `DebugArtifactsStage` — optional, gated by `SyncRequest.create_debug_artifacts`.

`SyncPipeline.run(request: SyncRequest, progress_callback=None) -> SyncResult` is the single public entry point. The old `synchronize_videos_from_audio`/`synchronize_videos_from_brightness` functions either become thin wrappers around `SyncPipeline.run(..., method=...)` for backward compatibility during the migration, or are removed once all callers (CLI, API) are updated to call `SyncPipeline` directly.

## Concurrency model for trimming

Replace `multiprocessing.Pool.starmap` with `concurrent.futures.ProcessPoolExecutor` + `as_completed`. This gives two things the current implementation lacks:

- **Per-task error isolation**: today, if one worker's `trim_single_video` raises, the whole `starmap` call surfaces a single aggregate failure with no partial-result visibility. `as_completed` lets the pipeline report exactly which video failed and why, while still letting sibling trims finish.
- **A natural hook for progress reporting**: each completed future can immediately report per-video progress instead of the pipeline blocking silently until every video is done.

Worker function signature takes only picklable arguments: `(video_info: VideoInfo, lag: LagResult, backend_kind: VideoBackendKind, output_dir: Path)`.

### Progress reporting (cross-referenced from `03-api-design.md`)

`core` exposes a generic, optional hook: `progress_callback: Callable[[str, float], None] | None`, threaded through `PipelineContext` and down into `TrimStage`. When run from the CLI it's a no-op or a simple print; when run from the API, `api` supplies a callback that writes into a `multiprocessing.Manager().dict()` created per job. **The mechanism lives in `api`, not `core`** — `core` stays deployment-agnostic and has no notion of "jobs" or shared process state; it just calls whatever callback it was given.

### Trim performance fix (resolves KI-06)

The deffcode trim path's current `frame_number in frame_list` check (O(n) list scan per decoded frame, O(n²) overall) is replaced with a `set[int]` membership test or, where the frame list is contiguous, a simple range check — O(1) per frame.

## Audio subsystem

- **Reference-video selection (resolves KI-13)**: today, `find_cross_correlation_lags` picks `next(iter(audio_signal_dict))`, an implicit dependency on alphabetical file-discovery order. The rewrite makes this an explicit, documented strategy — recommend "video with the longest audio duration" as a tie-break-free deterministic choice (falls back sensibly even if all durations happen to match, since ties then resolve to sorted-video-name order, which is still deterministic and documented).
- **In-memory reuse (resolves KI-12)**: `trim_audio_files` reuses the signal already loaded during extraction instead of reloading each `.wav` from disk.
- **Confidence score (resolves KI-14)**: `cross_correlate` additionally returns a confidence metric (e.g. ratio of the peak correlation value to the surrounding noise floor, or peak sharpness) that populates `LagResult.confidence`.
- **In-memory-only loading (KI-11)**: accepted as a documented v1 limitation given the local single-user, minutes-not-hours use case. Not addressed by streaming in this pass.

## Brightness subsystem

- **No side effects in computation (resolves KI-07)**: `compute_brightness_series(video: VideoInfo, backend: VideoBackend) -> np.ndarray` is a pure function. Persistence to a `.npy` sidecar becomes a separate, explicit `save_brightness_series(series, path)` call, made only by `DebugArtifactsStage` when debug artifacts are requested.
- **Explicit event result (resolves KI-08)**: `find_first_brightness_change` returns `BrightnessEvent | None` (carrying the detected frame index and its converted lag in seconds) instead of relying on an index-0 fallback as an implicit "not found" sentinel.

## Error handling (resolves KI-19)

A structured exception hierarchy replaces generic `RuntimeError`s:

```python
class SkellySyncError(Exception): ...
class VideoProbeError(SkellySyncError): ...
class BackendSubprocessError(SkellySyncError):
    def __init__(self, message: str, stderr: str, returncode: int | None, timed_out: bool): ...
```

All ffmpeg/ffprobe subprocess invocations are wrapped with an explicit timeout and, on failure, raise `BackendSubprocessError` carrying the captured stderr — today this is logged but dropped from the exception message itself, making failures hard to diagnose from just the raised error.

## Debug artifacts

- Fixes the brightness debug plot's mislabeled x-axis (KI-09): the axis is either correctly divided by fps to show real time, or explicitly labeled as frame index — not both mismatched as today.
- Fixes the `Path.exists` missing-parentheses bug (KI-10) in the branch that decides whether to source brightness debug data from the raw or normalized folder.

## Output format (KI-16)

Trimmed/normalized output remains `.mp4` regardless of input container — a deliberate, documented v1 decision that keeps backend code simple. Revisit only if a concrete need for preserving other containers arises.

## Known issues resolved by this document

KI-01, KI-02, KI-03, KI-04, KI-05, KI-06, KI-07, KI-08, KI-09, KI-10, KI-11 (documented, not fixed), KI-12, KI-13, KI-14, KI-16, KI-19.
