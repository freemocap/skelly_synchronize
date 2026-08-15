import io
import zipfile
from pathlib import Path

import pytest
import requests

from skelly_synchronize.core.config import RAW_VIDEOS_FOLDER_NAME

# Real multi-camera capture session used for full end-to-end confidence,
# hosted as a GitHub release asset. Only used by the @pytest.mark.slow tier --
# not needed for the fast fixture-based integration tests in tests/integration/.
SAMPLE_DATA_ZIP_URL = "https://github.com/freemocap/skellysamples/releases/download/synch_test_data/audio_synchronization_test_data.zip"
SAMPLE_DATA_FILE_NAME = "audio_synchronization_test_data"

CACHE_DIR = Path.home() / ".cache" / "skelly_synchronize"


def _download_and_extract_sample_data() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sample_data_path = CACHE_DIR / SAMPLE_DATA_FILE_NAME

    if not sample_data_path.exists():
        response = requests.get(SAMPLE_DATA_ZIP_URL, timeout=(10, 60))
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(sample_data_path)

    return sample_data_path


@pytest.fixture(scope="session")
def sample_dataset_raw_video_folder_path() -> Path:
    """Session-scoped, opt-in only (used exclusively by @pytest.mark.slow tests).

    Downloads once and caches under ~/.cache/skelly_synchronize -- subsequent
    runs (local or CI) reuse the cached extraction instead of re-downloading.
    """
    sample_session_folder_path = _download_and_extract_sample_data()

    for subfolder_path in sample_session_folder_path.iterdir():
        if subfolder_path.name == RAW_VIDEOS_FOLDER_NAME:
            return subfolder_path

    raise FileNotFoundError(
        f"Could not find a '{RAW_VIDEOS_FOLDER_NAME}' folder in "
        f"{sample_session_folder_path}"
    )
