from pathlib import Path
from typing import Protocol

from skelly_synchronize.core.models import VideoBackendKind, VideoInfo


class VideoBackend(Protocol):
    def probe(self, filepath: Path) -> VideoInfo: ...

    def trim(
        self,
        filepath: Path,
        start_seconds: float,
        end_seconds: float | None,
        output_path: Path,
    ) -> Path: ...


def get_backend(kind: VideoBackendKind) -> VideoBackend:
    """Construct a `VideoBackend` for the given kind.

    Only `VideoBackendKind` (a picklable `str` enum) should ever be passed
    into multiprocessing worker processes -- never a backend instance.
    """
    if kind == VideoBackendKind.FFMPEG:
        from skelly_synchronize.core.backends.ffmpeg import FfmpegBackend

        return FfmpegBackend()
    if kind == VideoBackendKind.DEFFCODE:
        from skelly_synchronize.core.backends.deffcode import DeffcodeBackend

        return DeffcodeBackend()
    raise ValueError(f"Unknown video backend kind: {kind}")
