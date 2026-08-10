import logging
import os
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Protocol

import cv2
import librosa
from pydantic import BaseModel, ConfigDict, Field

from skelly_synchronize.core.audio import (
    find_cross_correlation_lags,
    trim_audio_in_memory,
)
from skelly_synchronize.core.backends.base import get_backend
from skelly_synchronize.core.backends.ffmpeg import (
    FfmpegBackend,
    attach_audio,
    extract_audio,
    extract_audio_sample_rate,
    normalize_framerate_and_sample_rate,
)
from skelly_synchronize.core.brightness import (
    compute_brightness_series,
    find_first_brightness_change,
    save_brightness_series,
)
from skelly_synchronize.core.config import (
    AUDIO_FILES_FOLDER_NAME,
    BRIGHTNESS_SUFFIX,
    DEBUG_PLOT_NAME,
    DEBUG_TOML_NAME,
    NORMALIZED_VIDEOS_FOLDER_NAME,
    NUMPY_EXTENSION,
    STANDARD_AUDIO_SAMPLE_RATE,
    SYNCHRONIZED_VIDEOS_FOLDER_NAME,
    TRIMMED_AUDIO_FOLDER_NAME,
    AudioExtension,
    VideoExtension,
    synced_video_filename,
)
from skelly_synchronize.core.debug import (
    plot_audio_waveforms,
    plot_brightness_series,
    save_debug_toml,
)
from skelly_synchronize.core.discovery import get_video_file_list
from skelly_synchronize.core.exceptions import SkellySyncError
from skelly_synchronize.core.models import (
    LagResult,
    SyncMethod,
    SyncRequest,
    VideoBackendKind,
    VideoInfo,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]


class PipelineContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request: SyncRequest
    synchronized_folder_path: Path | None = None
    discovered_paths: list[Path] = Field(default_factory=list)
    videos: list[VideoInfo] = Field(default_factory=list)
    videos_before: list[VideoInfo] = Field(default_factory=list)
    pre_trim_videos: list[VideoInfo] = Field(default_factory=list)
    normalized_folder_path: Path | None = None
    lags: list[LagResult] = Field(default_factory=list)
    audio_folder_path: Path | None = None
    audio_signals: dict | None = (
        None  # dict[str, np.ndarray]; kept outside typed models
    )
    audio_sample_rate: int | None = None
    synchronized_fps: float | None = None
    synchronized_frame_count: int | None = None
    debug_artifact_paths: list[Path] = Field(default_factory=list)


class PipelineStage(Protocol):
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext: ...


class SetupOutputFolderStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        request = context.request
        if request.synchronized_video_folder_path is not None:
            output_folder = Path(request.synchronized_video_folder_path)
        else:
            output_folder = (
                Path(request.raw_video_folder_path).parent
                / SYNCHRONIZED_VIDEOS_FOLDER_NAME
            )
        output_folder.mkdir(parents=True, exist_ok=True)
        context.synchronized_folder_path = output_folder
        return context


class DiscoverVideosStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        context.discovered_paths = get_video_file_list(
            context.request.raw_video_folder_path
        )
        return context


def _count_video_frames(filepath: Path) -> int:
    """Read the actual frame count out of a video file's container metadata."""
    capture = cv2.VideoCapture(str(filepath))
    try:
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()


def _probe_with_frame_count(backend, filepath: Path) -> VideoInfo:
    """Probe a video and attach its real frame count.

    Frame count isn't part of what ffprobe's duration/fps query returns, so
    it's filled in as a second, explicit step wherever a `VideoInfo` is
    built -- for raw videos, normalized videos, and trimmed/synced videos
    alike -- so every stage of the pipeline reports it consistently.
    """
    video_info = backend.probe(filepath)
    return video_info.model_copy(update={"frame_count": _count_video_frames(filepath)})


class ProbeStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        backend = FfmpegBackend()
        context.videos = [
            _probe_with_frame_count(backend, path) for path in context.discovered_paths
        ]
        context.videos_before = list(context.videos)
        return context


class NormalizeFramerateStage:
    """Conditional: only runs if fps (or, for audio, sample rate) diverges.

    Encapsulates the re-probe against its own output so callers never have to
    manually re-run discovery/probing (resolves KI-05).
    """

    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        videos = context.videos
        fps_values = {video.fps for video in videos}

        sample_rates: set[int] | None = None
        if context.request.method == SyncMethod.AUDIO:
            sample_rates = {
                extract_audio_sample_rate(video.filepath) for video in videos
            }

        needs_normalize = len(fps_values) > 1 or (
            sample_rates is not None and len(sample_rates) > 1
        )
        if not needs_normalize:
            return context

        target_fps = min(fps_values)
        target_sample_rate = (
            int(min(sample_rates)) if sample_rates else STANDARD_AUDIO_SAMPLE_RATE
        )

        normalized_folder = (
            Path(context.request.raw_video_folder_path) / NORMALIZED_VIDEOS_FOLDER_NAME
        )
        normalized_folder.mkdir(parents=True, exist_ok=True)

        for video in videos:
            output_path = (
                normalized_folder / f"{video.camera_name}.{VideoExtension.MP4.value}"
            )
            normalize_framerate_and_sample_rate(
                video.filepath, output_path, target_fps, target_sample_rate
            )

        context.normalized_folder_path = normalized_folder

        backend = FfmpegBackend()
        context.videos = [
            _probe_with_frame_count(backend, path)
            for path in get_video_file_list(normalized_folder)
        ]
        return context


class AudioLagStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        audio_folder = context.synchronized_folder_path / AUDIO_FILES_FOLDER_NAME
        audio_folder.mkdir(parents=True, exist_ok=True)

        audio_signals = {}
        sample_rate = None
        for video in context.videos:
            audio_path = (
                audio_folder / f"{video.camera_name}.{AudioExtension.WAV.value}"
            )
            extract_audio(video.filepath, audio_path)
            camera_signal, sample_rate = librosa.load(path=audio_path, sr=None)
            audio_signals[video.camera_name] = camera_signal

        context.pre_trim_videos = list(context.videos)
        context.audio_folder_path = audio_folder
        context.audio_signals = audio_signals
        context.audio_sample_rate = int(sample_rate)
        context.lags = find_cross_correlation_lags(
            audio_signals, context.videos, int(sample_rate)
        )
        return context


class BrightnessLagStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        threshold = context.request.brightness_ratio_threshold
        context.pre_trim_videos = list(context.videos)

        raw_lags: dict[str, float] = {}
        for video in context.videos:
            series = compute_brightness_series(video)
            event = find_first_brightness_change(series, video.fps, threshold)
            if event is None:
                raise SkellySyncError(
                    f"No brightness change detected for camera {video.camera_name}"
                )
            raw_lags[video.camera_name] = event.lag_seconds

        max_lag = max(raw_lags.values())
        context.lags = [
            LagResult(camera_name=camera_name, lag_seconds=max_lag - raw_lag)
            for camera_name, raw_lag in raw_lags.items()
        ]
        return context


def _trim_video_worker(
    video_info: VideoInfo,
    lag: LagResult,
    backend_kind: VideoBackendKind,
    output_dir: Path,
    minimum_duration: float,
) -> VideoInfo:
    """Runs in a worker process -- arguments must stay picklable.

    Only `VideoBackendKind` (a `str` enum) is passed, never a backend
    instance, and probing the result always goes through ffmpeg (KI-03).
    """
    backend = get_backend(backend_kind)
    output_path = Path(output_dir) / synced_video_filename(video_info.camera_name)

    start_seconds = lag.lag_seconds
    end_seconds = start_seconds + minimum_duration
    backend.trim(video_info.filepath, start_seconds, end_seconds, output_path)

    return _probe_with_frame_count(get_backend(VideoBackendKind.FFMPEG), output_path)


class TrimStage:
    """Trims every video to the shared window in parallel.

    Uses `ProcessPoolExecutor` + `as_completed` instead of
    `multiprocessing.Pool.starmap` so a single camera's trim failure doesn't
    hide which camera failed or block progress reporting for the others.
    """

    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        videos = context.videos
        lags_by_camera = {lag.camera_name: lag for lag in context.lags}
        output_dir = context.synchronized_folder_path

        minimum_duration = min(
            video.duration_seconds - lags_by_camera[video.camera_name].lag_seconds
            for video in videos
        )

        max_workers = max(1, min(len(videos), (os.cpu_count() or 2) - 1))

        results: list[VideoInfo] = []
        errors: list[tuple[str, BaseException]] = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_camera = {
                executor.submit(
                    _trim_video_worker,
                    video,
                    lags_by_camera[video.camera_name],
                    context.request.video_handler,
                    output_dir,
                    minimum_duration,
                ): video.camera_name
                for video in videos
            }
            for future in as_completed(future_to_camera):
                camera_name = future_to_camera[future]
                try:
                    results.append(future.result())
                    if progress_callback is not None:
                        progress_callback(camera_name, 1.0)
                except Exception as e:  # noqa: BLE001 - isolate per-camera failures
                    logger.error(
                        f"Error trimming video {camera_name}: {e}", exc_info=True
                    )
                    errors.append((camera_name, e))

        if errors:
            failed_cameras = ", ".join(camera_name for camera_name, _ in errors)
            raise SkellySyncError(
                f"Trimming failed for camera(s): {failed_cameras}"
            ) from errors[0][1]

        context.videos = sorted(results, key=lambda video: video.camera_name)
        return context


class VerifySynchronizedFramerateStage:
    """Hard-fail if the trimmed videos don't all share one exact framerate.

    Synchronized videos are only actually synchronized if every frame index
    maps to the same wall-clock time across cameras -- a framerate mismatch
    (even a tiny one introduced by a backend's re-encode) silently breaks
    that guarantee, so this is checked explicitly rather than assumed.
    """

    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        fps_by_camera = {video.camera_name: video.fps for video in context.videos}
        unique_fps_values = set(fps_by_camera.values())

        if len(unique_fps_values) > 1:
            raise SkellySyncError(
                "Synchronized videos do not share an identical framerate: "
                f"{fps_by_camera}"
            )

        context.synchronized_fps = (
            unique_fps_values.pop() if unique_fps_values else None
        )
        return context


