from fastapi.testclient import TestClient

import skelly_synchronize.api.jobs as jobs_module
from skelly_synchronize.api.jobs import JobStore, get_job_store
from skelly_synchronize.api.main import app
from skelly_synchronize.core.models import SyncMethod, SyncResult


class FakeProcessRunsImmediately:
    """Runs `target` synchronously on `start()` -- avoids real multiprocessing
    so tests stay fast and so monkeypatched `run_pipeline` (patched in this
    process) is actually the code that executes."""

    def __init__(self, target, args):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        self._target(*self._args)
        self._alive = False

    def is_alive(self):
        return self._alive

    def terminate(self):
        self._alive = False

    def join(self, timeout=None):
        pass


class FakeProcessStaysAlive(FakeProcessRunsImmediately):
    """Never runs `target` -- simulates a still-running job for cancel tests."""

    def start(self):
        self._alive = True


def _sync_request(tmp_path):
    (tmp_path / "cam_a.mp4").touch()
    return {
        "raw_video_folder_path": str(tmp_path),
        "method": SyncMethod.AUDIO.value,
        "create_debug_artifacts": False,
    }


def _fake_result(tmp_path):
    return SyncResult(
        synchronized_video_folder_path=tmp_path / "synchronized_videos",
        videos_before=[],
        videos_after=[],
        lags=[],
        debug_artifact_paths=[],
        elapsed_seconds=0.1,
        synchronized_frame_count=10,
    )


def _override_job_store(monkeypatch, process_class):
    monkeypatch.setattr(jobs_module.multiprocessing, "Process", process_class)
    store = JobStore()
    app.dependency_overrides[get_job_store] = lambda: store
    return store


def test_create_and_get_job_succeeds(tmp_path, monkeypatch):
    def fake_run_pipeline(request, progress_callback=None):
        if progress_callback is not None:
            progress_callback("cam_a", 1.0)
        return _fake_result(tmp_path)

    monkeypatch.setattr(jobs_module, "run_pipeline", fake_run_pipeline)
    _override_job_store(monkeypatch, FakeProcessRunsImmediately)
    client = TestClient(app)
    try:
        create_response = client.post("/jobs", json=_sync_request(tmp_path))
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_response = client.get(f"/jobs/{job_id}")
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["status"] == "succeeded"
        assert body["progress"] == 1.0
        assert body["result"]["synchronized_frame_count"] == 10
    finally:
        app.dependency_overrides.clear()


def test_create_job_missing_folder_returns_404(tmp_path, monkeypatch):
    _override_job_store(monkeypatch, FakeProcessRunsImmediately)
    client = TestClient(app)
    try:
        request = _sync_request(tmp_path)
        request["raw_video_folder_path"] = str(tmp_path / "does_not_exist")

        response = client.post("/jobs", json=request)

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_list_jobs_includes_created_job(tmp_path, monkeypatch):
    monkeypatch.setattr(
        jobs_module,
        "run_pipeline",
        lambda request, progress_callback=None: _fake_result(tmp_path),
    )
    _override_job_store(monkeypatch, FakeProcessRunsImmediately)
    client = TestClient(app)
    try:
        create_response = client.post("/jobs", json=_sync_request(tmp_path))
        job_id = create_response.json()["job_id"]

        list_response = client.get("/jobs")

        assert list_response.status_code == 200
        assert any(job["id"] == job_id for job in list_response.json())
    finally:
        app.dependency_overrides.clear()


def test_cancel_job_marks_cancelled(tmp_path, monkeypatch):
    _override_job_store(monkeypatch, FakeProcessStaysAlive)
    client = TestClient(app)
    try:
        create_response = client.post("/jobs", json=_sync_request(tmp_path))
        job_id = create_response.json()["job_id"]

        cancel_response = client.delete(f"/jobs/{job_id}")

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


def test_get_unknown_job_returns_404(monkeypatch):
    _override_job_store(monkeypatch, FakeProcessRunsImmediately)
    client = TestClient(app)
    try:
        response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_debug_plot_missing_before_success_returns_404(tmp_path, monkeypatch):
    _override_job_store(monkeypatch, FakeProcessStaysAlive)
    client = TestClient(app)
    try:
        create_response = client.post("/jobs", json=_sync_request(tmp_path))
        job_id = create_response.json()["job_id"]

        response = client.get(f"/jobs/{job_id}/debug-plot")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
