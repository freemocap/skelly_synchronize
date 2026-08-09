from enum import Enum

NUMPY_EXTENSION = "npy"


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
