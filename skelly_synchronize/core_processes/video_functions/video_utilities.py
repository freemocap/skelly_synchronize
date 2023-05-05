import logging
from pathlib import Path
from typing import Dict
from skelly_synchronize.core_processes.video_functions.deffcode_functions import (
    trim_single_video_deffcode,
)

from skelly_synchronize.core_processes.video_functions.ffmpeg_functions import (
    extract_video_duration_ffmpeg,
    extract_video_fps_ffmpeg,
    trim_single_video_ffmpeg,
)
from skelly_synchronize.utils.path_handling_utilities import (
    get_file_name,
    name_synced_video,
)


def get_video_info_dict(
    video_filepath_list: list, video_handler: str = "ffmpeg"
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
) -> list:
    """Take a list of video files and a list of lags, and make all videos start and end at the same time."""

    minimum_duration = find_minimum_video_duration(
        video_info_dict=video_info_dict, lag_dict=lag_dict
    )
    minimum_frames = int(minimum_duration * fps)

    for video_dict in video_info_dict.values():
        logging.debug(f"trimming video file {video_dict['camera name']}")
        synced_video_name = name_synced_video(
            raw_video_filename=video_dict["camera name"]
        )

        start_time = lag_dict[video_dict["camera name"]]
        start_frame = int(start_time * fps)
        frame_list = get_frame_list(
            start_frame=start_frame, duration_frames=minimum_frames
        )

        if video_handler == "ffmpeg":
            logging.info(f"Saving video - Cam name: {video_dict['camera name']}")
            logging.info(f"desired saving duration is: {minimum_duration} seconds")
            trim_single_video_ffmpeg(
                input_video_pathstring=video_dict["video pathstring"],
                start_time=start_time,
                desired_duration=minimum_duration,
                output_video_pathstring=str(
                    synchronized_folder_path / synced_video_name
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
            trim_single_video_deffcode(
                input_video_pathstring=video_dict["video pathstring"],
                frame_list=frame_list,
                output_video_pathstring=str(
                    synchronized_folder_path / synced_video_name
                ),
            )
            logging.info(
                f"Video Saved - Cam name: {video_dict['camera name']}, Video Duration in Frames: {minimum_frames}"
            )


def get_fps_list(video_info_dict: Dict[str, dict]):
    """Get list of the frames per second in earch video"""
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
