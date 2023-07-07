import subprocess
from pathlib import Path


def extract_audio_from_video_ffmpeg(
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


def extract_video_duration_ffmpeg(file_pathstring: str):
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


def extract_video_fps_ffmpeg(file_pathstring: str):
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


def trim_single_video_ffmpeg(
    input_video_pathstring: str,
    start_time: float,
    desired_duration: float,
    output_video_pathstring: str,
):
    """Run a subprocess call to trim a video from start time to last as long as the desired duration"""

    subprocess.run(
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


def attach_audio_to_video_ffmpeg(
    input_video_pathstring: str,
    audio_file_pathstring: str,
    output_video_pathstring: str,
):
    """Run a subprocess call to attach audio file back to the video"""

    attach_audio_subprocess = subprocess.run(
        [
            "ffmpeg",
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
        print(f"Error occurred: {attach_audio_subprocess.stderr.decode('utf-8')}")
