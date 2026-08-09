import subprocess
from pathlib import Path

import pytest

from skelly_synchronize.core.backends.ffmpeg import FfmpegBackend
from skelly_synchronize.core.exceptions import BackendSubprocessError


class FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setattr(
        "skelly_synchronize.core.backends.ffmpeg.shutil.which",
        lambda _: "/usr/bin/ffprobe",
    )
    return FfmpegBackend()


def test_probe_parses_duration_and_fps(monkeypatch, backend):
    responses = iter(
        [
            FakeCompletedProcess(returncode=0, stdout=b"12.5"),
            FakeCompletedProcess(returncode=0, stdout=b"30/1"),
        ]
    )
    monkeypatch.setattr(
        "skelly_synchronize.core.backends.ffmpeg.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )

    video_info = backend.probe(Path("some_video.mp4"))

    assert video_info.camera_name == "some_video"
    assert video_info.duration_seconds == 12.5
    assert video_info.fps == 30.0


def test_probe_raises_backend_subprocess_error_on_failure(monkeypatch, backend):
    monkeypatch.setattr(
        "skelly_synchronize.core.backends.ffmpeg.subprocess.run",
        lambda *args, **kwargs: FakeCompletedProcess(
            returncode=1, stderr=b"no such file"
        ),
    )

    with pytest.raises(BackendSubprocessError) as exc_info:
        backend.probe(Path("missing_video.mp4"))

    assert exc_info.value.stderr == "no such file"
    assert exc_info.value.returncode == 1


def test_run_subprocess_raises_on_timeout(monkeypatch, backend):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=30)

    monkeypatch.setattr(
        "skelly_synchronize.core.backends.ffmpeg.subprocess.run", raise_timeout
    )

    with pytest.raises(BackendSubprocessError) as exc_info:
        backend.probe(Path("slow_video.mp4"))

    assert exc_info.value.timed_out is True
