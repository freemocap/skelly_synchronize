import librosa
import toml
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import List

from skelly_synchronize.system.paths_and_file_names import (
    DEBUG_PLOT_NAME,
    DEBUG_TOML_NAME,
    AUDIO_FILES_FOLDER_NAME,
    LAG_DICTIONARY_NAME,
    SYNCHRONIZED_VIDEO_NAME,
)


def create_debug_plots(synchronized_video_folder_path: Path):
    output_filepath = synchronized_video_folder_path / DEBUG_PLOT_NAME
    audio_folder_path = synchronized_video_folder_path / AUDIO_FILES_FOLDER_NAME
    debug_toml_path = synchronized_video_folder_path / DEBUG_TOML_NAME
    debug_dictionary = toml.load(debug_toml_path)

    # get a single video's duration from debug dictionary
    arbitrary_video_information = next(
        iter(debug_dictionary[SYNCHRONIZED_VIDEO_NAME].values())
    )
    video_duration = float(arbitrary_video_information["video duration"])

    list_of_audio_paths = get_audio_paths_from_folder(audio_folder_path)
    plot_waveforms(
        audio_filepath_list=list_of_audio_paths,
        lag_dictionary=debug_dictionary[LAG_DICTIONARY_NAME],
        synched_video_length=video_duration,
        output_filepath=output_filepath,
    )


def get_audio_paths_from_folder(
    folder_path: Path, file_extension: str = ".wav"
) -> List[Path]:
    search_extension = "*" + file_extension.lower()
    return list(Path(folder_path).glob(search_extension))


def plot_waveforms(
    audio_filepath_list: List[Path],
    lag_dictionary: dict,
    synched_video_length: float,
    output_filepath: Path,
):
    fig, axs = plt.subplots(2, 1, sharex=True, sharey=True)
    fig.suptitle("Audio Cross Correlation Debug")

    axs[0].set_ylabel("Amplitude")
    axs[1].set_ylabel("Amplitude")
    axs[1].set_xlabel("Time (s)")

    axs[0].set_title("Before Cross Correlation")
    axs[1].set_title("After Cross Correlation")

    for audio_filepath in audio_filepath_list:
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)
        lag = lag_dictionary[audio_filepath.stem]

        lag_in_samples = int(float(lag) * sr)
        synched_video_length_in_samples = int(synched_video_length * sr)

        shortened_audio_signal = audio_signal[lag_in_samples:]
        shortened_audio_signal = shortened_audio_signal[
            :synched_video_length_in_samples
        ]

        time = np.linspace(0, len(audio_signal) / sr, num=len(audio_signal))
        shortened_time = np.linspace(
            0, len(shortened_audio_signal) / sr, num=len(shortened_audio_signal)
        )

        axs[0].plot(time, audio_signal, alpha=0.4)
        axs[1].plot(shortened_time, shortened_audio_signal, alpha=0.4)

    plt.savefig(output_filepath)
