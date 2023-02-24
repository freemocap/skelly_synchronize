import pytest
from pathlib import Path

from skelly_synchronize.skelly_synchronize import VideoSynchronize


@pytest.fixture
def lag_list():
    return [0.0, 4.3402267573696145, 9.475963718820863]


def test_normalize_lag_list(lag_list):
    """Actually need to split normalize lag list into different function"""
    test_synchronize = VideoSynchronize("iPhoneTesting", Path("/Users/philipqueen/Documents/Humon Research Lab/FreeMocap_Data"))
    assert  test_synchronize._normalize_lag_dictionary(lag_list) == [9.475963718820863, 5.135736961451248, 0.0], "Lag dict did not normalize correctly"
