from pathlib import Path

import cv2
import pytest

from skelly_synchronize.core.backends.base import get_backend
from skelly_synchronize.core.models import VideoBackendKind

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _frame_size(video_path: Path) -> tuple[int, int]:
    capture = cv2.VideoCapture(str(video_path))
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height
    finally:
        capture.release()


@pytest.mark.parametrize(
    "video_handler", [VideoBackendKind.FFMPEG, VideoBackendKind.DEFFCODE]
)
def test_backend_trim_corrects_rotated_iphone_style_video(
    tmp_path, video_handler: VideoBackendKind
):
    """Regression test for a display-matrix-rotated source losing its orientation.

    `vertical_iphone_style.mp4` is muxed landscape (64x48 coded dimensions)
    with a display matrix tagging it as rotated -- the same shape as real
    iPhone vertical recordings. A trimmed output that ignores the rotation
    tag comes out still 64x48 (stretched); a correct one comes out 48x64
    (portrait, matching how e.g. OpenCV reads the untrimmed source once it
    applies that same rotation tag on decode). Both backends need to agree
    on this, since `video_handler` is a user-facing choice.
    """
    source_path = FIXTURES_DIR / "rotation" / "vertical_iphone_style.mp4"
    output_path = tmp_path / "trimmed.mp4"

    get_backend(video_handler).trim(source_path, 0.0, 5, output_path)

    assert _frame_size(output_path) == (48, 64)
