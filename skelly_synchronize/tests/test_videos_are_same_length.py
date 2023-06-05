import pytest
from pathlib import Path
from typing import Union

from skelly_synchronize.tests.utilities.check_list_values_are_equal import (
    check_list_values_are_equal,
)
from skelly_synchronize.tests.utilities.get_number_of_frames_of_videos_in_a_folder import (
    get_number_of_frames_of_videos_in_a_folder,
)


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_videos_are_same_length(synchronized_video_folder_path: Union[str, Path]):
    synchronized_video_framecounts = get_number_of_frames_of_videos_in_a_folder(
        folder_path=synchronized_video_folder_path
    )
    assert isinstance(
        check_list_values_are_equal(synchronized_video_framecounts), (int, float)
    )
