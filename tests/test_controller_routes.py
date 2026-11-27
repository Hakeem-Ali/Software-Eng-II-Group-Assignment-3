"""Controller (router) tests: status codes and access rules for the new routes."""


from fastapi.testclient import TestClient

from app.main import app
from app.routers.errors import status_for
from app.seed import seed

# Seeded users (see app/seed.py): admin=1, graduate (DCIT)=2, graduate (other)=3,
# employer (owns listing 1)=4, other employer=5.
ADMIN, GRAD, OTHER_GRAD, EMPLOYER, OTHER_EMPLOYER = 1, 2, 3, 4, 5

client = TestClient(app)


def setup_function():
    seed(reset=True)


def apply_to_listing_1() -> int:
    r = client.post(
        "/api/graduates/applications",
        json={"listing_id": 1, "cover_letter": "hi", "actor_id": GRAD},
    )
    assert r.status_code == 201
    return r.json()["application_id"]


def submit_pending_listing() -> int:
    r = client.post(
        "/api/employer/listings",
        json={
            "title": "Tester",
            "company": "Acme",
            "description": "d",
            "apply_mode": "on-platform-collect",
            "deadline": "2099-12-31",
            "actor_id": EMPLOYER,
        },
    )
    assert r.status_code == 201
    return r.json()["listing_id"]


def test_status_for_maps_service_errors():
    cases = [
        ("listing not found", 404),
        ("application not found", 404),
        ("unknown user", 401),
        ("admin only", 403),
        ("only the listing employer may advance applications", 403),
        ("application already submitted", 409),
        ("cannot deny listing with status denied", 409),
        ("use the admin reopen operation", 422),
        ("something unexpected", 400),
        (None, 400),
    ]
    for message, expected in cases:
        assert status_for(message) == expected, message


def test_active_applications_lists_my_application():
    app_id = apply_to_listing_1()
    r = client.get("/api/graduates/applications/active", params={"actor_id": GRAD})
    assert r.status_code == 200
    assert [a["id"] for a in r.json()["applications"]] == [app_id]


def test_active_applications_graduates_only():
    r = client.get("/api/graduates/applications/active", params={"actor_id": EMPLOYER})
    assert r.status_code == 403


def test_applicant_can_read_own_application():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}", params={"actor_id": GRAD})
    assert r.status_code == 200
    assert r.json()["application"]["status"] == "submitted"


def test_listing_employer_can_read_application():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}", params={"actor_id": EMPLOYER})
    assert r.status_code == 200


def test_other_graduate_cannot_read_application():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}", params={"actor_id": OTHER_GRAD})
    assert r.status_code == 403


def test_other_employer_cannot_read_application():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}", params={"actor_id": OTHER_EMPLOYER})
    assert r.status_code == 403


def test_read_missing_application_is_404():
    r = client.get("/api/applications/999", params={"actor_id": GRAD})
    assert r.status_code == 404


def test_read_application_unknown_user_is_json_401():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}", params={"actor_id": 999})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["detail"] == "unknown user"


def test_history_records_status_change():
    app_id = apply_to_listing_1()
    empty = client.get(f"/api/applications/{app_id}/history", params={"actor_id": EMPLOYER})
    assert empty.status_code == 200
    assert empty.json()["history"] == []

    moved = client.post(
        f"/api/applications/{app_id}/transition",
        json={"action": "mark_reviewed", "actor_id": EMPLOYER},
    )
    assert moved.status_code == 200

    r = client.get(f"/api/applications/{app_id}/history", params={"actor_id": ADMIN})
    assert r.status_code == 200
    row = r.json()["history"][0]
    assert (row["from_status"], row["to_status"]) == ("submitted", "reviewed")
    assert row["actor_id"] == EMPLOYER


def test_applicant_cannot_read_history():
    app_id = apply_to_listing_1()
    r = client.get(f"/api/applications/{app_id}/history", params={"actor_id": GRAD})
    assert r.status_code == 403


def test_status_change_notifies_the_applicant():
    app_id = apply_to_listing_1()
    client.post(
        f"/api/applications/{app_id}/transition",
        json={"action": "mark_reviewed", "actor_id": EMPLOYER},
    )
    r = client.get("/api/notifications", params={"actor_id": GRAD})
    assert r.status_code == 200
    texts = [n["text"] for n in r.json()["notifications"]]
    assert any("reviewed" in t for t in texts)


def test_notifications_graduates_only():
    r = client.get("/api/notifications", params={"actor_id": EMPLOYER})
    assert r.status_code == 403


def test_employer_sees_own_listings():
    r = client.get("/api/employer/listings", params={"actor_id": EMPLOYER})
    assert r.status_code == 200
    assert all(item["employer_id"] == EMPLOYER for item in r.json()["listings"])
    assert len(r.json()["listings"]) >= 1


def test_employer_listings_employers_only():
    r = client.get("/api/employer/listings", params={"actor_id": GRAD})
    assert r.status_code == 403


def test_job_detail_returns_listing():
    r = client.get("/api/jobs/1", params={"actor_id": GRAD})
    assert r.status_code == 200
    assert r.json()["listing"]["id"] == 1


def test_job_detail_missing_listing_is_404():
    r = client.get("/api/jobs/999", params={"actor_id": GRAD})
    assert r.status_code == 404


def test_admin_can_deny_pending_listing_once():
    listing_id = submit_pending_listing()
    first = client.post(f"/api/admin/listings/{listing_id}/deny", json={"actor_id": ADMIN})
    assert first.status_code == 200
    assert first.json()["status"] == "denied"
    second = client.post(f"/api/admin/listings/{listing_id}/deny", json={"actor_id": ADMIN})
    assert second.status_code == 409


def test_deny_requires_admin():
    listing_id = submit_pending_listing()
    r = client.post(f"/api/admin/listings/{listing_id}/deny", json={"actor_id": EMPLOYER})
    assert r.status_code == 403


def test_deny_missing_listing_is_404():
    r = client.post("/api/admin/listings/999/deny", json={"actor_id": ADMIN})
    assert r.status_code == 404


def test_admin_can_unpublish_live_listing_once():
    first = client.post("/api/admin/listings/1/unpublish", json={"actor_id": ADMIN})
    assert first.status_code == 200
    assert first.json()["status"] == "unpublished"
    second = client.post("/api/admin/listings/1/unpublish", json={"actor_id": ADMIN})
    assert second.status_code == 409


def test_unpublish_requires_admin():
    r = client.post("/api/admin/listings/1/unpublish", json={"actor_id": EMPLOYER})
    assert r.status_code == 403


def test_graduate_can_unsubscribe_after_subscribing():
    assert client.post("/api/graduates/subscribe", json={"actor_id": GRAD}).status_code == 200
    r = client.post("/api/graduates/unsubscribe", json={"actor_id": GRAD})
    assert r.status_code == 200


def test_unsubscribe_without_subscription_is_404():
    client.post("/api/graduates/unsubscribe", json={"actor_id": GRAD})
    r = client.post("/api/graduates/unsubscribe", json={"actor_id": GRAD})
    assert r.status_code == 404


def test_unsubscribe_graduates_only():
    r = client.post("/api/graduates/unsubscribe", json={"actor_id": EMPLOYER})
    assert r.status_code == 403

def test_cannot_publish_a_denied_listing():
    listing_id = submit_pending_listing()
    client.post(f"/api/admin/listings/{listing_id}/deny", json={"actor_id": ADMIN})
    r = client.post(f"/api/admin/listings/{listing_id}/publish", json={"actor_id": ADMIN})
    assert r.status_code == 409
