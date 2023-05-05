import sys
import pytest
from pathlib import Path


print(f"Thank you for using skelly_synchronize!")
print(f"This is printing from: {__file__}")

base_package_path = Path(__file__).parent.parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

from skelly_synchronize.tests.utilities.load_sample_data import (
    find_synchronized_videos_folder_path,
    load_sample_data,
)
from skelly_synchronize.utils.get_video_files import get_video_file_list


def pytest_sessionstart():
    pytest.sample_session_folder_path = load_sample_data()
    video_folder_path = find_synchronized_videos_folder_path(
        pytest.sample_session_folder_path
    )
    pytest.video_file_list = get_video_file_list(
        folder_path=video_folder_path, file_type=".mp4"
    )


@pytest.fixture
def test_video_pathstring():
    return str(pytest.video_file_list[0])


@pytest.fixture
def output_video_pathstring():
    return str(pytest.sample_session_folder_path / "trimmed_sample_video.mp4")
