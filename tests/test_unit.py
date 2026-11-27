from types import SimpleNamespace
from unittest.mock import Mock

import jwt

from app.services.auth_service import AuthService
from app.utilities.security import encrypt_password, verify_password
import pytest

from app.models.application import (
    Application,
    ApplicationAction,
    ApplicationStatus,
    IllegalTransitionError,
)
from app.models.listing import ApplyMode, Listing, ListingStatus
from app.models.user import User
from app.repositories.listing import ListingRepository
from app.services.listings import ListingService
from app.services.lifecycle import ListingOwnerPolicy


@pytest.mark.parametrize(
    "status",
    [ListingStatus.DENIED, ListingStatus.UNPUBLISHED],
)
def test_publish_listing_returns_error_for_non_pending_listing(status):
    listing = Listing(
        employer_id=2,
        title="Junior Developer",
        company="Test Company",
        description="Test listing",
        apply_mode=ApplyMode.ON_PLATFORM_COLLECT,
        deadline="2099-12-31",
        status=status,
    )
    users = Mock()
    users.get_by_id.return_value = SimpleNamespace(role="admin")
    listings = Mock()
    listings.get.return_value = listing
    service = ListingService(
        listings=listings,
        subscriptions=Mock(),
        notifications=Mock(),
        users=users,
        unit_of_work=Mock(),
    )

    result = service.publish_listing(admin_id=1, listing_id=3)

    assert result == {
        "ok": False,
        "error": f"cannot publish listing with status {status}",
    }
    listings.save.assert_not_called()


def test_password_hash_round_trip_and_rejects_wrong_password():
    password_hash = encrypt_password("correct horse")

    assert password_hash != "correct horse"
    assert verify_password("correct horse", password_hash)
    assert not verify_password("wrong horse", password_hash)


def test_authenticate_user_returns_token_for_valid_credentials(monkeypatch):
    user = SimpleNamespace(
        id=7,
        username="alice",
        password=encrypt_password("secret"),
        role="regular_user",
    )

    class FakeUserRepository:
        def get_by_username(self, username):
            return user if username == "alice" else None

    monkeypatch.setattr(
        "app.services.auth_service.create_access_token",
        lambda data: {"sub": data["sub"], "role": data["role"]},
    )

    token = AuthService(FakeUserRepository()).authenticate_user("alice", "secret")

    assert token == {"sub": "7", "role": "regular_user"}


def test_authenticate_user_returns_none_for_invalid_credentials():
    user = SimpleNamespace(
        id=7,
        username="alice",
        password=encrypt_password("secret"),
        role="regular_user",
    )

    class FakeUserRepository:
        def get_by_username(self, username):
            return user if username == "alice" else None

    service = AuthService(FakeUserRepository())

    assert service.authenticate_user("alice", "incorrect") is None
    assert service.authenticate_user("missing", "secret") is None


def test_access_token_contains_subject_and_role():
    from app.config import get_settings
    from app.utilities.security import create_access_token

    token = create_access_token({"sub": "7", "role": "admin"})
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == "7"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_application_legal_transition_chain():
    application = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="submitted",
    )

    assert application.apply("mark_reviewed") is ApplicationStatus.REVIEWED
    assert application.current_state().allowed_actions() == frozenset(
        {ApplicationAction.SHORTLIST, ApplicationAction.REJECT}
    )
    assert application.apply("shortlist") == "shortlisted"
    assert application.apply("reject") == "rejected"
    assert not application.is_active()


def test_application_illegal_jumps_and_terminal_states_fail():
    application = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="submitted",
    )

    with pytest.raises(IllegalTransitionError):
        application.apply("shortlist")
    with pytest.raises(IllegalTransitionError):
        application.apply("hire")

    application.status = ApplicationStatus.HIRED
    with pytest.raises(IllegalTransitionError):
        application.apply("reject")


def test_reviewed_application_can_be_rejected_but_not_hired():
    application = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="reviewed",
    )

    assert application.apply("reject") == "rejected"
    application.status = "reviewed"
    with pytest.raises(IllegalTransitionError):
        application.apply("hire")


def test_admin_reopen_only_goes_from_rejected_to_reviewed():
    rejected = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="rejected",
    )
    assert rejected.apply("reopen") == "reviewed"

    hired = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="hired",
    )
    with pytest.raises(IllegalTransitionError):
        hired.apply("reopen")


def test_password_is_never_in_user_serialization():
    user = User(
        username="alice",
        email="alice@example.com",
        password=encrypt_password("secret"),
        role="graduate",
        programme="DCIT",
    )

    assert "secret" not in repr(user)
    assert "password" not in user.model_dump()


def test_only_listing_owner_can_advance_or_read_applications():
    listing = SimpleNamespace(employer_id=11)

    assert ListingOwnerPolicy.can_advance(
        {"id": 11, "role": "employer"}, listing
    )
    assert not ListingOwnerPolicy.can_advance(
        {"id": 12, "role": "employer"}, listing
    )
    assert not ListingOwnerPolicy.can_advance(
        {"id": 11, "role": "admin"}, listing
    )


def test_only_dcit_graduates_are_eligible():
    dcit = User(
        username="dcit",
        email="dcit@example.com",
        password=encrypt_password("secret"),
        role="graduate",
        programme="DCIT",
    )
    other = User(
        username="other",
        email="other@example.com",
        password=encrypt_password("secret"),
        role="graduate",
        programme="OTHER",
    )

    assert dcit.is_eligible_graduate()
    assert not other.is_eligible_graduate()


def test_entity_enum_fields_reject_stringly_typed_values():
    application = Application(
        listing_id=1,
        graduate_id=2,
        cover_letter="letter",
        resume_text="resume",
        status="submitted",
    )
    listing = Listing(
        employer_id=1,
        title="Job",
        company="Company",
        description="Description",
        apply_mode="on-platform-collect",
        deadline="2099-12-31",
        status="pending",
    )

    assert isinstance(application.status, ApplicationStatus)
    assert listing.apply_mode.value == "on-platform-collect"
    assert listing.status.value == "pending"


def test_listing_repository_returns_all_listings_for_employer(test_session):
    test_session.add_all(
        [
            Listing(
                employer_id=12,
                title="First",
                company="Company",
                description="First listing",
                apply_mode="on-platform-collect",
                deadline="2099-12-31",
            ),
            Listing(
                employer_id=12,
                title="Second",
                company="Company",
                description="Second listing",
                apply_mode="external-link",
                external_url="https://example.com/apply",
                deadline="2099-12-31",
            ),
            Listing(
                employer_id=34,
                title="Other employer",
                company="Other",
                description="Not owned by employer 12",
                apply_mode="on-platform-collect",
                deadline="2099-12-31",
            ),
        ]
    )
    test_session.commit()

    listings = ListingRepository(test_session).for_employer(12)

    assert [listing.title for listing in listings] == ["First", "Second"]
