import time
import logging
from pathlib import Path
from skelly_synchronize.core_processes.debug_output import (
    remove_audio_files_from_audio_signal_dict,
    save_dictionaries_to_toml,
)


logging.basicConfig(level=logging.INFO)

from skelly_synchronize.utils.get_video_files import get_video_file_list
from skelly_synchronize.core_processes.audio_utilities import (
    get_audio_files,
    get_audio_sample_rates,
)
from skelly_synchronize.core_processes.correlation_functions import find_lags
from skelly_synchronize.core_processes.video_functions.video_utilities import (
    get_fps_list,
    get_video_info_dict,
    trim_videos,
)
from skelly_synchronize.utils.path_handling_utilities import (
    get_parent_directory,
    create_directory,
)
from skelly_synchronize.tests.utilities.check_list_values_are_equal import (
    check_list_values_are_equal,
)
from skelly_synchronize.tests.utilities.get_number_of_frames_of_videos_in_a_folder import (
    get_number_of_frames_of_videos_in_a_folder,
)
from skelly_synchronize.system.paths_and_file_names import (
    DEBUG_TOML_NAME,
    SYNCHRONIZED_VIDEOS_FOLDER_NAME,
    AUDIO_FILES_FOLDER_NAME,
)


def synchronize_videos_from_audio(
    raw_video_folder_path: Path,
    file_type: str = ".mp4",
    video_handler: str = "deffcode",
):
    """Run the functions from the VideoSynchronize class to synchronize all videos with the given file type in the base path folder.
    Uses deffcode and to handle the video files as default, set "video_handler" to "ffmpeg" to use ffmpeg methods instead.
    ffmpeg is used to get audio from the video files with either method.
    """
    # start timer to measure performance
    start_timer = time.time()

    session_folder_path = get_parent_directory(raw_video_folder_path)
    video_file_list = get_video_file_list(
        folder_path=raw_video_folder_path, file_type=file_type
    )

    synchronized_video_folder_path = create_directory(
        parent_directory=session_folder_path,
        directory_name=SYNCHRONIZED_VIDEOS_FOLDER_NAME,
    )
    audio_folder_path = create_directory(
        parent_directory=session_folder_path, directory_name=AUDIO_FILES_FOLDER_NAME
    )

    # create dictionaries with video and audio information
    video_info_dict = get_video_info_dict(
        video_filepath_list=video_file_list, video_handler="ffmpeg"
    )
    audio_signal_dict = get_audio_files(
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

    synchronized_video_info_dict = get_video_info_dict(
        video_filepath_list=get_video_file_list(
            synchronized_video_folder_path, file_type=file_type
        )
    )

    save_dictionaries_to_toml(
        input_dictionaries={
            "Raw video information": video_info_dict,
            "Synchronized video information": synchronized_video_info_dict,
            "Audio information": remove_audio_files_from_audio_signal_dict(
                audio_signal_dictionary=audio_signal_dict
            ),
            "Lag dictionary": lag_dict,
        },
        output_file_path=session_folder_path / DEBUG_TOML_NAME,
    )

    # end performance timer
    end_timer = time.time()

    # calculate and display elapsed processing time
    elapsed_time = end_timer - start_timer
    logging.info(f"Elapsed processing time in seconds: {elapsed_time}")

    return synchronized_video_folder_path


if __name__ == "__main__":
    raw_video_folder_path = Path("path/to/your/folder/of/raw/videos")
    file_type = "MP4"
    synchronize_videos_from_audio(raw_video_folder_path=raw_video_folder_path, file_type=file_type)
