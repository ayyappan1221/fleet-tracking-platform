"""Health check test — Wave 1 GREEN contract."""

from tests.test_api import client  # noqa: F401 — pytest fixture import


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
