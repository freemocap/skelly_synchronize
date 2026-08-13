import logging
import shutil
import subprocess
from pathlib import Path

from skelly_synchronize.core.config import (
    FFMPEG_ENCODE_SUBPROCESS_TIMEOUT_SECONDS,
    FFMPEG_SUBPROCESS_TIMEOUT_SECONDS,
)
from skelly_synchronize.core.exceptions import BackendSubprocessError, VideoProbeError
from skelly_synchronize.core.models import VideoInfo

logger = logging.getLogger(__name__)

FFMPEG_EXECUTABLE = "ffmpeg"
FFPROBE_EXECUTABLE = "ffprobe"

# ffmpeg's accurate `-ss` seeks to the first frame whose timestamp is >= the
# target. Seeking to a target that lands exactly on (or a hair after) the
# intended frame's own timestamp is therefore ambiguous under floating-point
# rounding -- it can tip into skipping that frame and starting one frame
# late. Nudging the seek target slightly earlier removes the ambiguity
# without risking landing on the previous frame instead, since this is far
# smaller than any realistic frame duration (up to ~1000fps).
SEEK_EPSILON_SECONDS = 1e-4


def check_for_ffmpeg() -> str:
    ffmpeg_pathstring = shutil.which(FFMPEG_EXECUTABLE)
    if ffmpeg_pathstring is None:
        raise FileNotFoundError(
            "ffmpeg not found, please install ffmpeg and add it to your PATH"
        )
    return ffmpeg_pathstring


def check_for_ffprobe() -> str:
    ffprobe_pathstring = shutil.which(FFPROBE_EXECUTABLE)
    if ffprobe_pathstring is None:
        raise FileNotFoundError(
            "ffprobe not found, please install ffmpeg and add it to your PATH"
        )
    return ffprobe_pathstring


def _parse_ffmpeg_output(output: str, filepath: Path) -> float:
    cleaned_out = (
        str(output)
        .replace("b'", "")
        .replace("'", "")
        .replace("\\n", "")
        .replace("\\r", "")
        .replace("\\t", "")
        .replace("\\", "")
    )

    try:
        return float(cleaned_out)
    except (ValueError, RuntimeError):
        split_str = cleaned_out.split("/")
        if len(split_str) == 2:
            return float(int(split_str[0])) / float(split_str[1])
        raise VideoProbeError(
            f"Unable to parse ffprobe output {output!r} for video {filepath}"
        )


