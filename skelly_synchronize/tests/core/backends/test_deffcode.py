from skelly_synchronize.core.backends.deffcode import TRANSPOSITION_FILTERS


def test_transposition_filters_cover_all_common_orientations():
    for orientation in (90.0, -270.0, -90.0, 270.0, 180.0, -180.0):
        assert orientation in TRANSPOSITION_FILTERS
        assert "transpose" in TRANSPOSITION_FILTERS[orientation]
