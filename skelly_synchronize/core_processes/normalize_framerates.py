from pathlib import Path
from typing import Dict, List, Optional
from skelly_synchronize.core_processes.video_functions.ffmpeg_functions import (
    normalize_framerates_in_video_ffmpeg,
)
from skelly_synchronize.system.file_extensions import VideoExtension
from skelly_synchronize.system.paths_and_file_names import NORMALIZED_VIDEOS_FOLDER_NAME

from skelly_synchronize.utils.path_handling_utilities import create_directory

standard_audio_sample_rate = 44100


def normalize_framerates(
    raw_video_folder_path: Path,
    video_info_dict: Dict[str, dict],
    fps_list: List[float],
    audio_samplerate_list: Optional[List[float]] = None,
) -> Path:
    """Normalize the frame rates of a list of videos. Also normalize audio sample rates, if given"""
    normalized_videos_folder_path = create_directory(
        parent_directory=raw_video_folder_path,
        directory_name=NORMALIZED_VIDEOS_FOLDER_NAME,
    )

    fps_list.sort()
    desired_fps = min(fps_list)

    if audio_samplerate_list:
        audio_samplerate_list.sort()
        desired_audio_sample_rate = min(audio_samplerate_list)
    else:
        desired_audio_sample_rate = standard_audio_sample_rate

    for video_dict in video_info_dict.values():
        normalize_framerates_in_video_ffmpeg(
            input_video_pathstring=str(video_dict["video pathstring"]),
            output_video_pathstring=str(
                normalized_videos_folder_path
                / f"{video_dict['camera name']}.{VideoExtension.MP4.value}"
            ),
            desired_fps=desired_fps,
            desired_sample_rate=int(desired_audio_sample_rate),
        )

    return normalized_videos_folder_path
