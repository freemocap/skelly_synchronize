import logging
import subprocess
import shutil
from pathlib import Path
from typing import Union

from skelly_synchronize.system.file_extensions import AudioExtension

logger = logging.getLogger(__name__)

ffmpeg_string = "ffmpeg"
ffprobe_string = "ffprobe"


def check_for_ffmpeg():
    if shutil.which(ffmpeg_string) is None:
        raise FileNotFoundError(
            "ffmpeg not found, please install ffmpeg and add it to your PATH"
        )


def check_for_ffprobe():
    if shutil.which(ffprobe_string) is None:
        raise FileNotFoundError(
            "ffprobe not found, please install ffmpeg and add it to your PATH"
        )


def extract_audio_from_video_ffmpeg(
    file_pathstring: str, output_file_path: Union[Path, str]
):
    """Run a subprocess call to extract the audio from a video file using ffmpeg"""
    check_for_ffmpeg()
    if str(Path(output_file_path).suffix).strip(".") not in {
        extension.value for extension in AudioExtension
    }:
        raise ValueError(
            f"output path {Path(output_file_path).suffix} is not a valid audio extension, extracting audio requires a valid audio extension"
        )

    extract_audio_subprocess = subprocess.run(
        [
            ffmpeg_string,
            "-y",
            "-i",
            file_pathstring,
            str(output_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if extract_audio_subprocess.returncode != 0:
        raise RuntimeError(
            f"Unable to extract audio from video file {file_pathstring}, check that video has audio"
        )


def extract_video_duration_ffmpeg(file_pathstring: str):
    """Run a subprocess call to get the duration from a video file using ffmpeg"""

    check_for_ffprobe()
    extract_duration_subprocess = subprocess.run(
        [
            ffprobe_string,
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

    if extract_duration_subprocess.returncode != 0:
        raise RuntimeError(
            f"extract duration subprocess failed for video {file_pathstring} with return code {extract_duration_subprocess.returncode}"
        )

    video_duration = float(extract_duration_subprocess.stdout)

    return video_duration


def extract_video_fps_ffmpeg(file_pathstring: str):
    """Run a subprocess call to get the fps of a video file using ffmpeg"""

    check_for_ffprobe()
    extract_fps_subprocess = subprocess.run(
        [
            ffprobe_string,
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
    if extract_fps_subprocess.returncode != 0:
        raise RuntimeError(
            f"extract fps subprocess failed for video {file_pathstring} with return code {extract_fps_subprocess.returncode}"
        )

    # get the results, then remove the excess characters to get something like '####/###'
    cleaned_stdout = str(extract_fps_subprocess.stdout).split("'")[1].split("\\")[0]
    # separate out numerator and denominator to calculate the fraction
    numerator, denominator = cleaned_stdout.split("/")
    video_fps = float(int(numerator) / int(denominator))

    return video_fps


def extract_audio_sample_rate_ffmpeg(file_pathstring: str):
    """Run a subprocess call to get the audio sample rate of a video file using ffmpeg"""

    check_for_ffprobe()
    extract_sample_rate_subprocess = subprocess.run(
        [
            ffprobe_string,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_pathstring,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if extract_sample_rate_subprocess.returncode != 0:
        raise RuntimeError(
            f"extract sample rate subprocess failed for video {file_pathstring} with return code {extract_sample_rate_subprocess.returncode}"
        )

    # get the result, then remove the excess characters to get something like '####'
    cleaned_stdout = (
        str(extract_sample_rate_subprocess.stdout).split("'")[1].split("\\")[0]
    )
    # convert to float
    audio_sample_rate = float(cleaned_stdout)

    return audio_sample_rate


def normalize_framerates_in_video_ffmpeg(
    input_video_pathstring: str,
    output_video_pathstring: str,
    desired_fps: float = 30,
    desired_sample_rate: int = 44100,
):
    """Run a subprocess call to normalize the framerate and audio sample rate of a video file using ffmpeg"""

    check_for_ffmpeg()
    normalize_framerates_subprocess = subprocess.run(
        [
            ffmpeg_string,
            "-i",
            f"{input_video_pathstring}",
            "-r",
            f"{desired_fps}",
            "-ar",
            f"{desired_sample_rate}",
            "-y",
            f"{output_video_pathstring}",
        ]
    )

    if normalize_framerates_subprocess.returncode != 0:
        raise RuntimeError(
            f"Error normalizing video framerate in {input_video_pathstring} with target fps {desired_fps} and target sample rate {desired_sample_rate}, ffmpeg returned code {normalize_framerates_subprocess.returncode}"
        )


def trim_single_video_ffmpeg(
    input_video_pathstring: str,
    start_time: float,
    desired_duration: float,
    output_video_pathstring: str,
):
    """Run a subprocess call to trim a video from start time to last as long as the desired duration"""
    check_for_ffmpeg()
    trim_video_subprocess = subprocess.run(
        [
            ffmpeg_string,
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

    if trim_video_subprocess.returncode != 0:
        raise RuntimeError(
            f"trim video subprocess failed for video {input_video_pathstring} with return code {trim_video_subprocess.returncode}"
        )


def attach_audio_to_video_ffmpeg(
    input_video_pathstring: str,
    audio_file_pathstring: str,
    output_video_pathstring: str,
):
    """Run a subprocess call to attach audio file back to the video"""

    check_for_ffmpeg()
    attach_audio_subprocess = subprocess.run(
        [
            ffmpeg_string,
            "-i",
            f"{input_video_pathstring}",
            "-i",
            f"{audio_file_pathstring}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            f"{output_video_pathstring}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if attach_audio_subprocess.returncode != 0:
        raise RuntimeError(
            f"Error occurred attaching audio to video {input_video_pathstring} with return code {attach_audio_subprocess.returncode}"
        )
