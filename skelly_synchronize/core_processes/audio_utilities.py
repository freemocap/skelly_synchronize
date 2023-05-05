import logging
from pathlib import Path
import librosa
import numpy as np
from typing import Dict

from skelly_synchronize.core_processes.video_functions.ffmpeg_functions import (
    extract_audio_from_video_ffmpeg,
)


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


def get_audio_files(
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

        audio_signal, sample_rate = librosa.load(
            path=audio_folder_path / audio_name, sr=None
        )

        audio_duration = librosa.get_duration(y=audio_signal, sr=sample_rate)
        logging.info(f"audio file {audio_name} is {audio_duration} seconds long")
        audio_signal_dict[audio_name] = {
            "audio file": audio_signal,
            "sample rate": sample_rate,
            "camera name": video_dict["camera name"],
            "audio duration": audio_duration,
        }

    return audio_signal_dict
