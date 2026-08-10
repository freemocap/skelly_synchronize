from pathlib import Path

from fastapi import APIRouter, HTTPException

from skelly_synchronize.api.schemas import VideoPreview, VideosResponse
from skelly_synchronize.core.discovery import get_video_file_list

router = APIRouter()


@router.get("/videos")
def list_videos(folder_path: Path) -> VideosResponse:
    if not folder_path.is_dir():
        raise HTTPException(
            status_code=404, detail=f"folder does not exist: {folder_path}"
        )

    video_paths = get_video_file_list(folder_path)
    videos = [VideoPreview(video_name=path.stem, filepath=path) for path in video_paths]
    return VideosResponse(folder_path=folder_path, videos=videos)
