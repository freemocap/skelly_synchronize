import pytest
from pathlib import Path
from typing import Union

from skelly_synchronize.system.paths_and_file_names import (
    AUDIO_FILES_FOLDER_NAME,
    DEBUG_PLOT_NAME,
    DEBUG_TOML_NAME,
    TRIMMED_AUDIO_FOLDER_NAME,
)


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_synchronized_video_folder_exists(
    synchronized_video_folder_path: Union[str, Path]
):
    assert synchronized_video_folder_path.exists()


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_debug_plot_exists(synchronized_video_folder_path: Union[str, Path]):
    debug_plot_filepath = Path(synchronized_video_folder_path) / DEBUG_PLOT_NAME
    assert debug_plot_filepath.exists()


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_audio_files_folder_exists(synchronized_video_folder_path: Union[str, Path]):
    audio_files_folder = Path(synchronized_video_folder_path) / AUDIO_FILES_FOLDER_NAME
    assert audio_files_folder.exists()


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_trimmed_audio_folder_exists(synchronized_video_folder_path: Union[str, Path]):
    trimmed_audio_folder_filepath = (
        Path(synchronized_video_folder_path)
        / AUDIO_FILES_FOLDER_NAME
        / TRIMMED_AUDIO_FOLDER_NAME
    )
    assert trimmed_audio_folder_filepath.exists()


@pytest.mark.usefixtures("synchronized_video_folder_path")
def test_debug_toml_exists(synchronized_video_folder_path: Union[str, Path]):
    debug_toml_filepath = Path(synchronized_video_folder_path) / DEBUG_TOML_NAME
    assert debug_toml_filepath.exists()
