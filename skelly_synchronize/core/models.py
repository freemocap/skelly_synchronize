from enum import Enum
from pathlib import Path

from pydantic import BaseModel

VideoName = str  # alias for clarity in signatures


class VideoBackendKind(str, Enum):
    FFMPEG = "ffmpeg"
    DEFFCODE = "deffcode"


class SyncMethod(str, Enum):
    AUDIO = "audio cross-correlation"
    BRIGHTNESS = "brightness change detection"


class VideoInfo(BaseModel):
    filepath: Path
    video_name: str
    duration_seconds: float
    fps: float
    frame_count: int | None = None


class AudioInfo(BaseModel):
    filepath: Path
    video_name: str
    sample_rate: int
    duration_seconds: float
    # raw signal (np.ndarray) is intentionally NOT a field here


class LagResult(BaseModel):
    video_name: str
    lag_seconds: float
    confidence: float | None = None


class SyncRequest(BaseModel):
    raw_video_folder_path: Path
    synchronized_video_folder_path: Path | None = None
    method: SyncMethod
    video_handler: VideoBackendKind = VideoBackendKind.DEFFCODE
    brightness_ratio_threshold: float = 1000.0  # only used when method == BRIGHTNESS
    create_debug_artifacts: bool = True


class SyncResult(BaseModel):
    synchronized_video_folder_path: Path
    videos_before: list[VideoInfo]
    videos_after: list[VideoInfo]
    lags: list[LagResult]
    debug_artifact_paths: list[Path]
    elapsed_seconds: float
    # The single frame count shared by every synchronized video -- verified
    # identical across videos by VerifySynchronizedFrameCountStage
    synchronized_frame_count: int | None = None
