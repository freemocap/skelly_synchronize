import argparse
import logging
import sys
from pathlib import Path

from skelly_synchronize import __version__
from skelly_synchronize.core.exceptions import SkellySyncError
from skelly_synchronize.core.logging_setup import configure_logging
from skelly_synchronize.core.models import SyncMethod, SyncRequest, VideoBackendKind
from skelly_synchronize.core.pipeline.runner import run_pipeline

_METHOD_CHOICES = {
    "audio": SyncMethod.AUDIO,
    "brightness": SyncMethod.BRIGHTNESS,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skelly-synchronize",
        description=(
            "Synchronize multi-camera video recordings post-recording, "
            "without needing timestamps."
        ),
    )
    parser.add_argument(
        "raw_video_folder_path",
        type=Path,
        help="Folder containing the raw video files to synchronize.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="synchronized_video_folder_path",
        type=Path,
        default=None,
        help=(
            "Folder to write synchronized videos to. Defaults to a "
            "'synchronized_videos' folder next to the raw video folder."
        ),
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=sorted(_METHOD_CHOICES),
        default="audio",
        help="Synchronization strategy to use (default: %(default)s).",
    )
    parser.add_argument(
        "--video-handler",
        choices=[kind.value for kind in VideoBackendKind],
        default=VideoBackendKind.DEFFCODE.value,
        help="Backend used to trim videos (default: %(default)s).",
    )
    parser.add_argument(
        "--brightness-threshold",
        dest="brightness_ratio_threshold",
        type=float,
        default=1000.0,
        help=(
            "Brightness ratio threshold used to detect the sync event "
            "(only used with --method brightness; default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--no-debug-artifacts",
        dest="create_debug_artifacts",
        action="store_false",
        default=True,
        help="Skip writing synchronization_debug.toml and debug_plot.png.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    if not args.raw_video_folder_path.is_dir():
        print(
            f"Error: raw video folder does not exist or is not a directory: "
            f"{args.raw_video_folder_path}",
            file=sys.stderr,
        )
        return 1

    request = SyncRequest(
        raw_video_folder_path=args.raw_video_folder_path,
        synchronized_video_folder_path=args.synchronized_video_folder_path,
        method=_METHOD_CHOICES[args.method],
        video_handler=VideoBackendKind(args.video_handler),
        brightness_ratio_threshold=args.brightness_ratio_threshold,
        create_debug_artifacts=args.create_debug_artifacts,
    )

    def progress_callback(video_name: str, progress: float) -> None:
        if progress >= 1.0:
            print(f"  {video_name}: trimmed")

    try:
        result = run_pipeline(request, progress_callback)
    except SkellySyncError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Synchronized videos written to: {result.synchronized_video_folder_path}")
    print(f"Elapsed: {result.elapsed_seconds:.2f}s")
    print(f"Synchronized frame count: {result.synchronized_frame_count}")
    print("Lags:")
    for lag in result.lags:
        print(f"  {lag.video_name}: {lag.lag_seconds:.4f}s")
    print(f"Final video length: {result.synchronized_frame_count} frames")
    if result.debug_artifact_paths:
        print("Debug artifacts:")
        for artifact_path in result.debug_artifact_paths:
            print(f"  {artifact_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
