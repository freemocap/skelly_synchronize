"""API-only schema types with no equivalent in `core`.

`SyncRequest`/`SyncResult`/`Job` are used directly as request/response
schemas elsewhere -- this module only adds wrapper types the API needs on
top of those.
"""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from skelly_synchronize.api.jobs import JobStatus


class JobCreateResponse(BaseModel):
    job_id: UUID
    status: JobStatus


class VideoPreview(BaseModel):
    video_name: str
    filepath: Path


class VideosResponse(BaseModel):
    folder_path: Path
    videos: list[VideoPreview]
