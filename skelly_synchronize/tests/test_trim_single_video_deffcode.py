import pytest
import logging


from skelly_synchronize.tests.utilities.find_frame_count_of_video import (
    find_frame_count_of_video,
)
from skelly_synchronize.core_processes.video_functions.deffcode_functions import (
    trim_single_video_deffcode,
)


@pytest.fixture
def frame_list():
    start_frame = 10
    duration_frames = 200
    return [start_frame + frame for frame in range(duration_frames)]


def test_trim_single_video_deffcode(
    test_video_pathstring: str,
    frame_list: list,
    output_video_pathstring: str,
    caplog,
):
    caplog.set_level(logging.INFO)
    trim_single_video_deffcode(
        input_video_pathstring=test_video_pathstring,
        frame_list=frame_list,
        output_video_pathstring=output_video_pathstring,
    )

    assert find_frame_count_of_video(output_video_pathstring) == len(frame_list)
