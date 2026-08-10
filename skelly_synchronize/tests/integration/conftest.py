import shutil
from pathlib import Path
from typing import Callable

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def raw_video_folder_factory(tmp_path: Path) -> Callable[[str], Path]:
    """Copy a checked-in fixture set (e.g. "audio_sync") into an isolated raw_videos folder.

    Copying into `tmp_path` keeps each test's pipeline run (and any
    normalized/audio/debug output it writes alongside the input) isolated
    from the checked-in fixtures and from other tests.
    """

    def _make(fixture_set_name: str) -> Path:
        source_dir = FIXTURES_DIR / fixture_set_name
        raw_video_folder_path = tmp_path / "raw_videos"
        shutil.copytree(source_dir, raw_video_folder_path)
        return raw_video_folder_path

    return _make
