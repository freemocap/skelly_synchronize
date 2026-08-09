class SkellySyncError(Exception):
    """Base class for all errors raised by skelly_synchronize.core."""


class VideoProbeError(SkellySyncError):
    """Raised when video metadata (duration, fps, ...) cannot be determined."""


class BackendSubprocessError(SkellySyncError):
    """Raised when an ffmpeg/ffprobe subprocess invocation fails or times out."""

    def __init__(
        self,
        message: str,
        stderr: str = "",
        returncode: int | None = None,
        timed_out: bool = False,
    ) -> None:
        super().__init__(message, stderr, returncode, timed_out)
        self.stderr = stderr
        self.returncode = returncode
        self.timed_out = timed_out
