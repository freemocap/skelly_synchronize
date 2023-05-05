import pytest

from skelly_synchronize.core_processes.correlation_functions import (
    normalize_lag_dictionary,
)


@pytest.fixture
def lag_dict():
    return {"Cam1": 0.0, "Cam2": 4.3402267573696145, "Cam3": 9.475963718820863}


@pytest.fixture
def normalized_lag_dict():
    return {"Cam1": 9.475963718820863, "Cam2": 5.135736961451248, "Cam3": 0.0}


def test_normalize_lag_dict(lag_dict, normalized_lag_dict):
    assert (
        normalize_lag_dictionary(lag_dict) == normalized_lag_dict
    ), "Lag dict did not normalize correctly"


if __name__ == "__main__":
    test_normalize_lag_dict(lag_dict, normalized_lag_dict)
    print("tests passed")
