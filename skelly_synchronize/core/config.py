from enum import Enum

# directory names
SYNCHRONIZED_VIDEOS_FOLDER_NAME = "synchronized_videos"
RAW_VIDEOS_FOLDER_NAME = "raw_videos"
AUDIO_FILES_FOLDER_NAME = "audio_files"
TRIMMED_AUDIO_FOLDER_NAME = "trimmed_audio"
NORMALIZED_VIDEOS_FOLDER_NAME = "normalized_videos"

# file names
DEBUG_TOML_NAME = "synchronization_debug.toml"
DEBUG_PLOT_NAME = "debug_plot.png"
NUMPY_EXTENSION = "npy"

# naming conventions
SYNCED_VIDEO_PRECURSOR = "synced_"
RAW_VIDEO_PREFIX = "raw_"
BRIGHTNESS_SUFFIX = "_brightness"

# audio defaults
STANDARD_AUDIO_SAMPLE_RATE = 44100

# subprocess defaults
FFMPEG_SUBPROCESS_TIMEOUT_SECONDS = 30
FFMPEG_ENCODE_SUBPROCESS_TIMEOUT_SECONDS = 1800


class AudioExtension(Enum):
    WAV = "wav"
    FLAC = "flac"
    MP3 = "mp3"
    AAC = "aac"


class VideoExtension(Enum):
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MPEG = "mpeg"
    MOV = "mov"


def synced_video_filename(raw_video_filename: str) -> str:
    """Take a raw video filename, strip the raw prefix if present, and return the synced video filename."""
    stripped_name = str(raw_video_filename).removeprefix(RAW_VIDEO_PREFIX)
    return f"{SYNCED_VIDEO_PRECURSOR}{stripped_name}.{VideoExtension.MP4.value}"
