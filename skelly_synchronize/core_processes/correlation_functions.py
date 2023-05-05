import logging
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


def normalize_lag_dictionary(lag_dictionary: Dict[str, float]) -> Dict[str, float]:
    """Subtract every value in the dict from the max value.
    This creates a normalized lag dict where the latest video has lag of 0.
    The max value lag represents the latest starting video."""

    normalized_lag_dictionary = {
        camera_name: (max(lag_dictionary.values()) - value)
        for camera_name, value in lag_dictionary.items()
    }

    return normalized_lag_dictionary


def find_lags(audio_signal_dict: dict, sample_rate: int) -> Dict[str, float]:
    """Take a file list containing video and audio files, as well as the sample rate of the audio, cross correlate the audio files, and output a lag list.
    The lag list is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
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
