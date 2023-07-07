import logging
import sys
from pathlib import Path
from typing import Union

base_package_path = Path(__file__).parent.parent.parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

from skelly_synchronize.utils.get_video_files import get_video_file_list
from skelly_synchronize.tests.utilities.find_frame_count_of_video import (
    find_frame_count_of_video,
)

logger = logging.getLogger(__name__)


def get_number_of_frames_of_videos_in_a_folder(folder_path: Union[str, Path]):
    """
    Get the number of frames in the first video in a folder
    """

    list_of_video_paths = get_video_file_list(
        folder_path=Path(folder_path), file_type=".mp4"
    )

    if len(list_of_video_paths) == 0:
        logger.error(f"No videos found in {folder_path}")
        return None

    frame_count_list = []
    for video_path in list_of_video_paths:
        frame_count = find_frame_count_of_video(video_pathstring=str(video_path))
        frame_count_list.append(int(frame_count))

    return frame_count_list


if __name__ == "__main__":
    folder_path = Path("YOUR/FOLDER/PATH")
    print(get_number_of_frames_of_videos_in_a_folder(folder_path))
