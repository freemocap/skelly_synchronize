import logging
from pathlib import Path
from typing import Union

logging.basicConfig(level=logging.INFO)


def get_parent_directory(path: Union[str, Path]) -> Path:
    """Get the parent directory of the specified path."""
    path = ensure_path_object(path)

    logging.info(f"Input path: {path}")

    if path == path.parent:
        logging.warning(
            f"Root directory detected, no parent directory. Returning {path}"
        )
        return path

    parent_directory = path.parent
    logging.info(f"Parent directory: {parent_directory}")

    return parent_directory


def create_directory(parent_directory: Path, directory_name: str) -> Path:
    """Create a new directory under the specified parent directory."""
    parent_directory = ensure_path_object(parent_directory)
    new_directory_path = parent_directory / directory_name

    try:
        new_directory_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created directory: {new_directory_path}")
    except Exception as e:
        logging.error(f"Error creating directory: {new_directory_path}. Exception: {e}")
        raise

    return new_directory_path


def get_file_name(file_path: Union[str, Path]) -> str:
    """Get the name of the file without directories or file extensions."""
    file_path = ensure_path_object(file_path)

    try:
        file_name = file_path.stem
        logging.info(f"Retrieved file name: {file_name} from path: {file_path}")
        return file_name
    except Exception as e:
        logging.error(
            f"Error retrieving file name from path: {file_path}. Exception: {e}"
        )
        raise


def name_synced_video(raw_video_filename: str) -> str:
    """Take a raw video filename, remove the raw prefix if its there, and return the synced video filename"""
    raw_video_filename = str(raw_video_filename)
    if raw_video_filename.split("_")[0] == "raw":
        synced_video_name = "synced_" + raw_video_filename[4:] + ".mp4"
    else:
        synced_video_name = "synced_" + raw_video_filename + ".mp4"

    return synced_video_name


def ensure_path_object(path: Union[str, Path]) -> Path:
    """Ensure the input is a Path object. If the input is a string, convert it to a Path object."""
    if not isinstance(path, Path):
        path = Path(path)

    return path
