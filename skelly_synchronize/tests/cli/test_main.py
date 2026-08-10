from pathlib import Path

import pytest

from skelly_synchronize.cli import main as main_module
from skelly_synchronize.cli.main import build_parser, main
from skelly_synchronize.core.models import SyncMethod, SyncResult, VideoBackendKind


def test_parser_requires_raw_video_folder_path():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--method", "audio"])


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["some_folder"])

    assert args.raw_video_folder_path == Path("some_folder")
    assert args.synchronized_video_folder_path is None
    assert args.method == "audio"
    assert args.video_handler == VideoBackendKind.DEFFCODE.value
    assert args.brightness_ratio_threshold == 1000.0
    assert args.create_debug_artifacts is True
    assert args.verbose is False


def test_parser_overrides():
    parser = build_parser()
    args = parser.parse_args(
        [
            "some_folder",
            "--method",
            "audio",
            "--output",
            "out_folder",
            "--video-handler",
            "ffmpeg",
            "--brightness-threshold",
            "500",
            "--no-debug-artifacts",
            "--verbose",
        ]
    )

    assert args.synchronized_video_folder_path == Path("out_folder")
    assert args.method == "audio"
    assert args.video_handler == "ffmpeg"
    assert args.brightness_ratio_threshold == 500.0
    assert args.create_debug_artifacts is False
    assert args.verbose is True


def test_main_rejects_missing_raw_video_folder(tmp_path, capsys):
    missing_folder = tmp_path / "does_not_exist"

    exit_code = main([str(missing_folder), "--method", "audio"])

    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


def test_main_happy_path_builds_request_and_prints_summary(
    tmp_path, capsys, monkeypatch
):
    raw_folder = tmp_path / "raw_videos"
    raw_folder.mkdir()
    synced_folder = tmp_path / "synchronized_videos"

    captured_request = {}

    def fake_run_pipeline(request, progress_callback=None):
        captured_request["request"] = request
        if progress_callback is not None:
            progress_callback("cam_1", 1.0)
        return SyncResult(
            synchronized_video_folder_path=synced_folder,
            videos_before=[],
            videos_after=[],
            lags=[],
            debug_artifact_paths=[],
            elapsed_seconds=1.5,
        )

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main([str(raw_folder), "--method", "brightness"])

    assert exit_code == 0
    request = captured_request["request"]
    assert request.raw_video_folder_path == raw_folder
    assert request.method == SyncMethod.BRIGHTNESS
    assert request.video_handler == VideoBackendKind.DEFFCODE

    out = capsys.readouterr().out
    assert str(synced_folder) in out
    assert "cam_1: trimmed" in out
