from pathlib import Path

from skelly_synchronize.core.backends.deffcode import (
    TRANSPOSITION_FILTERS,
    _get_transpose_ffparams,
)


def test_transposition_filters_cover_all_common_orientations():
    for orientation in (90.0, -270.0, -90.0, 270.0, 180.0, -180.0):
        assert orientation in TRANSPOSITION_FILTERS
        assert "transpose" in TRANSPOSITION_FILTERS[orientation]


def test_get_transpose_ffparams_returns_empty_for_unrotated_video(monkeypatch):
    monkeypatch.setattr(
        "skelly_synchronize.core.backends.deffcode.extract_video_rotation",
        lambda filepath: 0.0,
    )

    assert _get_transpose_ffparams(Path("landscape_video.mp4")) == {}


def test_get_transpose_ffparams_returns_transpose_filter_for_rotated_video(
    monkeypatch,
):
    monkeypatch.setattr(
        "skelly_synchronize.core.backends.deffcode.extract_video_rotation",
        lambda filepath: -90.0,
    )

    ffparams = _get_transpose_ffparams(Path("vertical_iphone_video.mp4"))

    assert ffparams == {
        "-ffprefixes": ["-noautorotate"],
        "-vf": TRANSPOSITION_FILTERS[-90.0],
    }
