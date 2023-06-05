import pytest
from typing import Union
from pathlib import Path

from skelly_synchronize.utils.get_video_files import get_video_file_list


@pytest.mark.usefixtures("raw_video_folder_path", "synchronized_video_folder_path")
def test_number_of_videosis_preserved(
    raw_video_folder_path: Union[str, Path],
    synchronized_video_folder_path: Union[str, Path],
):
    assert len(get_video_file_list(folder_path=raw_video_folder_path)) == len(
        get_video_file_list(folder_path=synchronized_video_folder_path)
    )
