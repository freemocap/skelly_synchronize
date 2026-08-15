import logging
from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel

from skelly_synchronize.core.models import VideoInfo

logger = logging.getLogger(__name__)


class BrightnessEvent(BaseModel):
    frame_index: int
    lag_seconds: float


def compute_brightness_series(video: VideoInfo) -> np.ndarray:
    """Compute the mean grayscale brightness of every frame in a video.

    Pure function -- no file I/O side effects (resolves KI-07). Persisting the
    result is a separate, explicit call to `save_brightness_series`.
    """
    capture = cv2.VideoCapture(str(video.filepath))
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        brightness = np.zeros(frame_count)

        for frame_index in range(frame_count):
            read_ok, frame = capture.read()
            if not read_ok or frame is None:
                brightness = brightness[:frame_index]
                break
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness[frame_index] = np.mean(gray_frame)
    finally:
        capture.release()

    return brightness


def save_brightness_series(series: np.ndarray, output_path: Path) -> Path:
    """Persist a brightness series to a `.npy` sidecar. Explicit, opt-in (KI-07)."""
    output_path = Path(output_path)
    np.save(output_path, series)
    return output_path


def find_first_brightness_change(
    brightness_series: np.ndarray,
    fps: float,
    brightness_ratio_threshold: float = 1000.0,
) -> BrightnessEvent | None:
    """Find the first frame with a significant brightness change (e.g. a flash).

    Returns an explicit `BrightnessEvent | None` instead of relying on an
    index-0 fallback as an implicit "not found" sentinel (resolves KI-08).
    """
    if brightness_series.size == 0:
        return None

    brightness_difference = np.diff(brightness_series, prepend=brightness_series[0])
    brightness_double_difference = np.diff(
        brightness_difference, prepend=brightness_difference[0]
    )
    combined_brightness_metric = brightness_difference * brightness_double_difference

    crossings = np.flatnonzero(combined_brightness_metric >= brightness_ratio_threshold)
    if crossings.size > 0:
        frame_index = int(crossings[0])
        logger.info(f"First brightness change detected at frame {frame_index}")
        return BrightnessEvent(frame_index=frame_index, lag_seconds=frame_index / fps)

    # no crossing exceeded the threshold -- fall back to the sharpest detected
    # change, but only if there actually was one (a genuinely flat/no-op
    # series has no brightness event to report).
    fallback_frame_index = int(np.argmax(brightness_double_difference))
    if brightness_double_difference[fallback_frame_index] <= 0:
        logger.info("No brightness change detected in video")
        return None

    logger.info(
        "No brightness change exceeded threshold, "
        f"defaulting to fastest detected change at frame {fallback_frame_index}"
    )
    return BrightnessEvent(
        frame_index=fallback_frame_index, lag_seconds=fallback_frame_index / fps
    )
