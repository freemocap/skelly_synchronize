import logging
import subprocess
import shutil
from pathlib import Path
from typing import Union

from skelly_synchronize.system.file_extensions import AudioExtension

logger = logging.getLogger(__name__)

ffmpeg_string = "ffmpeg"
ffprobe_string = "ffprobe"


def check_for_ffmpeg() -> str:
    ffmpeg_pathstring = shutil.which(ffmpeg_string)
    if ffmpeg_pathstring is None:
        raise FileNotFoundError(
            "ffmpeg not found, please install ffmpeg and add it to your PATH"
        )

    return ffmpeg_pathstring


def check_for_ffprobe():
    if shutil.which(ffprobe_string) is None:
        raise FileNotFoundError(
            "ffprobe not found, please install ffmpeg and add it to your PATH"
        )


def parse_ffmpeg_output(output: str, file_pathstring: str) -> float:
    cleaned_out = (
        str(output)
        .replace("b'", "")
        .replace("'", "")
        .replace("\\n", "")
        .replace("\\r", "")
        .replace("\\t", "")
        .replace("\\", "")
    )

    try:
        output_as_float = float(cleaned_out)
    except (ValueError, RuntimeError):
        split_str = str(cleaned_out).split("/")
        if len(split_str) == 2:
            output_as_float = float(int(split_str[0])) / float((split_str[1]))
        else:
            raise RuntimeError(
                f"Unable to parse duration {output} from video {file_pathstring}"
            )

    return output_as_float


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
    extract_duration_subprocess = subprocess.run(
        [
            ffprobe_string,
            "-v",
            "error",
            "-select_streams",
            "v:0",
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

    video_duration = parse_ffmpeg_output(
        str(extract_duration_subprocess.stdout), file_pathstring
    )

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

    video_fps = parse_ffmpeg_output(str(extract_fps_subprocess.stdout), file_pathstring)

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

    if str(extract_sample_rate_subprocess.stdout) == "":
        raise ValueError(
            f"No audio file found for video {file_pathstring}, check that video has audio"
        )

    audio_sample_rate = parse_ffmpeg_output(
        str(extract_sample_rate_subprocess.stdout), file_pathstring
    )

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


if __name__ == "__main__":
    video_path = ""

    print(f"video duration: {extract_video_duration_ffmpeg(video_path)}")

    print(f"video fps: {extract_video_fps_ffmpeg(video_path)}")

    print(f"audio sample rate: {extract_audio_sample_rate_ffmpeg(video_path)}")
