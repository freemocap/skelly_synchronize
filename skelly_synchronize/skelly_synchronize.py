import librosa
import time
import logging
import subprocess
import cv2
import numpy as np
import json
from scipy import signal
from pathlib import Path
from typing import Dict
from deffcode import FFdecoder

logging.basicConfig(level=logging.INFO)

from skelly_synchronize.utils.get_video_files import get_video_file_list
from skelly_synchronize.utils.path_handling_utilities import (
    get_parent_directory,
    get_file_name,
    create_directory,
)

from skelly_synchronize.utils.check_if_video_has_reversed_metadata import (
    check_if_video_has_reversed_metadata,
)
from skelly_synchronize.tests.utilities.check_list_values_are_equal import (
    check_list_values_are_equal,
)
from skelly_synchronize.tests.utilities.get_number_of_frames_of_videos_in_a_folder import (
    get_number_of_frames_of_videos_in_a_folder,
)


class VideoSynchronize:
    """Class of functions for time synchronizing and trimming video files based on cross correlation of their audio."""

    def __init__(self) -> None:
        """Initialize VideoSynchronize class"""
        logging.debug("VideoSynchronize class initialized")

    def synchronize(
        self,
        session_folder_path: Path,
        video_file_list: list,
        video_handler: str = "deffcode",
    ) -> list:
        """Run the functions from the VideoSynchronize class to synchronize all videos with the given file type in the base path folder.
        Uses deffcode and to handle the video files as default, set "video_handler" to "ffmpeg" to use ffmpeg methods instead.
        ffmpeg is used to get audio from the video files with either method.
        """

        self.synchronized_folder_path = create_directory(
            parent_directory=session_folder_path, directory_name="synchronized_videos"
        )
        self.audio_folder_path = create_directory(
            parent_directory=session_folder_path, directory_name="audio_files"
        )

        # create dictionaries with video and audio information
        video_info_dict = self._get_video_info_dict(
            video_filepath_list=video_file_list, video_handler="ffmpeg"
        )
        audio_signal_dict = self._get_audio_files(
            video_info_dict=video_info_dict, audio_extension="wav"
        )

        # get video fps and audio sample rate
        fps_list = self._get_fps_list(video_info_dict=video_info_dict)
        audio_sample_rates = self._get_audio_sample_rates(
            audio_signal_dict=audio_signal_dict
        )

        # frame rates and audio sample rates must be the same duration for the trimming process to work correctly
        fps = check_list_values_are_equal(input_list=fps_list)
        audio_sample_rate = check_list_values_are_equal(input_list=audio_sample_rates)

        # find the lags between starting times
        lag_dict = self._find_lags(
            audio_signal_dict=audio_signal_dict, sample_rate=audio_sample_rate
        )

        self._trim_videos(
            video_info_dict=video_info_dict,
            lag_dict=lag_dict,
            fps=fps,
            video_handler=video_handler,
        )

        synchronized_video_framecounts = get_number_of_frames_of_videos_in_a_folder(
            folder_path=self.synchronized_folder_path
        )
        logging.info(
            f"All videos are {check_list_values_are_equal(synchronized_video_framecounts)} frames long"
        )

    def _get_video_info_dict(
        self, video_filepath_list: list, video_handler: str = "ffmpeg"
    ) -> Dict[str, dict]:
        """Get a dictionary with video information from the given video file paths."""
        video_info_dict = dict()
        for video_filepath in video_filepath_list:
            video_dict = dict()
            video_dict["video filepath"] = video_filepath
            video_dict["video pathstring"] = str(video_filepath)
            video_name = get_file_name(video_filepath)
            video_dict["camera name"] = video_name

            if video_handler == "ffmpeg":
                video_dict["video duration"] = self._extract_video_duration_ffmpeg(
                    file_pathstring=str(video_filepath)
                )
                video_dict["video fps"] = self._extract_video_fps_ffmpeg(
                    file_pathstring=str(video_filepath)
                )

            video_info_dict[video_name] = video_dict

        return video_info_dict

    def _get_audio_files(
        self, video_info_dict: Dict[str, dict], audio_extension: str
    ) -> dict:
        """Get a dictionary with audio files and information from the given video file paths."""
        audio_signal_dict = dict()
        for video_dict in video_info_dict.values():
            self._extract_audio_from_video_ffmpeg(
                file_pathstring=video_dict["video pathstring"],
                file_name=video_dict["camera name"],
                output_folder_path=self.audio_folder_path,
                output_extension=audio_extension,
            )

            audio_name = video_dict["camera name"] + "." + audio_extension

            audio_signal, sample_rate = librosa.load(
                path=self.audio_folder_path / audio_name, sr=None
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

    def _get_fps_list(self, video_info_dict: Dict[str, dict]):
        """Get list of the frames per second in earch video"""
        return [video_dict["video fps"] for video_dict in video_info_dict.values()]

    def _find_lags(self, audio_signal_dict: dict, sample_rate: int) -> Dict[str, float]:
        """Take a file list containing video and audio files, as well as the sample rate of the audio, cross correlate the audio files, and output a lag list.
        The lag list is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
        """
        comparison_file_key = next(iter(audio_signal_dict))
        logging.info(
            f"comparison file is: {comparison_file_key}, sample rate is: {sample_rate}"
        )

        lag_dict = {
            single_audio_dict["camera name"]: self._cross_correlate(
                audio1=audio_signal_dict[comparison_file_key]["audio file"],
                audio2=single_audio_dict["audio file"],
            )
            / sample_rate
            for single_audio_dict in audio_signal_dict.values()
        }  # cross correlates all audio to the first audio file in the dict, and divides by the audio sample rate in order to get the lag in seconds

        normalized_lag_dict = self._normalize_lag_dictionary(lag_dictionary=lag_dict)

        logging.info(
            f"original lag dict: {lag_dict} normalized lag dict: {normalized_lag_dict}"
        )

        return normalized_lag_dict

    def _trim_videos(
        self,
        video_info_dict: Dict[str, dict],
        lag_dict: Dict[str, float],
        fps: float,
        video_handler: str = "deffcode",
    ) -> list:
        """Take a list of video files and a list of lags, and make all videos start and end at the same time."""

        minimum_duration = self._find_minimum_video_duration(
            video_info_dict=video_info_dict, lag_dict=lag_dict
        )
        minimum_frames = int(minimum_duration * fps)

        for video_dict in video_info_dict.values():
            logging.debug(f"trimming video file {video_dict['camera name']}")
            synced_video_name = self._name_synced_video(
                raw_video_filename=video_dict["camera name"]
            )

            start_time = lag_dict[video_dict["camera name"]]
            start_frame = int(start_time * fps)
            frame_list = self._get_frame_list(
                start_frame=start_frame, duration_frames=minimum_frames
            )

            if video_handler == "ffmpeg":
                logging.info(f"Saving video - Cam name: {video_dict['camera name']}")
                logging.info(f"desired saving duration is: {minimum_duration} seconds")
                self._trim_single_video_ffmpeg(
                    input_video_pathstring=video_dict["video pathstring"],
                    start_time=start_time,
                    desired_duration=minimum_duration,
                    output_video_pathstring=str(
                        self.synchronized_folder_path / synced_video_name
                    ),
                )
                logging.info(
                    f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration in Seconds: {minimum_duration}"
                )
            if video_handler == "deffcode":
                logging.info(f"Saving video - Cam name: {video_dict['camera name']}")
                logging.info(
                    f"start frame is: {start_frame} desired saving duration is: {minimum_frames} frames"
                )
                self._trim_single_video_deffcode(
                    input_video_pathstring=video_dict["video pathstring"],
                    frame_list=frame_list,
                    output_video_pathstring=str(
                        self.synchronized_folder_path / synced_video_name
                    ),
                )
                logging.info(
                    f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration in Frames: {minimum_frames}"
                )

    def _extract_audio_from_video_ffmpeg(
        self,
        file_pathstring: str,
        file_name: str,
        output_folder_path: Path,
        output_extension="wav",
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

    def _extract_video_duration_ffmpeg(self, file_pathstring: str):
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

    def _trim_single_video_deffcode(
        self,
        input_video_pathstring: str,
        frame_list: list,
        output_video_pathstring: str,
    ):
        vertical_video_bool = check_if_video_has_reversed_metadata(
            video_pathstring=input_video_pathstring
        )

        if vertical_video_bool:
            logging.info(
                f"Video has reversed metadata, changing FFmpeg transpose argument"
            )
            ffparams = {"-ffprefixes": ["-noautorotate"], "-vf": "transpose=1"}
        else:
            ffparams = {}

        decoder = FFdecoder(
            str(input_video_pathstring),
            frame_format="bgr24",
            verbose=True,
            **ffparams,
        ).formulate()

        metadata_dictionary = json.loads(decoder.metadata)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        framerate = metadata_dictionary["output_framerate"]
        framesize = tuple(metadata_dictionary["output_frames_resolution"])

        video_writer_object = cv2.VideoWriter(
            output_video_pathstring, fourcc, framerate, framesize
        )

        current_frame = 0
        written_frames = 0

        for frame in decoder.generateFrame():
            if frame is None:
                break

            if current_frame in frame_list:
                video_writer_object.write(frame)
                written_frames += 1

            if written_frames == len(frame_list):
                break

            current_frame += 1

        decoder.terminate()
        video_writer_object.release()

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

    def _get_frame_list(self, start_frame: int, duration_frames: int) -> list:
        """Get a list of frame numbers for video to be trimmed to"""
        return [start_frame + frame for frame in range(duration_frames)]

    def _get_audio_sample_rates(self, audio_signal_dict: Dict[str, float]) -> list:
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

    def _find_minimum_video_duration(
        self, video_info_dict: Dict[str, dict], lag_dict: dict
    ) -> float:
        """Take a list of video files and a list of lags, and find what the shortest video is starting from each videos lag offset"""

        min_duration = min(
            [
                video_dict["video duration"] - lag_dict[video_dict["camera name"]]
                for video_dict in video_info_dict.values()
            ]
        )

        return min_duration

    def _normalize_lag_dictionary(
        self, lag_dictionary: Dict[str, float]
    ) -> Dict[str, float]:
        """Subtract every value in the dict from the max value.
        This creates a normalized lag dict where the latest video has lag of 0.
        The max value lag represents the latest starting video."""

        normalized_lag_dictionary = {
            camera_name: (max(lag_dictionary.values()) - value)
            for camera_name, value in lag_dictionary.items()
        }

        return normalized_lag_dictionary

    def _name_synced_video(self, raw_video_filename: str) -> str:
        """Take a raw video filename, remove the raw prefix if its there, and return the synced video filename"""
        if raw_video_filename.split("_")[0] == "raw":
            synced_video_name = "synced_" + raw_video_filename[4:] + ".mp4"
        else:
            synced_video_name = "synced_" + raw_video_filename + ".mp4"

        return synced_video_name


def synchronize_videos(raw_video_folder_path: Path, file_type: str = ".mp4"):
    # start timer to measure performance
    start_timer = time.time()

    session_folder_path = get_parent_directory(raw_video_folder_path)
    video_file_list = get_video_file_list(
        folder_path=raw_video_folder_path, file_type=file_type
    )

    synchronize = VideoSynchronize()
    synchronize.synchronize(
        session_folder_path=session_folder_path,
        video_file_list=video_file_list,
    )
    synchronized_video_folder_path = synchronize.synchronized_folder_path

    # end performance timer
    end_timer = time.time()

    # calculate and display elapsed processing time
    elapsed_time = end_timer - start_timer
    logging.info(f"Elapsed processing time in seconds: {elapsed_time}")

    return synchronized_video_folder_path


if __name__ == "__main__":
    raw_video_folder_path = Path("path/to/your/folder/of/raw/videos")
    file_type = "MP4"
    synchronize_videos(raw_video_folder_path=raw_video_folder_path, file_type=file_type)
