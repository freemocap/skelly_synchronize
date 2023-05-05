import pytest
import sys
import logging
from pathlib import Path

print(f"Thank you for using skelly_synchronize!")
print(f"This is printing from: {__file__}")

base_package_path = Path(__file__).parent.parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

from skelly_synchronize.tests.utilities.find_frame_count_of_video import (
    find_frame_count_of_video,
)
from skelly_synchronize.core_processes.video_functions.deffcode_functions import (
    trim_single_video_deffcode,
)


@pytest.fixture
def test_video_pathstring():
    return "/Users/philipqueen/Documents/RawVideos/Cam0.MP4"


@pytest.fixture
def output_video_pathstring():
    return "/Users/philipqueen/Movies/ClippedCam0.mp4"

@pytest.fixture 
def frame_list():
    start_frame = 1
    duration_frames = 500
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
