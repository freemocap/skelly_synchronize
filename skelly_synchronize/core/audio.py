import logging
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from skelly_synchronize.core.models import LagResult, VideoInfo

logger = logging.getLogger(__name__)


def get_reference_camera_name(videos: list[VideoInfo]) -> str:
    """Pick a deterministic reference camera for cross-correlation (resolves KI-13).

    Strategy: the camera with the longest recorded duration; ties (including
    the degenerate all-equal case) resolve to sorted-camera-name order, which
    stays deterministic either way.
    """
    return sorted(videos, key=lambda v: (-v.duration_seconds, v.camera_name))[
        0
    ].camera_name


def cross_correlate(
    reference_signal: np.ndarray, other_signal: np.ndarray
) -> tuple[int, float]:
    """Cross correlate two audio signals.

    Returns (lag_in_samples, confidence). `confidence` is the ratio of the peak
    correlation magnitude to the mean correlation magnitude (peak sharpness) --
    a low ratio means the peak is not well distinguished from the noise floor
    (resolves KI-14).
    """
    correlation = signal.correlate(
        reference_signal, other_signal, mode="full", method="fft"
    )
    lags = signal.correlation_lags(
        reference_signal.size, other_signal.size, mode="full"
    )

    peak_index = int(np.argmax(correlation))
    lag = int(lags[peak_index])

    noise_floor = float(np.mean(np.abs(correlation))) + 1e-12
    confidence = float(np.abs(correlation[peak_index])) / noise_floor

    return lag, confidence


def find_cross_correlation_lags(
    audio_signals: dict[str, np.ndarray],
    videos: list[VideoInfo],
    sample_rate: int,
) -> list[LagResult]:
    """Cross correlate every camera's audio against a deterministic reference camera.

    Returns `LagResult`s satisfying the shared contract: `lag_seconds` is the
    number of seconds to trim off the front of that video so all videos align,
    normalized so the minimum lag is 0 (resolves KI-02 -- normalized once,
    here, rather than left as an implicit downstream assumption).
    """
    reference_camera_name = get_reference_camera_name(videos)
    reference_signal = audio_signals[reference_camera_name]

    logger.info(
        f"Using {reference_camera_name} as the cross-correlation reference camera"
    )

    raw_lags_seconds: dict[str, float] = {}
    confidences: dict[str, float] = {}
    for camera_name, camera_signal in audio_signals.items():
        lag_samples, confidence = cross_correlate(reference_signal, camera_signal)
        raw_lags_seconds[camera_name] = lag_samples / sample_rate
        confidences[camera_name] = confidence

    max_lag = max(raw_lags_seconds.values())

    return [
        LagResult(
            camera_name=camera_name,
            lag_seconds=max_lag - raw_lag,
            confidence=confidences[camera_name],
        )
        for camera_name, raw_lag in raw_lags_seconds.items()
    ]


def trim_audio_in_memory(
    audio_signals: dict[str, np.ndarray],
    sample_rate: int,
    lags_by_camera: dict[str, LagResult],
    synced_length_seconds: float,
    output_folder: Path,
) -> dict[str, Path]:
    """Trim already-loaded audio signals to the synchronized window.

    Reuses the in-memory signals from extraction instead of reloading each
    `.wav` from disk (resolves KI-12).
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    length_in_samples = int(synced_length_seconds * sample_rate)

    output_paths: dict[str, Path] = {}
    for camera_name, camera_signal in audio_signals.items():
        lag_in_samples = int(lags_by_camera[camera_name].lag_seconds * sample_rate)
        trimmed_signal = camera_signal[lag_in_samples:][:length_in_samples]

        output_path = output_folder / f"{camera_name}.wav"
        sf.write(output_path, trimmed_signal, sample_rate, subtype="PCM_24")
        output_paths[camera_name] = output_path

    return output_paths
