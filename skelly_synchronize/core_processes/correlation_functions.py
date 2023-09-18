import logging
import cv2
import numpy as np
from typing import Dict
from scipy import signal


def cross_correlate(audio1, audio2):
    """Take two audio files, synchronize them using cross correlation, and trim them to the same length.
    Inputs are two WAV files to be synchronized. Return the lag expressed in terms of the audio sample rate of the clips.
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
    video_pathstring: str, brightness_ratio_threshold: float = 4
) -> int:
    logging.info(f"Detecting first brightness change in {video_pathstring}")
    video_capture_object = cv2.VideoCapture(video_pathstring)

    ret, frame = video_capture_object.read()
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    previous_frame_brightness = np.mean(gray_frame)

    brightness_ratio = 1
    highest_brightness_ratio = 1
    frame_number = 0
    brightest_frame_yet = 0

    while ret and brightness_ratio < brightness_ratio_threshold:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_frame_brightness = np.mean(gray_frame)

        brightness_ratio = current_frame_brightness / previous_frame_brightness

        if brightness_ratio > highest_brightness_ratio:
            highest_brightness_ratio = brightness_ratio
            brightest_frame_yet = frame_number

        ret, frame = video_capture_object.read()
        frame_number += 1

    if brightness_ratio > brightness_ratio_threshold:
        logging.info(f"First brightness change detected at frame number {frame_number}")
    else:
        logging.info(
            f"First brightness change not detected, defaulting to frame with largest detected brightness ratio of {highest_brightness_ratio}"
        )

    return brightest_frame_yet


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
    logging.info(
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

    logging.info(
        f"original lag dict: {lag_dict} normalized lag dict: {normalized_lag_dict}"
    )

    return normalized_lag_dict


def find_brightest_point_lags(
    video_info_dict: dict, frame_rate: float, brightness_ratio_threshold: float = 3
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


if __name__ == "__main__":
    video_pathstring = "/Users/philipqueen/Downloads/first_brightness_change_check.mov"
    brightness_change = find_first_brightness_change(
        video_pathstring=video_pathstring, brightness_ratio_threshold=4
    )
    print(brightness_change)
