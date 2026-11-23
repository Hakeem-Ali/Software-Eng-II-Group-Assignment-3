"""Shallow scenario smoke tests — intentionally weak."""

from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed


def setup_module() -> None:
    seed(reset=True)


client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["scenario"] == "job-board"


def test_api_login_seed_admin():
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-dev"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"


def test_jobs_endpoint_returns_list():
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert isinstance(r.json()["jobs"], list)
    assert len(r.json()["jobs"]) >= 1


def test_external_listing_cannot_collect_application():
    r = client.post(
        "/api/graduates/applications",
        json={
            "listing_id": 2,
            "cover_letter": "letter",
            "resume_text": "resume",
            "actor_id": 2,
        },
    )
    assert r.status_code == 409


def test_publishing_listing_twice_does_not_duplicate_notifications():
    first = client.post(
        "/api/admin/listings/1/publish",
        json={"actor_id": 1},
    )
    second = client.post(
        "/api/admin/listings/1/publish",
        json={"actor_id": 1},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["count"] == 0
