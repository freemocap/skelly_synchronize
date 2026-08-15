from skelly_synchronize.core.config import synced_video_filename


def test_synced_video_filename_strips_raw_prefix():
    assert synced_video_filename("raw_cam_1") == "synced_cam_1.mp4"


def test_synced_video_filename_without_raw_prefix():
    assert synced_video_filename("cam_1") == "synced_cam_1.mp4"
