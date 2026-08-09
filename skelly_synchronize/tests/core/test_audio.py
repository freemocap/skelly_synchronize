from pathlib import Path

import numpy as np

from skelly_synchronize.core.audio import (
    cross_correlate,
    find_cross_correlation_lags,
    get_reference_camera_name,
    trim_audio_in_memory,
)
from skelly_synchronize.core.models import LagResult, VideoInfo


def _make_video_info(camera_name: str, duration_seconds: float) -> VideoInfo:
    return VideoInfo(
        filepath=Path(f"{camera_name}.mp4"),
        camera_name=camera_name,
        duration_seconds=duration_seconds,
        fps=30.0,
    )


def test_get_reference_camera_name_picks_longest_duration():
    videos = [
        _make_video_info("cam_a", 10.0),
        _make_video_info("cam_b", 12.0),
        _make_video_info("cam_c", 11.0),
    ]
    assert get_reference_camera_name(videos) == "cam_b"


def test_get_reference_camera_name_ties_break_by_name():
    videos = [
        _make_video_info("cam_b", 10.0),
        _make_video_info("cam_a", 10.0),
    ]
    assert get_reference_camera_name(videos) == "cam_a"


def test_cross_correlate_detects_known_shift():
    rng = np.random.default_rng(42)
    reference_signal = rng.standard_normal(1000)
    shift_samples = 50
    # zero-pad (not circular roll) so the shift is unambiguous for a noise signal
    shifted_signal = np.concatenate([np.zeros(shift_samples), reference_signal])[:1000]

    lag, confidence = cross_correlate(reference_signal, shifted_signal)

    assert lag == -shift_samples
    assert confidence > 1.0


def test_find_cross_correlation_lags_normalizes_to_zero_minimum():
    sample_rate = 1000
    rng = np.random.default_rng(7)
    base_signal = rng.standard_normal(sample_rate)
    shift_samples = 20

    audio_signals = {
        "cam_a": base_signal,
        "cam_b": np.concatenate([np.zeros(shift_samples), base_signal])[:sample_rate],
    }
    videos = [_make_video_info("cam_a", 1.0), _make_video_info("cam_b", 1.0)]

    lags = find_cross_correlation_lags(audio_signals, videos, sample_rate)
    lag_by_camera = {lag.camera_name: lag.lag_seconds for lag in lags}

    assert min(lag_by_camera.values()) == 0.0
    assert all(confidence.confidence is not None for confidence in lags)


def test_trim_audio_in_memory_reuses_loaded_signals(tmp_path):
    sample_rate = 100
    signals = {
        "cam_a": np.arange(0, 100, dtype=float),
        "cam_b": np.arange(0, 100, dtype=float),
    }
    lags = {
        "cam_a": LagResult(camera_name="cam_a", lag_seconds=0.0),
        "cam_b": LagResult(camera_name="cam_b", lag_seconds=0.1),
    }

    output_paths = trim_audio_in_memory(
        signals, sample_rate, lags, synced_length_seconds=0.5, output_folder=tmp_path
    )

    assert output_paths["cam_a"].exists()
    assert output_paths["cam_b"].exists()
