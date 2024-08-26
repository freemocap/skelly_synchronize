import logging
import librosa
from matplotlib import pyplot as plt
import numpy as np
from pathlib import Path
from typing import List

from skelly_synchronize.system.file_extensions import NUMPY_EXTENSION, AudioExtension
from skelly_synchronize.system.paths_and_file_names import (
    BRIGHTNESS_SUFFIX,
    DEBUG_PLOT_NAME,
    AUDIO_FILES_FOLDER_NAME,
    TRIMMED_AUDIO_FOLDER_NAME,
)

logger = logging.getLogger(__name__)


def create_brightness_debug_plots(
    raw_video_folder_path: Path, synchronized_video_folder_path: Path
):
    output_filepath = synchronized_video_folder_path / DEBUG_PLOT_NAME

    list_of_raw_brightness_paths = get_brightness_npys_from_folder(
        folder_path=raw_video_folder_path
    )
    list_of_trimmed_brightness_paths = get_brightness_npys_from_folder(
        folder_path=synchronized_video_folder_path
    )

    logger.info("Creating debug plots")
    plot_brightness_across_frames(
        raw_brightness_npys=list_of_raw_brightness_paths,
        trimmed_brightness_npys=list_of_trimmed_brightness_paths,
        output_filepath=output_filepath,
    )


def create_audio_debug_plots(synchronized_video_folder_path: Path):
    output_filepath = synchronized_video_folder_path / DEBUG_PLOT_NAME
    raw_audio_folder_path = synchronized_video_folder_path / AUDIO_FILES_FOLDER_NAME
    trimmed_audio_folder_path = raw_audio_folder_path / TRIMMED_AUDIO_FOLDER_NAME

    list_of_raw_audio_paths = get_audio_paths_from_folder(raw_audio_folder_path)
    list_of_trimmed_audio_paths = get_audio_paths_from_folder(trimmed_audio_folder_path)

    logger.info("Creating debug plots")
    plot_audio_waveforms(
        raw_audio_filepath_list=list_of_raw_audio_paths,
        trimmed_audio_filepath_list=list_of_trimmed_audio_paths,
        output_filepath=output_filepath,
    )


def get_brightness_npys_from_folder(folder_path: Path) -> List[Path]:
    search_extension = f"*{BRIGHTNESS_SUFFIX}.{NUMPY_EXTENSION}"
    return list(Path(folder_path).glob(search_extension))


def get_audio_paths_from_folder(
    folder_path: Path, audio_extension: AudioExtension = AudioExtension.WAV
) -> List[Path]:
    search_extension = f"*.{audio_extension.value}"
    return list(Path(folder_path).glob(search_extension))


def plot_brightness_across_frames(
    raw_brightness_npys: List[Path],
    trimmed_brightness_npys: List[Path],
    output_filepath: Path,
):
    fig, axs = plt.subplots(2, 1, sharex=True, sharey=True)
    fig.suptitle("Brightness Across Frames")

    axs[0].set_ylabel("Brightness")
    axs[1].set_ylabel("Brightness")
    axs[1].set_xlabel("Time (s)")

    axs[0].set_title("Before Cross Correlation")
    axs[1].set_title("After Cross Correlation")

    for brightness_npys in raw_brightness_npys:
        brightness_array = np.load(brightness_npys)

        time = np.linspace(0, len(brightness_array), num=len(brightness_array))

        axs[0].plot(time, brightness_array, alpha=0.5)

    for brightness_npys in trimmed_brightness_npys:
        brightness_array = np.load(brightness_npys)

        time = np.linspace(0, len(brightness_array), num=len(brightness_array))

        axs[1].plot(time, brightness_array, alpha=0.5)

    logger.info(f"Saving debug plots to: {output_filepath}")
    plt.savefig(output_filepath)


def plot_audio_waveforms(
    raw_audio_filepath_list: List[Path],
    trimmed_audio_filepath_list: List[Path],
    output_filepath: Path,
):
    fig, axs = plt.subplots(2, 1, sharex=True, sharey=True)
    fig.suptitle("Audio Cross Correlation Debug")

    axs[0].set_ylabel("Amplitude")
    axs[1].set_ylabel("Amplitude")
    axs[1].set_xlabel("Time (s)")

    axs[0].set_title("Before Cross Correlation")
    axs[1].set_title("After Cross Correlation")

    for audio_filepath in raw_audio_filepath_list:
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)

        time = np.linspace(0, len(audio_signal) / sr, num=len(audio_signal))

        axs[0].plot(time, audio_signal, alpha=0.4)

    for audio_filepath in trimmed_audio_filepath_list:
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)

        time = np.linspace(0, len(audio_signal) / sr, num=len(audio_signal))

        axs[1].plot(time, audio_signal, alpha=0.4)

    logger.info(f"Saving debug plots to: {output_filepath}")
    plt.savefig(output_filepath)
