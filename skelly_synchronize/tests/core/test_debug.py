from pathlib import Path

import toml

from skelly_synchronize.core.debug import save_debug_toml
from skelly_synchronize.core.models import LagResult, VideoInfo


def _make_video_info(camera_name: str, fps: float = 29.97) -> VideoInfo:
    return VideoInfo(
        filepath=Path(f"{camera_name}.mp4"),
        camera_name=camera_name,
        duration_seconds=10.0,
        fps=fps,
    )


def test_save_debug_toml_surfaces_synchronized_fps(tmp_path):
    output_path = tmp_path / "synchronization_debug.toml"

    save_debug_toml(
        output_path,
        videos_before=[
            _make_video_info("cam_a", fps=30.0),
            _make_video_info("cam_b", fps=29.97),
        ],
        videos_after=[
            _make_video_info("synced_cam_a"),
            _make_video_info("synced_cam_b"),
        ],
        lags=[LagResult(camera_name="cam_a", lag_seconds=0.0)],
        synchronized_fps=29.97,
        synchronized_frame_count=872,
    )

    data = toml.load(output_path)

    assert data["synchronized_video_fps"] == 29.97
    assert data["synchronized_video_frame_count"] == 872


def test_save_debug_toml_omits_synchronized_fields_when_unknown(tmp_path):
    output_path = tmp_path / "synchronization_debug.toml"

    save_debug_toml(
        output_path,
        videos_before=[],
        videos_after=[],
        lags=[],
        synchronized_fps=None,
        synchronized_frame_count=None,
    )

    data = toml.load(output_path)

    assert "synchronized_video_fps" not in data
    assert "synchronized_video_frame_count" not in data
