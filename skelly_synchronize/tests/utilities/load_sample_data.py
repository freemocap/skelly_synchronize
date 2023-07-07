import io
import requests
import zipfile
from pathlib import Path

from skelly_synchronize.system.paths_and_file_names import (
    FIGSHARE_SAMPLE_DATA_FILE_NAME,
    FIGSHARE_ZIP_FILE_URL,
    RAW_VIDEOS_FOLDER_NAME,
)


def load_sample_data() -> Path:
    extract_to_path = Path.home()
    extract_to_path.mkdir(exist_ok=True)

    figshare_sample_data_path = extract_to_path / FIGSHARE_SAMPLE_DATA_FILE_NAME

    if not Path.exists(figshare_sample_data_path):
        r = requests.get(FIGSHARE_ZIP_FILE_URL, timeout=(10, 60))
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(figshare_sample_data_path)

    return figshare_sample_data_path


def find_raw_videos_folder_path(session_folder_path: Path) -> Path:
    for subfolder_path in session_folder_path.iterdir():
        if subfolder_path.name == RAW_VIDEOS_FOLDER_NAME:
            return subfolder_path

    raise Exception(
        f"Could not find a videos folder in path {str(session_folder_path)}"
    )


if __name__ == "__main__":
    sample_data_path = load_sample_data()
