import concurrent.futures
from pathlib import Path

import numpy as np
import pytest

from skelly_synchronize.core.exceptions import SkellySyncError
from skelly_synchronize.core.models import (
    LagResult,
    SyncMethod,
    SyncRequest,
    VideoBackendKind,
    VideoInfo,
)
from skelly_synchronize.core.pipeline import stages as stages_module
from skelly_synchronize.core.pipeline.stages import (
    BrightnessLagStage,
    NormalizeFramerateStage,
    PipelineContext,
    SetupOutputFolderStage,
    TrimStage,
    VerifySynchronizedFrameCountStage,
    VerifySynchronizedFramerateStage,
    _probe_with_frame_count,
    _trim_video_worker,
)


def _make_video_info(
    video_name: str,
    fps: float = 30.0,
    duration_seconds: float = 10.0,
    frame_count: int | None = None,
):
    return VideoInfo(
        filepath=Path(f"{video_name}.mp4"),
        video_name=video_name,
        duration_seconds=duration_seconds,
        fps=fps,
        frame_count=frame_count,
    )


def _make_request(
    tmp_path: Path, method: SyncMethod = SyncMethod.BRIGHTNESS
) -> SyncRequest:
    raw_folder = tmp_path / "raw_videos"
    raw_folder.mkdir()
    return SyncRequest(raw_video_folder_path=raw_folder, method=method)


def test_setup_output_folder_stage_creates_default_folder(tmp_path):
    request = _make_request(tmp_path)
    context = PipelineContext(request=request)

    SetupOutputFolderStage().run(context, None)

    assert (
        context.synchronized_folder_path
        == request.raw_video_folder_path.parent / "synchronized_videos"
    )
    assert context.synchronized_folder_path.is_dir()


def test_normalize_framerate_stage_skips_when_fps_uniform(tmp_path):
    request = _make_request(tmp_path)
    videos = [_make_video_info("cam_a", fps=30.0), _make_video_info("cam_b", fps=30.0)]
    context = PipelineContext(request=request, videos=videos)

    result = NormalizeFramerateStage().run(context, None)

    assert result.normalized_folder_path is None
    assert result.videos == videos


class _FakeBrightnessEvent:
    def __init__(self, lag_seconds: float):
        self.lag_seconds = lag_seconds


def test_brightness_lag_stage_normalizes_lags(monkeypatch, tmp_path):
    request = _make_request(tmp_path, method=SyncMethod.BRIGHTNESS)
    videos = [_make_video_info("cam_a", fps=10.0), _make_video_info("cam_b", fps=10.0)]
    context = PipelineContext(request=request, videos=videos)

    raw_lag_seconds = {"cam_a": 1.0, "cam_b": 3.0}

    # encode the video's raw lag in the "series" so the fake event-finder
    # can decode it back out, without needing to track call order.
    monkeypatch.setattr(
        stages_module,
        "compute_brightness_series",
        lambda video: np.array([raw_lag_seconds[video.video_name]]),
    )
    monkeypatch.setattr(
        stages_module,
        "find_first_brightness_change",
        lambda series, fps, threshold: _FakeBrightnessEvent(
            lag_seconds=float(series[0])
        ),
    )

    lags = BrightnessLagStage().run(context, None).lags
    lag_by_video = {lag.video_name: lag.lag_seconds for lag in lags}

    max_lag = max(raw_lag_seconds.values())
    assert min(lag_by_video.values()) == 0.0
    assert lag_by_video["cam_a"] == max_lag - raw_lag_seconds["cam_a"]
    assert lag_by_video["cam_b"] == max_lag - raw_lag_seconds["cam_b"]


def test_brightness_lag_stage_raises_when_no_event_detected(monkeypatch, tmp_path):
    request = _make_request(tmp_path, method=SyncMethod.BRIGHTNESS)
    videos = [_make_video_info("cam_a")]
    context = PipelineContext(request=request, videos=videos)

    monkeypatch.setattr(
        stages_module, "compute_brightness_series", lambda video: np.zeros(5)
    )
    monkeypatch.setattr(
        stages_module,
        "find_first_brightness_change",
        lambda series, fps, threshold: None,
    )

    with pytest.raises(SkellySyncError):
        BrightnessLagStage().run(context, None)


class FakeBackend:
    def __init__(self, should_fail_for: set[str] | None = None):
        self.should_fail_for = should_fail_for or set()

    def trim(self, filepath, start_seconds, end_seconds, output_path):
        video_name = Path(filepath).stem
        if video_name in self.should_fail_for:
            raise RuntimeError(f"boom for {video_name}")
        Path(output_path).touch()

    def probe(self, filepath):
        return _make_video_info(Path(filepath).stem, duration_seconds=5.0)


def test_trim_video_worker_uses_ffmpeg_backend_for_final_probe(monkeypatch, tmp_path):
    fake_backend = FakeBackend()
    monkeypatch.setattr(stages_module, "get_backend", lambda kind: fake_backend)

    video_info = _make_video_info("raw_cam_a", duration_seconds=10.0)
    lag = LagResult(video_name="raw_cam_a", lag_seconds=1.0)

    result = _trim_video_worker(
        video_info, lag, VideoBackendKind.FFMPEG, tmp_path, minimum_duration=5.0
    )

    assert result.video_name == "synced_cam_a"


