import logging
import librosa
from matplotlib import pyplot as plt
import numpy as np
from pathlib import Path
from typing import List

from skelly_synchronize.system.paths_and_file_names import (
    DEBUG_PLOT_NAME,
    AUDIO_FILES_FOLDER_NAME,
    TRIMMED_AUDIO_FOLDER_NAME,
)


def create_debug_plots(synchronized_video_folder_path: Path):
    output_filepath = synchronized_video_folder_path / DEBUG_PLOT_NAME
    raw_audio_folder_path = synchronized_video_folder_path / AUDIO_FILES_FOLDER_NAME
    trimmed_audio_folder_path = raw_audio_folder_path / TRIMMED_AUDIO_FOLDER_NAME

    list_of_raw_audio_paths = get_audio_paths_from_folder(raw_audio_folder_path)
    list_of_trimmed_audio_paths = get_audio_paths_from_folder(trimmed_audio_folder_path)

    logging.info("Creating debug plots")
    plot_waveforms(
        raw_audio_filepath_list=list_of_raw_audio_paths,
        trimmed_audio_filepath_list=list_of_trimmed_audio_paths,
        output_filepath=output_filepath,
    )


def get_audio_paths_from_folder(
    folder_path: Path, file_extension: str = ".wav"
) -> List[Path]:
    search_extension = "*" + file_extension.lower()
    return Path(folder_path).glob(search_extension)


def plot_waveforms(
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

    logging.info(f"Saving debug plots to: {output_filepath}")
    plt.savefig(output_filepath)
