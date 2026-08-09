import numpy as np

from skelly_synchronize.core.brightness import find_first_brightness_change


def test_find_first_brightness_change_detects_flash():
    brightness = np.concatenate([np.full(10, 10.0), np.full(20, 200.0)])

    event = find_first_brightness_change(
        brightness, fps=30.0, brightness_ratio_threshold=1000.0
    )

    assert event is not None
    assert event.frame_index == 10
    assert event.lag_seconds == 10 / 30.0


def test_find_first_brightness_change_returns_none_for_flat_series():
    # regression test for KI-08: a flat series used to fall through to an
    # implicit index-0 "no crossing found" sentinel that looked like a real event.
    brightness = np.full(30, 128.0)

    event = find_first_brightness_change(
        brightness, fps=30.0, brightness_ratio_threshold=1000.0
    )

    assert event is None


def test_find_first_brightness_change_returns_none_for_empty_series():
    event = find_first_brightness_change(np.array([]), fps=30.0)
    assert event is None


def test_find_first_brightness_change_falls_back_to_sharpest_change_below_threshold():
    # small, gradual change that never crosses the (high) threshold
    brightness = np.array([10.0, 10.0, 12.0, 10.0, 10.0])

    event = find_first_brightness_change(
        brightness, fps=10.0, brightness_ratio_threshold=1000.0
    )

    assert event is not None
    assert event.lag_seconds == event.frame_index / 10.0
