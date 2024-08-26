import logging
from pathlib import Path

from skelly_synchronize.system.file_extensions import VideoExtension

logger = logging.getLogger(__name__)


def get_video_file_list(folder_path: Path) -> list:
    """Return a list of all video files in the base_path folder that match a video file type"""
    list_of_video_formats = [extension.value for extension in VideoExtension]

    video_filepath_list = []
    for file_type in list_of_video_formats:
        file_extension_upper = "*" + file_type.upper()
        file_extension_lower = "*" + file_type.lower()

        video_filepath_list.extend(list(folder_path.glob(file_extension_upper)))
        video_filepath_list.extend(list(folder_path.glob(file_extension_lower)))

    # because glob behaves differently on windows vs. mac/linux, we collect all files both upper and lowercase, and remove redundant files that appear on windows
    unique_video_filepath_list = get_unique_list(video_filepath_list)

    logger.info(f"{len(unique_video_filepath_list)} videos found in folder")

    return unique_video_filepath_list


def get_unique_list(list: list) -> list:
    """Return a list of the unique elements from input list"""
    unique_list = []
    [unique_list.append(clip) for clip in list if clip not in unique_list]
    return unique_list
