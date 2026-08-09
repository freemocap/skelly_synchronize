import logging
from pathlib import Path

from skelly_synchronize.core.config import VideoExtension

logger = logging.getLogger(__name__)


def get_video_file_list(folder_path: Path) -> list[Path]:
    """Return a sorted list of unique video files in folder_path matching a supported extension."""
    folder_path = Path(folder_path)
    video_filepaths: list[Path] = []
    for extension in VideoExtension:
        video_filepaths.extend(folder_path.glob(f"*.{extension.value.upper()}"))
        video_filepaths.extend(folder_path.glob(f"*.{extension.value.lower()}"))

    # glob behaves differently on windows vs mac/linux; de-duplicate paths that
    # show up twice when the filesystem is case-insensitive.
    unique_filepaths = list(dict.fromkeys(video_filepaths))

    logger.info(f"{len(unique_filepaths)} videos found in folder {folder_path}")

    return sorted(unique_filepaths, key=lambda p: str(p).lower())
