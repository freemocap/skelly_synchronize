import logging
from pathlib import Path

import librosa
import matplotlib
import numpy as np
import toml

# Force the non-interactive Agg backend: these plots are only ever saved to
# file, never shown, and matplotlib's auto-selected GUI backend (macosx/Qt/Tk)
# can crash when the pipeline is invoked from a thread or process other than
# a GUI app's main thread (e.g. from a Qt-based caller, or a worker process).
matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from skelly_synchronize.core.models import LagResult, VideoInfo

logger = logging.getLogger(__name__)


def save_debug_toml(
    output_path: Path,
    videos_before: list[VideoInfo],
    videos_after: list[VideoInfo],
    lags: list[LagResult],
    synchronized_fps: float | None = None,
    synchronized_frame_count: int | None = None,
) -> Path:
    """Dump raw/synchronized video info and lag results to a TOML file for debugging.

    `synchronized_fps`/`synchronized_frame_count` are the single fps and frame
    count shared by every synchronized video -- surfaced explicitly here
    (rather than requiring a reader to cross-check every entry in
    `synchronized_video_information`) since an exact frame-count match across
    videos is the core correctness guarantee synchronization is supposed to
    provide.
    """
    data = {
        "raw_video_information": {
            video.video_name: video.model_dump(mode="json") for video in videos_before
        },
        "synchronized_video_information": {
            video.video_name: video.model_dump(mode="json") for video in videos_after
        },
        "lag_results": {lag.video_name: lag.model_dump() for lag in lags},
    }
    # toml has no null type, so an unknown value is an absent key, not a null value.
    if synchronized_fps is not None:
        data["synchronized_video_fps"] = synchronized_fps
    if synchronized_frame_count is not None:
        data["synchronized_video_frame_count"] = synchronized_frame_count

    output_path = Path(output_path)
    with open(output_path, "w") as toml_file:
        toml_file.write(toml.dumps(data))
    return output_path


def plot_audio_waveforms(
    raw_audio_paths: list[Path],
    trimmed_audio_paths: list[Path],
    output_path: Path,
) -> Path:
    fig, axs = plt.subplots(2, 1, sharex=True, sharey=True)
    fig.suptitle("Audio Cross Correlation Debug")

    axs[0].set_ylabel("Amplitude")
    axs[1].set_ylabel("Amplitude")
    axs[1].set_xlabel("Time (s)")
    axs[0].set_title("Before Cross Correlation")
    axs[1].set_title("After Cross Correlation")

    for audio_path in raw_audio_paths:
        audio_signal, sample_rate = librosa.load(path=audio_path, sr=None)
        time = np.linspace(0, len(audio_signal) / sample_rate, num=len(audio_signal))
        axs[0].plot(time, audio_signal, alpha=0.4)

    for audio_path in trimmed_audio_paths:
        audio_signal, sample_rate = librosa.load(path=audio_path, sr=None)
        time = np.linspace(0, len(audio_signal) / sample_rate, num=len(audio_signal))
        axs[1].plot(time, audio_signal, alpha=0.4)

    output_path = Path(output_path)
    logger.info(f"Saving debug plots to: {output_path}")
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_brightness_series(
    before_series: dict[str, np.ndarray],
    before_fps: dict[str, float],
    after_series: dict[str, np.ndarray],
    after_fps: dict[str, float],
    output_path: Path,
) -> Path:
    """Plot brightness-over-time before/after trimming.

    The x-axis is frame index divided by fps to show real elapsed time
    (resolves KI-09 -- the old plot labeled the axis "Time (s)" but plotted
    raw, unscaled frame indices).
    """
    fig, axs = plt.subplots(2, 1, sharex=False, sharey=True)
    fig.suptitle("Brightness Across Frames")

    axs[0].set_ylabel("Brightness")
    axs[1].set_ylabel("Brightness")
    axs[0].set_xlabel("Time (s)")
    axs[1].set_xlabel("Time (s)")
    axs[0].set_title("Before Trimming")
    axs[1].set_title("After Trimming")

    for video_name, brightness_array in before_series.items():
        fps = before_fps[video_name]
        time = np.arange(len(brightness_array)) / fps
        axs[0].plot(time, brightness_array, alpha=0.5, label=video_name)

    for video_name, brightness_array in after_series.items():
        fps = after_fps[video_name]
        time = np.arange(len(brightness_array)) / fps
        axs[1].plot(time, brightness_array, alpha=0.5, label=video_name)

    output_path = Path(output_path)
    logger.info(f"Saving debug plots to: {output_path}")
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
