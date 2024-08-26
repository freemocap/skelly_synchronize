import logging
from pathlib import Path
import cv2
import numpy as np
from typing import Dict
from scipy import signal

from skelly_synchronize.system.file_extensions import NUMPY_EXTENSION
from skelly_synchronize.system.paths_and_file_names import BRIGHTNESS_SUFFIX

logger = logging.getLogger(__name__)


def cross_correlate(audio1: np.ndarray, audio2: np.ndarray):
    """Take two audio files, synchronize them using cross correlation, and trim them to the same length.
    Inputs are two audio arrays to be synchronized. Return the lag expressed in terms of the audio sample rate of the clips.
    """

    # compute cross correlation with scipy correlate function, which gives the correlation of every different lag value
    # mode='full' makes sure every lag value possible between the two signals is used, and method='fft' uses the fast fourier transform to speed the process up
    correlation = signal.correlate(audio1, audio2, mode="full", method="fft")
    # lags gives the amount of time shift used at each index, corresponding to the index of the correlate output list
    lags = signal.correlation_lags(audio1.size, audio2.size, mode="full")
    # lag is the time shift used at the point of maximum correlation - this is the key value used for shifting our audio/video
    lag = lags[np.argmax(correlation)]

    return lag


def find_first_brightness_change(
    video_pathstring: str, brightness_ratio_threshold: float = 1000
) -> int:
    logger.info(f"Detecting first brightness change in {video_pathstring}")
    brightness_array = find_brightness_across_frames(video_pathstring)
    brightness_difference = np.diff(brightness_array, prepend=brightness_array[0])
    brightness_double_difference = np.diff(
        brightness_difference, prepend=brightness_difference[0]
    )

    combined_brightness_metric = brightness_difference * brightness_double_difference

    first_brightness_change = np.argmax(
        combined_brightness_metric >= brightness_ratio_threshold
    )

    if first_brightness_change == 0:
        logger.info(
            "No brightness change exceeded threshold, defaulting to frame with fastest detected brightness change"
        )
        first_brightness_change = np.argmax(brightness_double_difference)
    else:
        logger.info(
            f"First brightness change detected at frame number {first_brightness_change}"
        )

    return int(first_brightness_change)


def find_brightness_across_frames(video_pathstring: str) -> np.ndarray:
    video_capture_object = cv2.VideoCapture(video_pathstring)

    video_framecount = int(video_capture_object.get(cv2.CAP_PROP_FRAME_COUNT))
    brightness_array = np.zeros(video_framecount)

    frame_number = 0

    while frame_number < video_framecount:
        ret, frame = video_capture_object.read()
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness_array[frame_number] = np.mean(gray_frame)
        frame_number += 1

    video_path = Path(video_pathstring)
    brightness_array_pathstring = f"{str(video_path.parent / video_path.stem)}{BRIGHTNESS_SUFFIX}.{NUMPY_EXTENSION}"
    np.save(file=brightness_array_pathstring, arr=brightness_array)

    return brightness_array


def normalize_lag_dictionary(lag_dictionary: Dict[str, float]) -> Dict[str, float]:
    """Subtract every value in the dict from the max value.
    This creates a normalized lag dict where the latest video has lag of 0.
    The max value lag represents the latest starting video."""

    normalized_lag_dictionary = {
        camera_name: (max(lag_dictionary.values()) - value)
        for camera_name, value in lag_dictionary.items()
    }

    return normalized_lag_dictionary


def find_cross_correlation_lags(
    audio_signal_dict: dict, sample_rate: int
) -> Dict[str, float]:
    """Take a dictionary of audio signals, as well as the sample rate of the audio, cross correlate the audio files, and output a lag dictionary.
    The lag dict is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
    """
    comparison_file_key = next(iter(audio_signal_dict))
    logger.info(
        f"comparison file is: {comparison_file_key}, sample rate is: {sample_rate}"
    )

    lag_dict = {
        single_audio_dict["camera name"]: cross_correlate(
            audio1=audio_signal_dict[comparison_file_key]["audio file"],
            audio2=single_audio_dict["audio file"],
        )
        / sample_rate
        for single_audio_dict in audio_signal_dict.values()
    }  # cross correlates all audio to the first audio file in the dict, and divides by the audio sample rate in order to get the lag in seconds

    normalized_lag_dict = normalize_lag_dictionary(lag_dictionary=lag_dict)

    logger.info(
        f"original lag dict: {lag_dict} normalized lag dict: {normalized_lag_dict}"
    )

    return normalized_lag_dict


def find_brightest_point_lags(
    video_info_dict: dict, frame_rate: float, brightness_ratio_threshold: float = 1000
) -> Dict[str, float]:
    """Take a video info dictionary, find the first significant contrast change in the video, and return its time in second as the lag.
    The lag dict is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
    """
    lag_dict = {
        video_dict["camera name"]: find_first_brightness_change(
            video_pathstring=str(video_dict["video pathstring"]),
            brightness_ratio_threshold=brightness_ratio_threshold,
        )
        / frame_rate
        for video_dict in video_info_dict.values()
    }

    return lag_dict
