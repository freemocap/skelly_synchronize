import logging
import librosa
import soundfile as sf
from pathlib import Path
import numpy as np
from typing import Dict

from skelly_synchronize.core_processes.video_functions.ffmpeg_functions import (
    extract_audio_from_video_ffmpeg,
)
from skelly_synchronize.system.paths_and_file_names import TRIMMED_AUDIO_FOLDER_NAME


def get_audio_sample_rates(audio_signal_dict: Dict[str, float]) -> list:
    """Get the sample rates of each audio file and return them in a list"""
    audio_sample_rate_list = [
        single_audio_dict["sample rate"]
        for single_audio_dict in audio_signal_dict.values()
    ]

    return audio_sample_rate_list


def normalize_audio(audio_file):
    """Perform z-score normalization on an audio file and return the normalized audio file - this is best practice for correlating."""
    return (audio_file - np.mean(audio_file)) / np.std(audio_file - np.mean(audio_file))


def extract_audio_files(
    video_info_dict: Dict[str, dict], audio_extension: str, audio_folder_path: Path
) -> dict:
    """Get a dictionary with audio files and information from the given video file paths."""
    audio_signal_dict = dict()
    for video_dict in video_info_dict.values():
        extract_audio_from_video_ffmpeg(
            file_pathstring=video_dict["video pathstring"],
            file_name=video_dict["camera name"],
            output_folder_path=audio_folder_path,
            output_extension=audio_extension,
        )

        audio_name = video_dict["camera name"] + "." + audio_extension
        audio_file_path = audio_folder_path / audio_name

        if not audio_file_path.is_file():
            logging.error("Error loading audio file, verify video has audio track")
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        audio_signal, sample_rate = librosa.load(path=audio_file_path, sr=None)

        audio_duration = librosa.get_duration(y=audio_signal, sr=sample_rate)
        logging.info(f"audio file {audio_name} is {audio_duration} seconds long")
        audio_signal_dict[audio_name] = {
            "audio file": audio_signal,
            "sample rate": sample_rate,
            "camera name": video_dict["camera name"],
            "audio duration": audio_duration,
        }

    return audio_signal_dict


def trim_audio_files(
    audio_folder_path: Path, lag_dictionary: dict, synced_video_length: float
):
    logging.info("Trimming audio files to match synchronized video length")

    trimmed_audio_folder_path = Path(audio_folder_path) / TRIMMED_AUDIO_FOLDER_NAME
    trimmed_audio_folder_path.mkdir(parents=True, exist_ok=True)

    for audio_filepath in audio_folder_path.glob("*.wav"):
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)
        lag = lag_dictionary[audio_filepath.stem]

        lag_in_samples = int(float(lag) * sr)
        synched_video_length_in_samples = int(synced_video_length * sr)

        shortened_audio_signal = audio_signal[lag_in_samples:]
        shortened_audio_signal = shortened_audio_signal[
            :synched_video_length_in_samples
        ]

        audio_filename = str(audio_filepath.stem) + ".wav"

        logging.info(f"Saving audio {audio_filename}")
        output_path = trimmed_audio_folder_path / audio_filename
        sf.write(output_path, shortened_audio_signal, sr, subtype="PCM_24")

    return trimmed_audio_folder_path