def test_trim_stage_isolates_per_video_errors(monkeypatch, tmp_path):
    # Run the pool in-thread (not in a subprocess) so the monkeypatched
    # backend factory is visible to "worker" code during the test.
    monkeypatch.setattr(
        stages_module, "ProcessPoolExecutor", concurrent.futures.ThreadPoolExecutor
    )

    fake_backend = FakeBackend(should_fail_for={"cam_b"})
    monkeypatch.setattr(stages_module, "get_backend", lambda kind: fake_backend)

    request = _make_request(tmp_path, method=SyncMethod.BRIGHTNESS)
    output_dir = tmp_path / "synchronized_videos"
    output_dir.mkdir()

    videos = [
        _make_video_info("cam_a", duration_seconds=10.0),
        _make_video_info("cam_b", duration_seconds=10.0),
    ]
    lags = [
        LagResult(video_name="cam_a", lag_seconds=0.0),
        LagResult(video_name="cam_b", lag_seconds=0.0),
    ]
    context = PipelineContext(
        request=request, videos=videos, lags=lags, synchronized_folder_path=output_dir
    )

    with pytest.raises(SkellySyncError, match="cam_b"):
        TrimStage().run(context, None)


def test_trim_stage_succeeds_when_all_videos_trim_cleanly(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stages_module, "ProcessPoolExecutor", concurrent.futures.ThreadPoolExecutor
    )

    fake_backend = FakeBackend()
    monkeypatch.setattr(stages_module, "get_backend", lambda kind: fake_backend)

    request = _make_request(tmp_path, method=SyncMethod.BRIGHTNESS)
    output_dir = tmp_path / "synchronized_videos"
    output_dir.mkdir()

    videos = [
        _make_video_info("cam_a", duration_seconds=10.0),
        _make_video_info("cam_b", duration_seconds=10.0),
    ]
    lags = [
        LagResult(video_name="cam_a", lag_seconds=0.0),
        LagResult(video_name="cam_b", lag_seconds=1.0),
    ]
    context = PipelineContext(
        request=request, videos=videos, lags=lags, synchronized_folder_path=output_dir
    )

    result = TrimStage().run(context, None)

    assert {video.video_name for video in result.videos} == {
        "synced_cam_a",
        "synced_cam_b",
    }


def test_verify_synchronized_framerate_stage_passes_when_fps_matches(tmp_path):
    request = _make_request(tmp_path)
    videos = [
        _make_video_info("synced_cam_a", fps=29.97),
        _make_video_info("synced_cam_b", fps=29.97),
    ]
    context = PipelineContext(request=request, videos=videos)

    result = VerifySynchronizedFramerateStage().run(context, None)

    assert result.synchronized_fps == 29.97


def test_verify_synchronized_framerate_stage_raises_on_any_mismatch(tmp_path):
    # this is the core correctness guarantee of synchronization: even a tiny
    # fps discrepancy between videos (e.g. from a lossy backend re-encode)
    # must fail loudly instead of silently producing misaligned output.
    videos = [
        _make_video_info("synced_cam_a", fps=29.97),
        _make_video_info("synced_cam_b", fps=29.970000001),
    ]
    context = PipelineContext(
        request=_make_request(tmp_path),
        videos=videos,
    )

    with pytest.raises(SkellySyncError, match="framerate"):
        VerifySynchronizedFramerateStage().run(context, None)


def test_probe_with_frame_count_attaches_real_frame_count(monkeypatch, tmp_path):
    class FakeCaptureBackend:
        def probe(self, filepath):
            return _make_video_info(Path(filepath).stem)

    monkeypatch.setattr(stages_module, "_count_video_frames", lambda filepath: 872)

    video_info = _probe_with_frame_count(FakeCaptureBackend(), tmp_path / "cam_a.mp4")

    assert video_info.frame_count == 872


def test_verify_synchronized_frame_count_stage_passes_when_counts_match(tmp_path):
    request = _make_request(tmp_path)
    videos = [
        _make_video_info("synced_cam_a", frame_count=300),
        _make_video_info("synced_cam_b", frame_count=300),
    ]
    context = PipelineContext(request=request, videos=videos)

    result = VerifySynchronizedFrameCountStage().run(context, None)

    assert result.synchronized_frame_count == 300


def test_verify_synchronized_frame_count_stage_raises_on_any_mismatch(tmp_path):
    # this is the actual correctness guarantee of synchronization: matching
    # fps doesn't help if one video's output is a frame longer or shorter.
    request = _make_request(tmp_path)
    videos = [
        _make_video_info("synced_cam_a", frame_count=300),
        _make_video_info("synced_cam_b", frame_count=299),
    ]
    context = PipelineContext(request=request, videos=videos)

    with pytest.raises(SkellySyncError, match="frame count"):
        VerifySynchronizedFrameCountStage().run(context, None)
