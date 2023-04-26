import pytest
import sys
import logging
from pathlib import Path

print(f"Thank you for using skelly_synchronize!")
print(f"This is printing from: {__file__}")

base_package_path = Path(__file__).parent.parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

from skelly_synchronize.skelly_synchronize import VideoSynchronize
from skelly_synchronize.tests.utilities.find_frame_count_of_video import (
    find_frame_count_of_video,
)


@pytest.fixture
def test_video_pathstring():
    return "/Users/philipqueen/Documents/RawVideos/Cam0.MP4"


@pytest.fixture
def output_video_pathstring():
    return "/Users/philipqueen/Movies/ClippedCam0.mp4"


@pytest.fixture
def start_frame():
    return 1


@pytest.fixture
def desired_duration_frames():
    return 1500


def test_trim_single_video_deffcode(
    test_video_pathstring,
    start_frame,
    desired_duration_frames,
    output_video_pathstring,
    caplog,
):
    caplog.set_level(logging.INFO)
    test_synchronize = VideoSynchronize()
    test_synchronize._trim_single_video_deffcode(
        input_video_pathstring=test_video_pathstring,
        start_frame=start_frame,
        desired_duration_frames=desired_duration_frames,
        output_video_pathstring=output_video_pathstring,
    )

    assert find_frame_count_of_video(output_video_pathstring) == desired_duration_frames
