from pathlib import Path

import pytest
from pydantic import ValidationError

from skelly_synchronize.core.models import (
    LagResult,
    SyncMethod,
    SyncResult,
    VideoBackendKind,
    VideoInfo,
)


def test_video_info_requires_all_fields():
    with pytest.raises(ValidationError):
        VideoInfo(filepath=Path("video.mp4"), video_name="cam_1")

    video_info = VideoInfo(
        filepath=Path("video.mp4"),
        video_name="cam_1",
        duration_seconds=10.0,
        fps=30.0,
    )
    assert video_info.frame_count is None


def test_lag_result_confidence_is_optional():
    lag_result = LagResult(video_name="cam_1", lag_seconds=0.5)
    assert lag_result.confidence is None


def test_sync_method_values():
    assert SyncMethod.AUDIO == "audio cross-correlation"
    assert SyncMethod.BRIGHTNESS == "brightness change detection"


def test_video_backend_kind_values():
    assert VideoBackendKind.FFMPEG == "ffmpeg"
    assert VideoBackendKind.DEFFCODE == "deffcode"


def test_sync_result_synchronized_frame_count_defaults_to_none():
    result = SyncResult(
        synchronized_video_folder_path=Path("synchronized_videos"),
        videos_before=[],
        videos_after=[],
        lags=[],
        debug_artifact_paths=[],
        elapsed_seconds=1.0,
    )
    assert result.synchronized_frame_count is None
