from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from skelly_synchronize.api.jobs import Job, JobStatus, JobStore, get_job_store
from skelly_synchronize.api.schemas import JobCreateResponse
from skelly_synchronize.core.config import DEBUG_PLOT_NAME
from skelly_synchronize.core.models import SyncRequest

router = APIRouter()

JobStoreDep = Annotated[JobStore, Depends(get_job_store)]


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(request: SyncRequest, job_store: JobStoreDep) -> JobCreateResponse:
    try:
        job = job_store.create(request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, job_store: JobStoreDep) -> Job:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job


@router.get("/jobs")
def list_jobs(job_store: JobStoreDep) -> list[Job]:
    return job_store.list()


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: UUID, job_store: JobStoreDep) -> Job:
    job = job_store.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return job


@router.get("/jobs/{job_id}/debug-plot")
def get_debug_plot(job_id: UUID, job_store: JobStoreDep) -> FileResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    if job.status != JobStatus.SUCCEEDED or job.result is None:
        raise HTTPException(status_code=404, detail=f"job has no debug plot: {job_id}")

    plot_path = next(
        (p for p in job.result.debug_artifact_paths if p.name == DEBUG_PLOT_NAME),
        None,
    )
    if plot_path is None or not plot_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"debug plot not found for job: {job_id}"
        )

    return FileResponse(plot_path)
