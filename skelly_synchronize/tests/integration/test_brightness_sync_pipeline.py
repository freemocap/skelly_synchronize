from pathlib import Path
from typing import Callable

import pytest

from skelly_synchronize.core.config import DEBUG_PLOT_NAME, DEBUG_TOML_NAME
from skelly_synchronize.core.discovery import get_video_file_list
from skelly_synchronize.core.models import SyncMethod, SyncRequest, VideoBackendKind
from skelly_synchronize.core.pipeline.runner import run_pipeline

# cam_a's flash fires 1s later, within its own timeline, than cam_b's --
# equivalent to cam_a having started recording 1s earlier than cam_b relative
# to the same real-world flash event. See skelly_synchronize/tests/fixtures/README.md.
EXPECTED_LAG_SECONDS = {"cam_a": 0.0, "cam_b": 1.0}
LAG_TOLERANCE_SECONDS = 0.05


@pytest.mark.parametrize(
    "video_handler", [VideoBackendKind.FFMPEG, VideoBackendKind.DEFFCODE]
)
def test_brightness_sync_pipeline_end_to_end(
    raw_video_folder_factory: Callable[[str], Path], video_handler: VideoBackendKind
):
    raw_video_folder_path = raw_video_folder_factory("brightness_sync")

    request = SyncRequest(
        raw_video_folder_path=raw_video_folder_path,
        method=SyncMethod.BRIGHTNESS,
        video_handler=video_handler,
    )

    result = run_pipeline(request)

    assert result.synchronized_video_folder_path.exists()

    lags_by_camera = {lag.camera_name: lag.lag_seconds for lag in result.lags}
    for camera_name, expected_lag in EXPECTED_LAG_SECONDS.items():
        assert lags_by_camera[camera_name] == pytest.approx(
            expected_lag, abs=LAG_TOLERANCE_SECONDS
        )

    synced_video_paths = get_video_file_list(result.synchronized_video_folder_path)
    assert len(synced_video_paths) == len(EXPECTED_LAG_SECONDS)

    assert result.synchronized_frame_count is not None
    assert result.synchronized_frame_count > 0

    debug_toml_path = result.synchronized_video_folder_path / DEBUG_TOML_NAME
    debug_plot_path = result.synchronized_video_folder_path / DEBUG_PLOT_NAME
    assert debug_toml_path.exists()
    assert debug_plot_path.exists()
