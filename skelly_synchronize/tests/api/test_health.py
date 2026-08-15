from fastapi.testclient import TestClient

from skelly_synchronize.api.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
