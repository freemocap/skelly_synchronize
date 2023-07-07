import time
import logging
from pathlib import Path
from skelly_synchronize.core_processes.debugging.debug_plots import create_debug_plots

from skelly_synchronize.utils.get_video_files import get_video_file_list
from skelly_synchronize.core_processes.audio_utilities import (
    extract_audio_files,
    get_audio_sample_rates,
)
from skelly_synchronize.core_processes.correlation_functions import find_lags
from skelly_synchronize.core_processes.video_functions.video_utilities import (
    attach_audio_to_videos,
    get_fps_list,
    create_video_info_dict,
    trim_videos,
)
from skelly_synchronize.core_processes.debugging.debug_output import (
    remove_audio_files_from_audio_signal_dict,
    save_dictionaries_to_toml,
)
from skelly_synchronize.utils.path_handling_utilities import (
    create_directory,
)
from skelly_synchronize.tests.utilities.check_list_values_are_equal import (
    check_list_values_are_equal,
)
from skelly_synchronize.tests.utilities.get_number_of_frames_of_videos_in_a_folder import (
    get_number_of_frames_of_videos_in_a_folder,
)
from skelly_synchronize.system.paths_and_file_names import (
    AUDIO_NAME,
    DEBUG_TOML_NAME,
    LAG_DICTIONARY_NAME,
    RAW_VIDEO_NAME,
    SYNCHRONIZED_VIDEO_NAME,
    SYNCHRONIZED_VIDEOS_FOLDER_NAME,
    AUDIO_FILES_FOLDER_NAME,
)

logging.basicConfig(level=logging.INFO)


def synchronize_videos_from_audio(
    raw_video_folder_path: Path,
    synchronized_video_folder_path: Path = None,
    file_type: str = ".mp4",
    video_handler: str = "deffcode",
    create_debug_plots_bool: bool = True,
):
    """Run the functions from the VideoSynchronize class to synchronize all videos with the given file type in the base path folder.
    Uses deffcode and to handle the video files as default, set "video_handler" to "ffmpeg" to use ffmpeg methods instead.
    ffmpeg is used to get audio from the video files with either method.

    Returns the folder path of the synchronized video folder.
    """
    start_timer = time.time()

    video_file_list = get_video_file_list(
        folder_path=raw_video_folder_path, file_type=file_type
    )
    if synchronized_video_folder_path is None:
        synchronized_video_folder_path = create_directory(
            parent_directory=raw_video_folder_path.parent,
            directory_name=SYNCHRONIZED_VIDEOS_FOLDER_NAME,
        )
    synchronized_video_folder_path = Path(synchronized_video_folder_path)

    audio_folder_path = create_directory(
        parent_directory=synchronized_video_folder_path,
        directory_name=AUDIO_FILES_FOLDER_NAME,
    )

    # create dictionaries with video and audio information
    video_info_dict = create_video_info_dict(
        video_filepath_list=video_file_list, video_handler="ffmpeg"
    )
    audio_signal_dict = extract_audio_files(
        video_info_dict=video_info_dict,
        audio_extension="wav",
        audio_folder_path=audio_folder_path,
    )

    # get video fps and audio sample rate
    fps_list = get_fps_list(video_info_dict=video_info_dict)
    audio_sample_rates = get_audio_sample_rates(audio_signal_dict=audio_signal_dict)

    # frame rates and audio sample rates must be the same duration for the trimming process to work correctly
    fps = check_list_values_are_equal(input_list=fps_list)
    audio_sample_rate = check_list_values_are_equal(input_list=audio_sample_rates)

    # find the lags between starting times
    lag_dict = find_lags(
        audio_signal_dict=audio_signal_dict, sample_rate=audio_sample_rate
    )

    trim_videos(
        video_info_dict=video_info_dict,
        synchronized_folder_path=synchronized_video_folder_path,
        lag_dict=lag_dict,
        fps=fps,
        video_handler=video_handler,
    )

    synchronized_video_framecounts = get_number_of_frames_of_videos_in_a_folder(
        folder_path=synchronized_video_folder_path
    )
    logging.info(
        f"All videos are {check_list_values_are_equal(synchronized_video_framecounts)} frames long"
    )

    synchronized_video_info_dict = create_video_info_dict(
        video_filepath_list=get_video_file_list(
            synchronized_video_folder_path, file_type=file_type
        )
    )

    save_dictionaries_to_toml(
        input_dictionaries={
            RAW_VIDEO_NAME: video_info_dict,
            SYNCHRONIZED_VIDEO_NAME: synchronized_video_info_dict,
            AUDIO_NAME: remove_audio_files_from_audio_signal_dict(
                audio_signal_dictionary=audio_signal_dict
            ),
            LAG_DICTIONARY_NAME: lag_dict,
        },
        output_file_path=synchronized_video_folder_path / DEBUG_TOML_NAME,
    )

    attach_audio_to_videos(
        synchronized_video_folder_path=synchronized_video_folder_path,
        audio_folder_path=audio_folder_path,
        lag_dictionary=lag_dict,
        synchronized_video_length=next(iter(synchronized_video_info_dict.values()))[
            "video duration"
        ],
    )
    if create_debug_plots_bool:
        create_debug_plots(
            synchronized_video_folder_path=synchronized_video_folder_path
        )

    end_timer = time.time()

    logging.info(f"Elapsed processing time in seconds: {end_timer - start_timer}")

    return synchronized_video_folder_path


if __name__ == "__main__":
    raw_video_folder_path = Path("path/to/your/folder/of/raw/videos")
    file_type = "MP4"
    synchronize_videos_from_audio(
        raw_video_folder_path=raw_video_folder_path, file_type=file_type
    )