class VerifySynchronizedFrameCountStage:
    """Hard-fail if the trimmed videos don't all have identical frame counts.

    This is the actual correctness guarantee of synchronization: if any
    camera's output has even one more or fewer frames than the others, frame
    N no longer corresponds to the same instant across cameras. Each video's
    `frame_count` was already read directly from its file during probing
    (`_probe_with_frame_count`), so this stage just compares those real,
    already-measured counts rather than re-deriving anything from duration/fps
    arithmetic.
    """

    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        frame_counts_by_camera = {
            video.camera_name: video.frame_count for video in context.videos
        }
        unique_frame_counts = set(frame_counts_by_camera.values())

        if len(unique_frame_counts) > 1:
            raise SkellySyncError(
                "Synchronized videos do not have identical frame counts: "
                f"{frame_counts_by_camera}"
            )

        context.synchronized_frame_count = (
            unique_frame_counts.pop() if unique_frame_counts else None
        )
        return context


class ReattachAudioStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        lags_by_camera = {lag.camera_name: lag for lag in context.lags}
        synced_length_seconds = (
            context.videos[0].duration_seconds if context.videos else 0.0
        )

        trimmed_audio_folder = context.audio_folder_path / TRIMMED_AUDIO_FOLDER_NAME
        trimmed_audio_paths = trim_audio_in_memory(
            context.audio_signals,
            context.audio_sample_rate,
            lags_by_camera,
            synced_length_seconds,
            trimmed_audio_folder,
        )

        for lag in context.lags:
            video_path = context.synchronized_folder_path / synced_video_filename(
                lag.camera_name
            )
            audio_path = trimmed_audio_paths[lag.camera_name]

            with tempfile.TemporaryDirectory(
                dir=str(context.synchronized_folder_path)
            ) as temp_dir:
                temp_output_path = (
                    Path(temp_dir)
                    / f"{video_path.stem}_with_audio.{VideoExtension.MP4.value}"
                )
                attach_audio(video_path, audio_path, temp_output_path)
                shutil.move(str(temp_output_path), str(video_path))

        return context


class DebugArtifactsStage:
    def run(
        self, context: PipelineContext, progress_callback: ProgressCallback | None
    ) -> PipelineContext:
        synced_folder = context.synchronized_folder_path
        artifact_paths = []

        toml_path = save_debug_toml(
            synced_folder / DEBUG_TOML_NAME,
            videos_before=context.videos_before,
            videos_after=context.videos,
            lags=context.lags,
            synchronized_fps=context.synchronized_fps,
            synchronized_frame_count=context.synchronized_frame_count,
        )
        artifact_paths.append(toml_path)

        plot_path = synced_folder / DEBUG_PLOT_NAME
        try:
            if context.request.method == SyncMethod.AUDIO:
                raw_audio_paths = sorted(
                    context.audio_folder_path.glob(f"*.{AudioExtension.WAV.value}")
                )
                trimmed_audio_paths = sorted(
                    (context.audio_folder_path / TRIMMED_AUDIO_FOLDER_NAME).glob(
                        f"*.{AudioExtension.WAV.value}"
                    )
                )
                plot_audio_waveforms(raw_audio_paths, trimmed_audio_paths, plot_path)
            else:
                # Whether debug data comes from the raw or normalized folder is
                # resolved from pipeline state, not a filesystem existence check
                # (resolves KI-10).
                source_folder = context.normalized_folder_path or Path(
                    context.request.raw_video_folder_path
                )

                before_series = {
                    video.camera_name: compute_brightness_series(video)
                    for video in context.pre_trim_videos
                }
                after_series = {
                    video.camera_name: compute_brightness_series(video)
                    for video in context.videos
                }
                for camera_name, series in before_series.items():
                    save_brightness_series(
                        series,
                        source_folder
                        / f"{camera_name}{BRIGHTNESS_SUFFIX}.{NUMPY_EXTENSION}",
                    )

                before_fps = {v.camera_name: v.fps for v in context.pre_trim_videos}
                after_fps = {v.camera_name: v.fps for v in context.videos}
                plot_brightness_series(
                    before_series, before_fps, after_series, after_fps, plot_path
                )
        except Exception:
            # Plotting is best-effort debug output, not core functionality --
            # matplotlib can fail when invoked from a thread/process other
            # than a GUI app's main thread (e.g. called from a Qt app or a
            # worker process). Don't let that discard an otherwise-successful
            # synchronization result.
            logger.warning(
                "Failed to generate debug plot at %s; continuing without it.",
                plot_path,
                exc_info=True,
            )
        else:
            artifact_paths.append(plot_path)

        context.debug_artifact_paths = artifact_paths
        return context
