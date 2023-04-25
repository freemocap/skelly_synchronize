import logging
from pathlib import Path
from typing import Union

logging.basicConfig(level=logging.INFO)

def get_parent_directory(path: Union[str, Path]) -> Path:
    path = ensure_path_object(path)

    logging.info(f"Input path: {path}")

    if path == path.parent:
        logging.warning(f"Root directory detected, no parent directory. Returning {path}")
        return path

    parent_directory = path.parent
    logging.info(f"Parent directory: {parent_directory}")

    return parent_directory

def get_file_name(file_path: Union[str, Path]) -> str:
    """
    Get the name of the file without directories or file extensions.
    """
    file_path = ensure_path_object(file_path)
    
    try:
        file_name = file_path.stem
        logging.info(f"Retrieved file name: {file_name} from path: {file_path}")
        return file_name
    except Exception as e:
        logging.error(f"Error retrieving file name from path: {file_path}. Exception: {e}")
        raise


def ensure_path_object(path: Union[str, Path]) -> Path:
    """
    Ensure the input is a Path object. If the input is a string, convert it to a Path object.
    """
    if not isinstance(path, Path):
        path = Path(path)

    return path
