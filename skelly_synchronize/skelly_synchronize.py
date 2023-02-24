import librosa
import time
import logging
import subprocess
import moviepy.editor as mp
import numpy as np
from scipy import signal
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO)

from utils.get_video_files import get_video_file_list


class VideoSynchronize:
    """Class of functions for time synchronizing and trimming video files based on cross correlation of their audio."""

    def __init__(self) -> None:
        """Initialize VideoSynchronize class"""
        logging.debug("VideoSynchronize class initialized")

    def synchronize(self, session_folder_path: Path, video_file_list: list) -> list:
        """Run the functions from the VideoSynchronize class to synchronize all videos with the given file type in the base path folder.
        Uses FFmpeg to handle the video files.
        """

        synchronized_video_folder_name = "SyncedVideos"
        self.synchronized_folder_path = (
            session_folder_path / synchronized_video_folder_name
        )
        audio_folder_name = "AudioFiles"
        self.audio_folder_path = session_folder_path / audio_folder_name

        # create synchronized video and audio file folders
        self.synchronized_folder_path.mkdir(parents=False, exist_ok=True)
        self.audio_folder_path.mkdir(parents=False, exist_ok=True)

        # create dictionaries with video and audio information
        video_info_dict = self._get_video_info_dict(video_file_list)
        audio_signal_dict = self._get_audio_files(
            video_info_dict, audio_extension="wav"
        )

        # get video fps and audio sample rate
        fps_list = self._get_fps_list(video_info_dict)
        audio_sample_rates = self.get_audio_sample_rates(audio_signal_dict)

        # frame rates and audio sample rates must be the same duration for the trimming process to work correctly
        self._check_rates(fps_list)
        self._check_rates(audio_sample_rates)

        # find the lags between starting times
        lag_dict = self._find_lags(audio_signal_dict, audio_sample_rates[0])

        synched_video_names = self._trim_videos(video_info_dict, lag_dict)
        return synched_video_names

    def _get_video_info_dict(self, video_filepath_list: list) -> Dict[str, dict]:
        video_info_dict = dict()
        for video_filepath in video_filepath_list:
            video_dict = dict()
            video_dict["video filepath"] = video_filepath
            video_dict["video pathstring"] = str(video_filepath)
            video_name = str(video_filepath).split("/")[-1]
            video_dict["camera name"] = video_name.split(".")[0]

            video_dict["video duration"] = self._extract_video_duration_ffmpeg(
                str(video_filepath)
            )
            video_dict["video fps"] = self._extract_video_fps_ffmpeg(
                str(video_filepath)
            )
            video_info_dict[video_name] = video_dict

        return video_info_dict

    def _get_audio_files(
        self, video_info_dict: Dict[str, dict], audio_extension: str
    ) -> dict:
        audio_signal_dict = dict()
        for video_dict in video_info_dict.values():
            self._extract_audio_from_video_ffmpeg(
                file_pathstring=video_dict["video pathstring"],
                file_name=video_dict["camera name"],
                output_folder_path=self.audio_folder_path,
                output_extension=audio_extension,
            )

            audio_name = video_dict["camera name"] + "." + audio_extension

            audio_signal, audio_rate = librosa.load(
                self.audio_folder_path / audio_name, sr=None
            )
            audio_signal_dict[audio_name] = {
                "audio file": audio_signal,
                "sample rate": audio_rate,
                "camera name": video_dict["camera name"],
            }

        return audio_signal_dict

    def _get_fps_list(self, video_info_dict: Dict[str, dict]):
        return [video_dict["video fps"] for video_dict in video_info_dict.values()]

    def _check_rates(self, rate_list: list):
        """Check if audio sample rates or video frame rates are equal, throw an exception if not (or if no rates are given)."""
        if len(rate_list) == 0:
            raise Exception("no rates given")

        if rate_list.count(rate_list[0]) == len(rate_list):
            logging.debug(f"all rates are equal to {rate_list[0]}")
            return rate_list[0]
        else:
            raise Exception(f"rates are not equal, rates are {rate_list}")

    def _find_lags(self, audio_signal_dict: dict, sample_rate: int) -> Dict[str, float]:
        """Take a file list containing video and audio files, as well as the sample rate of the audio, cross correlate the audio files, and output a lag list.
        The lag list is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
        """
        comparison_file_key = next(iter(audio_signal_dict))
        lag_dict = {
            single_audio_dict["camera name"]: self._cross_correlate(
                audio_signal_dict[comparison_file_key]["audio file"],
                single_audio_dict["audio file"],
            )
            / sample_rate
            for single_audio_dict in audio_signal_dict.values()
        }  # cross correlates all audio to the first audio file in the list, and divides by the audio sample rate in order to get the lag in seconds

        normalized_lag_dict = self._normalize_lag_dictionary(lag_dict)

        logging.debug(
            f"original lag list: {lag_dict} normalized lag list: {normalized_lag_dict}"
        )

        return normalized_lag_dict

    def _trim_videos(self, video_info_dict: Dict[str, dict], lag_dict: Dict[str, float]) -> list:
        """Take a list of video files and a list of lags, and make all videos start and end at the same time."""

        min_duration = self._find_minimum_video_duration(video_info_dict, lag_dict)
        trimmed_video_filenames = []  # can be used for plotting

        for video_dict in video_info_dict.values():
            logging.debug(f"trimming video file {video_dict['camera name']}")
            if video_dict["camera name"].split("_")[0] == "raw":
                synced_video_name = "synced_" + video_dict["camera name"][4:] + ".mp4"
            else:
                synced_video_name = "synced_" + video_dict["camera name"] + ".mp4"
            trimmed_video_filenames.append(
                synced_video_name
            )  # add new name to list to reference for plotting
            logging.info(f"Saving video - Cam name: {video_dict['camera name']}")
            self._trim_single_video_ffmpeg(
                input_video_pathstring=video_dict["video pathstring"],
                start_time=lag_dict[video_dict["camera name"]],
                desired_duration=min_duration,
                output_video_pathstring=str(
                    self.synchronized_folder_path / synced_video_name
                ),
            )
            logging.info(
                f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration: {min_duration}"
            )

        return trimmed_video_filenames

    def _extract_audio_from_video_ffmpeg(
        self, file_pathstring: str, file_name: str, output_folder_path: Path, output_extension="wav"
    ):
        """Run a subprocess call to extract the audio from a video file using ffmpeg"""

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                file_pathstring,
                f"{output_folder_path}/{file_name}.{output_extension}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def _extract_video_duration_ffmpeg(self, file_pathstring:str):
        """Run a subprocess call to get the duration from a video file using ffmpeg"""

        extract_duration_subprocess = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_pathstring,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        video_duration = float(extract_duration_subprocess.stdout)

        return video_duration

    def _extract_video_fps_ffmpeg(self, file_pathstring: str):
        """Run a subprocess call to get the fps of a video file using ffmpeg"""

        extract_fps_subprocess = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_pathstring,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # get the results, then remove the excess characters to get something like '####/###'
        cleaned_stdout = str(extract_fps_subprocess.stdout).split("'")[1].split("\\")[0]
        # separate out numerator and denominator to calculate the fraction
        numerator, denominator = cleaned_stdout.split("/")
        video_fps = float(int(numerator) / int(denominator))

        return video_fps

    def _trim_single_video_ffmpeg(
        self,
        input_video_pathstring: str,
        start_time: float,
        desired_duration: float,
        output_video_pathstring: str,
    ):
        """Run a subprocess call to trim a video from start time to last as long as the desired duration"""

        trim_video_subprocess = subprocess.run(
            [
                "ffmpeg",
                "-i",
                f"{input_video_pathstring}",
                "-ss",
                f"{start_time}",
                "-t",
                f"{desired_duration}",
                "-y",
                f"{output_video_pathstring}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def get_audio_sample_rates(self, audio_signal_dict: Dict[str, float]) -> list:
        """Get the sample rates of each audio file and return them in a list"""
        audio_sample_rate_list = [
            single_audio_dict["sample rate"]
            for single_audio_dict in audio_signal_dict.values()
        ]

        return audio_sample_rate_list

    def _normalize_audio(self, audio_file):
        """Perform z-score normalization on an audio file and return the normalized audio file - this is best practice for correlating."""
        return (audio_file - np.mean(audio_file)) / np.std(
            audio_file - np.mean(audio_file)
        )

    def _cross_correlate(self, audio1, audio2):
        """Take two audio files, synchronize them using cross correlation, and trim them to the same length.
        Inputs are two WAV files to be synchronizeded. Return the lag expressed in terms of the audio sample rate of the clips.
        """

        # compute cross correlation with scipy correlate function, which gives the correlation of every different lag value
        # mode='full' makes sure every lag value possible between the two signals is used, and method='fft' uses the fast fourier transform to speed the process up
        correlation = signal.correlate(audio1, audio2, mode="full", method="fft")
        # lags gives the amount of time shift used at each index, corresponding to the index of the correlate output list
        lags = signal.correlation_lags(audio1.size, audio2.size, mode="full")
        # lag is the time shift used at the point of maximum correlation - this is the key value used for shifting our audio/video
        lag = lags[np.argmax(correlation)]

        return lag

    def _find_minimum_video_duration(
        self, video_info_dict: Dict[str, dict], lag_list: list
    ) -> float:
        """Take a list of video files and a list of lags, and find what the shortest video is starting from each videos lag offset"""

        min_duration = min(
            [
                video_dict["video duration"] - lag_list[video_dict["camera name"]]
                for video_dict in video_info_dict.values()
            ]
        )

        return min_duration

    def _normalize_lag_dictionary(self, lag_dictionary: Dict[str, float]) -> Dict[str, float]:
        """Subtract every value in the dict from the max value.
        This creates a normalized lag dict where the latest video has lag of 0.
        The max value lag represents the latest starting video."""

        normalized_lag_dictionary = {
            camera_name: (max(lag_dictionary.values()) - value)
            for camera_name, value in lag_dictionary.items()
        }

        return normalized_lag_dictionary


def main(sessionID: str, fmc_data_path: Path, file_type: str):
    # start timer to measure performance
    start_timer = time.time()
    session_folder_path = fmc_data_path / sessionID

    raw_video_folder_name = "RawVideos"
    raw_video_folder_path = session_folder_path / raw_video_folder_name

    video_file_list = get_video_file_list(raw_video_folder_path, ".mp4")

    synchronize = VideoSynchronize()
    synchronize.synchronize(session_folder_path, video_file_list)

    # end performance timer
    end_timer = time.time()

    # calculate and display elapsed processing time
    elapsed_time = end_timer - start_timer
    logging.info(f"Elapsed processing time in seconds: {elapsed_time}")


if __name__ == "__main__":
    sessionID = "iPhoneTesting"
    freemocap_data_path = Path(
        "/Users/philipqueen/Documents/Humon Research Lab/FreeMocap_Data"
    )
    file_type = "MP4"
    main(sessionID, freemocap_data_path, file_type)
