import pytest
from pathlib import Path

from skelly_synchronize.skelly_synchronize import VideoSynchronize


@pytest.fixture
def lag_list():
    return {"Cam1": 0.0, "Cam2": 4.3402267573696145, "Cam3": 9.475963718820863}


def test_normalize_lag_list(lag_list):
    test_synchronize = VideoSynchronize(
        "iPhoneTesting",
        Path("/Users/philipqueen/Documents/Humon Research Lab/FreeMocap_Data"),
    )
    assert test_synchronize._normalize_lag_dictionary(lag_list) == {
        "Cam1": 9.475963718820863,
        "Cam2": 5.135736961451248,
        "Cam3": 0.0,
    }, "Lag dict did not normalize correctly"

if __name__ == "__main__":
    test_normalize_lag_list(lag_list)
    print("tests passed")
