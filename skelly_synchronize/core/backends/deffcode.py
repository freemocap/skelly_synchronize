import json
import logging
from pathlib import Path

import cv2
from deffcode import FFdecoder, Sourcer

from skelly_synchronize.core.backends.ffmpeg import FfmpegBackend, check_for_ffmpeg
from skelly_synchronize.core.exceptions import SkellySyncError
from skelly_synchronize.core.models import VideoInfo

logger = logging.getLogger(__name__)

# deffcode/ffmpeg auto-rotation combined with OpenCV's VideoWriter can double-apply
# rotation, so orientation-tagged sources need an explicit transpose filter instead.
TRANSPOSITION_FILTERS = {
    90.0: "transpose=cclock",
    -270.0: "transpose=cclock",
    -90.0: "transpose=clock",
    270.0: "transpose=clock",
    180.0: "transpose=cclock,transpose=cclock",
    -180.0: "transpose=clock,transpose=clock",
}


class DeffcodeBackend:
    """`VideoBackend` implementation that uses deffcode for frame-accurate trimming."""

    def __init__(self) -> None:
        self._ffmpeg_backend = FfmpegBackend()

    def probe(self, filepath: Path) -> VideoInfo:
        """Probing always delegates to ffmpeg/ffprobe (resolves KI-03)."""
        return self._ffmpeg_backend.probe(filepath)

    def trim(
        self,
        filepath: Path,
        start_seconds: float,
        frame_count: int,
        output_path: Path,
    ) -> Path:
        filepath = Path(filepath)
        output_path = Path(output_path)
        video_info = self.probe(filepath)

        # `end_frame` is derived by adding the exact integer `frame_count`
        # rather than by converting an end timestamp back to a frame index --
        # the latter risks losing a frame to floating-point rounding right at
        # the boundary (the same class of bug fixed in `FfmpegBackend.trim`).
        start_frame = round(start_seconds * video_info.fps)
        end_frame = start_frame + frame_count

        _trim_frames_with_deffcode(
            input_video_path=filepath,
            start_frame=start_frame,
            end_frame=end_frame,
            output_path=output_path,
        )
        return output_path


def _get_transpose_ffparams(input_video_path: Path, ffmpeg_location: str) -> dict:
    sourcer = Sourcer(
        source=str(input_video_path), custom_ffmpeg=ffmpeg_location
    ).probe_stream()
    orientation = sourcer.retrieve_metadata()["source_video_orientation"]

    if orientation == 0:
        return {}

    logger.info("Video has reversed metadata, changing FFmpeg transpose argument")
    return {
        "-ffprefixes": ["-noautorotate"],
        "-vf": TRANSPOSITION_FILTERS[orientation],
    }


def _trim_frames_with_deffcode(
    input_video_path: Path,
    start_frame: int,
    end_frame: int,
    output_path: Path,
) -> None:
    try:
        ffmpeg_location = check_for_ffmpeg()
    except FileNotFoundError:
        ffmpeg_location = ""

    ffparams = _get_transpose_ffparams(input_video_path, ffmpeg_location)

    decoder = FFdecoder(
        str(input_video_path),
        frame_format="bgr24",
        custom_ffmpeg=ffmpeg_location,
        verbose=False,
        **ffparams,
    ).formulate()

    metadata = json.loads(decoder.metadata)
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    framerate = metadata["output_framerate"]
    framesize = tuple(metadata["output_frames_resolution"])

    video_writer = cv2.VideoWriter(str(output_path), fourcc, framerate, framesize)

    try:
        current_frame = 0
        written_frames = 0
        for frame in decoder.generateFrame():
            if frame is None:
                break

            # frames requested are always a contiguous range, so a simple
            # bounds check is O(1) per frame instead of an O(n) list scan (KI-06).
            if start_frame <= current_frame < end_frame:
                video_writer.write(frame)
                written_frames += 1

            if current_frame >= end_frame - 1:
                break

            current_frame += 1
    finally:
        decoder.terminate()
        video_writer.release()

    if written_frames == 0:
        raise SkellySyncError(
            f"No frames written when trimming {input_video_path} "
            f"(requested frames [{start_frame}, {end_frame}))"
        )
