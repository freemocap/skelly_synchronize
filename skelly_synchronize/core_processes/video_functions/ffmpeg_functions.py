import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

ffmpeg_string = "ffmpeg"
ffprobe_string = "ffprobe"

def check_for_ffmpeg():
    if shutil.which(ffmpeg_string) is None:
        raise FileNotFoundError("ffmpeg not found, please install ffmpeg and add it to your PATH")
    
def check_for_ffprobe():
    if shutil.which(ffprobe_string) is None:
        raise FileNotFoundError("ffprobe not found, please install ffmpeg and add it to your PATH")

def extract_audio_from_video_ffmpeg(
    file_pathstring: str,
    file_name: str,
    output_folder_path: Path,
    output_extension="wav",
):
    """Run a subprocess call to extract the audio from a video file using ffmpeg"""

    check_for_ffmpeg()
    subprocess.run(
        [
            ffmpeg_string,
            "-y",
            "-i",
            file_pathstring,
            f"{output_folder_path}/{file_name}.{output_extension}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
        raise Exception(
            f"ffmpeg returned code {normalize_framerates_subprocess.returncode}"
        )


def trim_single_video_ffmpeg(
    input_video_pathstring: str,
    start_time: float,
    desired_duration: float,
    output_video_pathstring: str,
):
    """Run a subprocess call to trim a video from start time to last as long as the desired duration"""

    check_for_ffmpeg()
    subprocess.run(
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
        logger.error(f"Error occurred: {attach_audio_subprocess.stderr.decode('utf-8')}")