def _run_subprocess(
    command: list[str], timeout: float = FFMPEG_SUBPROCESS_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise BackendSubprocessError(
            f"Command timed out after {timeout}s: {' '.join(command)}",
            stderr=str(e.stderr or ""),
            returncode=None,
            timed_out=True,
        )


class FfmpegBackend:
    """`VideoBackend` implementation that shells out to the ffmpeg/ffprobe CLI."""

    def _extract_video_duration(self, filepath: Path) -> float:
        check_for_ffprobe()
        command = [
            FFPROBE_EXECUTABLE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ]
        result = _run_subprocess(command)
        if result.returncode != 0:
            raise BackendSubprocessError(
                f"Failed to extract duration for video {filepath}",
                stderr=result.stderr.decode(errors="replace"),
                returncode=result.returncode,
            )
        return _parse_ffmpeg_output(result.stdout, filepath)

    def _extract_video_fps(self, filepath: Path) -> float:
        check_for_ffprobe()
        command = [
            FFPROBE_EXECUTABLE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ]
        result = _run_subprocess(command)
        if result.returncode != 0:
            raise BackendSubprocessError(
                f"Failed to extract fps for video {filepath}",
                stderr=result.stderr.decode(errors="replace"),
                returncode=result.returncode,
            )
        return _parse_ffmpeg_output(result.stdout, filepath)

    def probe(self, filepath: Path) -> VideoInfo:
        """Probe video metadata using ffprobe.

        Probing always uses ffmpeg/ffprobe regardless of which backend is
        selected for trimming -- ffprobe is more complete/reliable for
        metadata than deffcode (resolves KI-03).
        """
        filepath = Path(filepath)
        duration_seconds = self._extract_video_duration(filepath)
        fps = self._extract_video_fps(filepath)
        return VideoInfo(
            filepath=filepath,
            video_name=filepath.stem,
            duration_seconds=duration_seconds,
            fps=fps,
        )

    def trim(
        self,
        filepath: Path,
        start_seconds: float,
        frame_count: int,
        output_path: Path,
    ) -> Path:
        check_for_ffmpeg()
        filepath = Path(filepath)
        output_path = Path(output_path)

        seek_seconds = max(0.0, start_seconds - SEEK_EPSILON_SECONDS)

        command = [
            FFMPEG_EXECUTABLE,
            "-i",
            str(filepath),
            "-ss",
            str(seek_seconds),
            "-frames:v",
            str(frame_count),
            "-y",
            str(output_path),
        ]

        result = _run_subprocess(command)
        if result.returncode != 0:
            raise BackendSubprocessError(
                f"Failed to trim video {filepath}",
                stderr=result.stderr.decode(errors="replace"),
                returncode=result.returncode,
            )
        return output_path


def extract_audio_sample_rate(filepath: Path) -> int:
    """Get the audio sample rate of a video file's audio stream via ffprobe."""
    check_for_ffprobe()
    command = [
        FFPROBE_EXECUTABLE,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(filepath),
    ]
    result = _run_subprocess(command)
    if result.returncode != 0:
        raise BackendSubprocessError(
            f"Failed to extract audio sample rate for video {filepath}",
            stderr=result.stderr.decode(errors="replace"),
            returncode=result.returncode,
        )
    if not result.stdout.strip():
        raise VideoProbeError(
            f"No audio stream found for video {filepath}, ensure video has audio"
        )
    return int(_parse_ffmpeg_output(result.stdout, filepath))


def extract_audio(filepath: Path, output_path: Path) -> Path:
    """Extract the audio track of a video file into output_path via ffmpeg."""
    check_for_ffmpeg()
    filepath = Path(filepath)
    output_path = Path(output_path)
    command = [FFMPEG_EXECUTABLE, "-y", "-i", str(filepath), str(output_path)]
    result = _run_subprocess(command, timeout=FFMPEG_ENCODE_SUBPROCESS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise BackendSubprocessError(
            f"Failed to extract audio from video {filepath}, check that video has audio",
            stderr=result.stderr.decode(errors="replace"),
            returncode=result.returncode,
        )
    return output_path


def normalize_framerate_and_sample_rate(
    filepath: Path,
    output_path: Path,
    desired_fps: float,
    desired_sample_rate: int,
) -> Path:
    """Re-encode a video to a target fps and audio sample rate via ffmpeg."""
    check_for_ffmpeg()
    filepath = Path(filepath)
    output_path = Path(output_path)
    command = [
        FFMPEG_EXECUTABLE,
        "-i",
        str(filepath),
        "-r",
        str(desired_fps),
        "-ar",
        str(desired_sample_rate),
        "-y",
        str(output_path),
    ]
    result = _run_subprocess(command, timeout=FFMPEG_ENCODE_SUBPROCESS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise BackendSubprocessError(
            f"Failed to normalize framerate/sample rate for video {filepath}",
            stderr=result.stderr.decode(errors="replace"),
            returncode=result.returncode,
        )
    return output_path


def attach_audio(video_path: Path, audio_path: Path, output_path: Path) -> Path:
    """Mux an audio file onto a video (re-encoding audio as AAC, copying video) via ffmpeg."""
    check_for_ffmpeg()
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    command = [
        FFMPEG_EXECUTABLE,
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-y",
        str(output_path),
    ]
    result = _run_subprocess(command, timeout=FFMPEG_ENCODE_SUBPROCESS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise BackendSubprocessError(
            f"Failed to attach audio {audio_path} to video {video_path}",
            stderr=result.stderr.decode(errors="replace"),
            returncode=result.returncode,
        )
    return output_path
