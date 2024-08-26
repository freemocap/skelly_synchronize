import logging
from pathlib import Path

from skelly_synchronize.system.file_extensions import VideoExtension
from skelly_synchronize.system.paths_and_file_names import SYNCED_VIDEO_PRECURSOR

logger = logging.getLogger(__name__)


def create_directory(parent_directory: Path, directory_name: str) -> Path:
    """Create a new directory under the specified parent directory."""
    parent_directory = Path(parent_directory)
    new_directory_path = parent_directory / directory_name

    try:
        new_directory_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {new_directory_path}")
    except Exception as e:
        logger.error(f"Error creating directory: {new_directory_path}. Exception: {e}")
        raise

    return new_directory_path


def name_synced_video(raw_video_filename: str) -> str:
    """Take a raw video filename, remove the raw prefix if its there, and return the synced video filename"""
    raw_video_filename = str(raw_video_filename)
    if raw_video_filename.split("_")[0] == "raw":
        synced_video_name = f"{SYNCED_VIDEO_PRECURSOR}{raw_video_filename[4:]}.{VideoExtension.MP4.value}"
    else:
        synced_video_name = (
            f"{SYNCED_VIDEO_PRECURSOR}{raw_video_filename}.{VideoExtension.MP4.value}"
        )

    return synced_video_name
