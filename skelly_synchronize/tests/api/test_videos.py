from fastapi.testclient import TestClient

from skelly_synchronize.api.main import app

client = TestClient(app)


def test_list_videos_returns_discovered_video_stems(tmp_path):
    (tmp_path / "cam_a.mp4").touch()
    (tmp_path / "cam_b.mov").touch()
    (tmp_path / "notes.txt").touch()

    response = client.get("/videos", params={"folder_path": str(tmp_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["folder_path"] == str(tmp_path)
    video_names = sorted(video["video_name"] for video in body["videos"])
    assert video_names == ["cam_a", "cam_b"]


def test_list_videos_missing_folder_returns_404(tmp_path):
    missing_folder = tmp_path / "does_not_exist"

    response = client.get("/videos", params={"folder_path": str(missing_folder)})

    assert response.status_code == 404
