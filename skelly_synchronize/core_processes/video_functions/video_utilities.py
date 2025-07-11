import logging
import multiprocessing
import tempfile
import shutil
from pathlib import Path
from typing import Dict

from skelly_synchronize.core_processes.audio_utilities import trim_audio_files
from skelly_synchronize.core_processes.video_functions.deffcode_functions import (
    trim_single_video_deffcode,
)
from skelly_synchronize.core_processes.video_functions.ffmpeg_functions import (
    attach_audio_to_video_ffmpeg,
    extract_video_duration_ffmpeg,
    extract_video_fps_ffmpeg,
    trim_single_video_ffmpeg,
)
from skelly_synchronize.system.file_extensions import AudioExtension, VideoExtension
from skelly_synchronize.utils.get_video_files import get_video_file_list
from skelly_synchronize.utils.path_handling_utilities import (
    name_synced_video,
)

logger = logging.getLogger(__name__)


def create_video_info_dict(
    video_filepath_list: list, video_handler: str = "ffmpeg"
) -> Dict[str, dict]:
    """Get a dictionary with video information from the given video file paths."""
    video_info_dict = dict()
    for video_filepath in video_filepath_list:
        video_dict = dict()
        video_dict["video filepath"] = Path(video_filepath)
        video_dict["video pathstring"] = str(video_filepath)
        video_name = Path(video_filepath).stem
        video_dict["camera name"] = video_name

        if video_handler == "ffmpeg":
            video_dict["video duration"] = extract_video_duration_ffmpeg(
                file_pathstring=str(video_filepath)
            )
            video_dict["video fps"] = extract_video_fps_ffmpeg(
                file_pathstring=str(video_filepath)
            )

        video_info_dict[video_name] = video_dict

    return video_info_dict


def trim_videos(
    video_info_dict: Dict[str, dict],
    synchronized_folder_path: Path,
    lag_dict: Dict[str, float],
    fps: float,
    video_handler: str = "deffcode",
) -> None:
    """Take a list of video files and a list of lags, and make all videos start and end at the same time."""

    if video_handler not in ["ffmpeg", "deffcode"]:
        raise ValueError("video_handler must be either 'ffmpeg' or 'deffcode'")

    minimum_duration = find_minimum_video_duration(
        video_info_dict=video_info_dict, lag_dict=lag_dict
    )
    minimum_frames = int(minimum_duration * fps)

    max_processes = min(len(video_info_dict), multiprocessing.cpu_count() - 1)

    with multiprocessing.Pool(processes=max_processes) as pool:
        pool.starmap(
            trim_single_video,
            [
                (
                    video_dict,
                    synchronized_folder_path,
                    minimum_duration,
                    minimum_frames,
                    lag_dict,
                    fps,
                    video_handler,
                )
                for video_dict in video_info_dict.values()
            ],
        )


def trim_single_video(
    video_dict: dict,
    synchronized_folder_path: Path,
    minimum_duration: float,
    minimum_frames: int,
    lag_dict: Dict[str, float],
    fps: float,
    video_handler: str = "deffcode",
) -> None:
    """Take a list of video files and a list of lags, and make all videos start and end at the same time."""

    try:
        logger.debug(f"trimming video file {video_dict['camera name']}")
        synced_video_name = name_synced_video(
            raw_video_filename=video_dict["camera name"]
        )

        start_time = lag_dict[video_dict["camera name"]]
        start_frame = int(start_time * fps)
        frame_list = get_frame_list(
            start_frame=start_frame, duration_frames=minimum_frames
        )

        if video_handler == "ffmpeg":
            logger.info(
                f"Saving video - Cam name: {video_dict['camera name']} - target duration: {minimum_duration} seconds"
            )
            trim_single_video_ffmpeg(
                input_video_pathstring=video_dict["video pathstring"],
                start_time=start_time,
                desired_duration=minimum_duration,
                output_video_pathstring=str(
                    synchronized_folder_path / synced_video_name
                ),
            )
            logger.info(
                f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration in Seconds: {minimum_duration}"
            )
        if video_handler == "deffcode":
            logger.info(
                f"Saving video - Cam name: {video_dict['camera name']} - start frame: {start_frame} - target duration: {minimum_frames} frames"
            )
            trim_single_video_deffcode(
                input_video_pathstring=video_dict["video pathstring"],
                frame_list=frame_list,
                output_video_pathstring=str(
                    synchronized_folder_path / synced_video_name
                ),
            )
            logger.info(
                f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration in Frames: {minimum_frames}"
            )
    except Exception as e:
        logger.error(
            f"Error trimming video {video_dict['camera name']}: {e}",
            exc_info=True,
        )
        raise e


def get_fps_list(video_info_dict: Dict[str, dict]):
    """Get list of the frames per second in each video"""
    return [video_dict["video fps"] for video_dict in video_info_dict.values()]


def get_frame_list(start_frame: int, duration_frames: int) -> list:
    """Get a list of frame numbers for video to be trimmed to"""
    return [start_frame + frame for frame in range(duration_frames)]


def find_minimum_video_duration(
    video_info_dict: Dict[str, dict], lag_dict: dict
) -> float:
    """Take a list of video files and a list of lags, and find what the shortest video is starting from each videos lag offset"""

    min_duration = min(
        [
            video_dict["video duration"] - lag_dict[video_dict["camera name"]]
            for video_dict in video_info_dict.values()
        ]
    )

    return min_duration


def attach_audio_to_videos(
    synchronized_video_folder_path: Path,
    audio_folder_path: Path,
    lag_dictionary: dict,
    synchronized_video_length: float,
):
    trimmed_audio_folder_path = trim_audio_files(
        audio_folder_path=audio_folder_path,
        lag_dictionary=lag_dictionary,
        synced_video_length=synchronized_video_length,
    )

    with tempfile.TemporaryDirectory(
        dir=str(synchronized_video_folder_path)
    ) as temp_dir:
        for video in get_video_file_list(synchronized_video_folder_path):
            video_name = video.stem
            if video_name.startswith("synced_"):
                audio_filename = f"{str(video_name).split('_', maxsplit=1)[-1]}.{AudioExtension.WAV.value}"
            else:
                audio_filename = f"{video_name}.{AudioExtension.WAV.value}"
            output_video_pathstring = str(
                Path(temp_dir)
                / f"{video_name}_with_audio_temp.{VideoExtension.MP4.value}"
            )

            logger.info(f"Attaching audio to video {video_name}")
            attach_audio_to_video_ffmpeg(
                input_video_pathstring=str(video),
                audio_file_pathstring=str(
                    Path(trimmed_audio_folder_path) / audio_filename
                ),
                output_video_pathstring=output_video_pathstring,
            )

            # overwrite synced video with video containing audio
            shutil.move(output_video_pathstring, video)
