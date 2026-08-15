from pathlib import Path

import pytest

from skelly_synchronize.core.config import DEBUG_PLOT_NAME, DEBUG_TOML_NAME
from skelly_synchronize.core.discovery import get_video_file_list
from skelly_synchronize.core.models import SyncMethod, SyncRequest
from skelly_synchronize.core.pipeline.runner import run_pipeline

pytestmark = pytest.mark.slow


def test_audio_sync_pipeline_against_sample_dataset(
    sample_dataset_raw_video_folder_path: Path, tmp_path: Path
):
    request = SyncRequest(
        raw_video_folder_path=sample_dataset_raw_video_folder_path,
        synchronized_video_folder_path=tmp_path / "synchronized_videos",
        method=SyncMethod.AUDIO,
    )

    result = run_pipeline(request)

    assert result.synchronized_video_folder_path.exists()

    raw_video_paths = get_video_file_list(sample_dataset_raw_video_folder_path)
    synced_video_paths = get_video_file_list(result.synchronized_video_folder_path)
    assert len(raw_video_paths) == len(synced_video_paths)

    assert result.synchronized_frame_count is not None
    assert result.synchronized_frame_count > 0
    assert all(
        video.frame_count == result.synchronized_frame_count
        for video in result.videos_after
    )

    assert (result.synchronized_video_folder_path / DEBUG_TOML_NAME).exists()
    assert (result.synchronized_video_folder_path / DEBUG_PLOT_NAME).exists()
