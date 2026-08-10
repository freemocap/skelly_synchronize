"""In-memory job store + per-job process orchestration.

Each job runs in its own OS process so a crashed/hung sync run can't take
down the API process, and `core`'s internal `ProcessPoolExecutor` (used for
parallel trimming) isn't nested inside a thread running an asyncio event
loop. Progress/result/error are bridged back via a `multiprocessing.Manager`
dict written to by the child process and read by the API process.
"""

import logging
import multiprocessing
import threading
from datetime import datetime, timezone
from enum import Enum
from multiprocessing.managers import DictProxy
from uuid import UUID, uuid4

from pydantic import BaseModel

from skelly_synchronize.core.discovery import get_video_file_list
from skelly_synchronize.core.exceptions import SkellySyncError
from skelly_synchronize.core.models import SyncRequest, SyncResult
from skelly_synchronize.core.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

_MAX_LISTED_JOBS = 20


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    id: UUID
    status: JobStatus
    progress: float = 0.0
    progress_message: str | None = None
    created_at: datetime
    updated_at: datetime
    request: SyncRequest
    result: SyncResult | None = None
    error: str | None = None


def _run_job(request: SyncRequest, shared: DictProxy) -> None:
    """Child-process entry point: run the pipeline, write progress/outcome to `shared`.

    Must stay a top-level function (not a closure/method) so it can be
    pickled by `multiprocessing`.
    """
    shared["status"] = JobStatus.RUNNING.value

    total_videos = len(get_video_file_list(request.raw_video_folder_path)) or 1
    completed_videos: set[str] = set()

    def progress_callback(video_name: str, progress: float) -> None:
        if progress >= 1.0:
            completed_videos.add(video_name)
        shared["progress"] = len(completed_videos) / total_videos
        shared["progress_message"] = f"trimmed {video_name}"

    try:
        result = run_pipeline(request, progress_callback)
    except SkellySyncError as e:
        shared["status"] = JobStatus.FAILED.value
        shared["error"] = str(e)
        return

    shared["status"] = JobStatus.SUCCEEDED.value
    shared["progress"] = 1.0
    shared["result"] = result.model_dump(mode="json")


class JobStore:
    """Guards job bookkeeping with a lock; job execution itself lives in child processes."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}
        self._handles: dict[UUID, tuple[multiprocessing.Process, DictProxy]] = {}
        self._lock = threading.Lock()
        self._manager: multiprocessing.managers.SyncManager | None = None

    def _get_manager(self) -> multiprocessing.managers.SyncManager:
        # Created lazily rather than in __init__: `job_store` is a module-level
        # singleton, so eagerly starting a Manager (itself a subprocess) as an
        # import-time side effect makes every spawn-based child process that
        # re-imports this module attempt to start its own Manager recursively.
        if self._manager is None:
            self._manager = multiprocessing.Manager()
        return self._manager

    def create(self, request: SyncRequest) -> Job:
        if not request.raw_video_folder_path.is_dir():
            raise FileNotFoundError(
                f"raw video folder does not exist: {request.raw_video_folder_path}"
            )

        job_id = uuid4()
        now = datetime.now(timezone.utc)
        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            request=request,
        )
        shared = self._get_manager().dict(
            status=JobStatus.PENDING.value,
            progress=0.0,
            progress_message=None,
            result=None,
            error=None,
        )
        process = multiprocessing.Process(target=_run_job, args=(request, shared))

        with self._lock:
            self._jobs[job_id] = job
            self._handles[job_id] = (process, shared)

        process.start()
        return job

    def _refresh(self, job_id: UUID) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            handle = self._handles.get(job_id)
        if job is None or handle is None:
            return None

        _, shared = handle
        result_data = shared.get("result")
        updated = job.model_copy(
            update={
                "status": JobStatus(shared.get("status", job.status.value)),
                "progress": shared.get("progress", job.progress),
                "progress_message": shared.get("progress_message"),
                "result": (
                    SyncResult.model_validate(result_data)
                    if result_data is not None
                    else None
                ),
                "error": shared.get("error"),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        with self._lock:
            self._jobs[job_id] = updated
        return updated

    def get(self, job_id: UUID) -> Job | None:
        return self._refresh(job_id)

    def list(self, limit: int = _MAX_LISTED_JOBS) -> list[Job]:
        with self._lock:
            job_ids = list(self._jobs.keys())
        jobs = [self._refresh(job_id) for job_id in job_ids]
        jobs = [job for job in jobs if job is not None]
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs[:limit]

    def cancel(self, job_id: UUID) -> Job | None:
        with self._lock:
            handle = self._handles.get(job_id)
        if handle is None:
            return None

        process, shared = handle
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            shared["status"] = JobStatus.CANCELLED.value
        return self._refresh(job_id)


job_store = JobStore()


def get_job_store() -> JobStore:
    return job_store
