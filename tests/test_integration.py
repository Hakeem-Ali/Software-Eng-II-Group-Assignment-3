import jwt
from sqlmodel import select

from app.config import get_settings
from app.models.listing import ApplyMode, Listing, ListingStatus
from app.models.notification import Notification, NotificationChannel
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.listing import ListingRepository
from app.repositories.notification import NotificationRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.unit_of_work import SqlModelUnitOfWork
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.board_auth import BoardAuthService
from app.services.listings import ListingService
from app.services.notifications import NotificationService
from app.services.user_service import UserService
from app.utilities.security import encrypt_password, verify_password


def _create_user(session, username, role, programme=None):
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password("secret"),
        role=role,
        programme=programme,
    )
    session.add(user)
    session.flush()
    return user


def _create_listing(
    session,
    employer_id,
    title,
    *,
    status=ListingStatus.PENDING,
    apply_mode=ApplyMode.ON_PLATFORM_COLLECT,
    deadline="2099-12-31",
    external_url=None,
):
    listing = Listing(
        employer_id=employer_id,
        title=title,
        company="Test Company",
        description=f"{title} description",
        apply_mode=apply_mode,
        external_url=external_url,
        deadline=deadline,
        status=status,
    )
    session.add(listing)
    session.flush()
    return listing


def _listing_service(session):
    return ListingService(
        listings=ListingRepository(session),
        subscriptions=SubscriptionRepository(session),
        notifications=NotificationRepository(session),
        users=UserRepository(session),
        unit_of_work=SqlModelUnitOfWork(session),
    )


def test_save_password(test_session):
    repository = UserRepository(test_session)
    service = AuthService(repository)

    created = service.register_user("alice", "alice@example.com", "secret")
    saved = repository.get_by_username("alice")

    assert saved is not None
    assert created.id == saved.id
    assert saved.username == "alice"
    assert saved.email == "alice@example.com"
    assert saved.role == "regular_user"
    assert saved.password != "secret"
    assert verify_password("secret", saved.password)


def test_login(test_session):
    repository = UserRepository(test_session)
    service = AuthService(repository)
    service.register_user("alice", "alice@example.com", "secret")

    token = service.authenticate_user("alice", "secret")
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(repository.get_by_username("alice").id)
    assert payload["role"] == "regular_user"


def test_register_user(test_session):
    repository = UserRepository(test_session)
    auth_service = AuthService(repository)
    auth_service.register_user("alice", "alice@example.com", "secret")

    users = UserService(repository).get_all_users()

    assert len(users) == 1
    assert users[0].username == "alice"
    assert users[0].email == "alice@example.com"


def test_listing_subscriptions_enforce_eligibility_and_are_idempotent(
    test_session,
):
    graduate = _create_user(test_session, "dcit", "graduate", "DCIT")
    other_graduate = _create_user(test_session, "other", "graduate", "Other")
    employer = _create_user(test_session, "employer", "employer")
    service = _listing_service(test_session)

    assert service.subscribe(graduate.id) == {"ok": True}
    assert service.subscribe(graduate.id) == {"ok": True}
    assert service.subscribe(other_graduate.id) == {
        "ok": False,
        "error": "only DCIT graduates may subscribe",
    }
    assert service.subscribe(employer.id) == {
        "ok": False,
        "error": "graduates only",
    }
    assert service.subscribe(9999) == {"ok": False, "error": "graduates only"}
    assert len(test_session.exec(select(Subscription)).all()) == 1

    assert service.unsubscribe(graduate.id) == {"ok": True}
    assert service.unsubscribe(graduate.id) == {
        "ok": False,
        "error": "subscription not found",
    }
    assert service.unsubscribe(employer.id) == {
        "ok": False,
        "error": "graduates only",
    }
    assert service.unsubscribe(9999) == {
        "ok": False,
        "error": "user not found",
    }


def test_listing_service_visibility_employer_access_and_job_detail(test_session):
    employer = _create_user(test_session, "employer", "employer")
    other_employer = _create_user(test_session, "other_employer", "employer")
    graduate = _create_user(test_session, "graduate", "graduate", "DCIT")
    published = _create_listing(
        test_session,
        employer.id,
        "Published",
        status=ListingStatus.PUBLISHED,
    )
    expired = _create_listing(
        test_session,
        employer.id,
        "Expired",
        status=ListingStatus.PUBLISHED,
        deadline="2000-01-01",
    )
    pending = _create_listing(test_session, employer.id, "Pending")
    _create_listing(
        test_session,
        other_employer.id,
        "Other employer",
        status=ListingStatus.PUBLISHED,
    )
    service = _listing_service(test_session)

    assert [row["title"] for row in service.list_jobs_for_graduates()] == [
        "Published",
        "Other employer",
    ]
    assert [row["title"] for row in service.list_pending_for_admin()] == [
        "Pending",
    ]
    employer_result = service.employer_listings(employer.id)
    assert employer_result["ok"] is True
    assert [row["title"] for row in employer_result["listings"]] == [
        "Published",
        "Expired",
        "Pending",
    ]
    assert service.employer_listings(graduate.id) == {
        "ok": False,
        "error": "employers only",
    }
    assert service.get_job(graduate.id, published.id)["ok"] is True
    assert service.get_job(graduate.id, expired.id) == {
        "ok": False,
        "error": "listing not found",
    }
    assert service.get_job(graduate.id, pending.id) == {
        "ok": False,
        "error": "listing not found",
    }
    assert service.get_job(graduate.id, 9999) == {
        "ok": False,
        "error": "listing not found",
    }
    assert service.get_job(9999, published.id) == {
        "ok": False,
        "error": "unknown user",
    }


def test_listing_submission_validates_apply_modes_and_pending_state(test_session):
    employer = _create_user(test_session, "employer", "employer")
    graduate = _create_user(test_session, "graduate", "graduate", "DCIT")
    service = _listing_service(test_session)

    internal = service.submit_listing(
        employer.id,
        "Internal",
        "Test Company",
        "Internal application",
        ApplyMode.ON_PLATFORM_COLLECT.value,
        "2099-12-31",
        external_url="https://example.com/ignored",
    )
    external_missing_url = service.submit_listing(
        employer.id,
        "External missing URL",
        "Test Company",
        "External application",
        ApplyMode.EXTERNAL_LINK.value,
        "2099-12-31",
    )
    external = service.submit_listing(
        employer.id,
        "External",
        "Test Company",
        "External application",
        ApplyMode.EXTERNAL_LINK.value,
        "2099-12-31",
        external_url="https://example.com/apply",
    )
    invalid_mode = service.submit_listing(
        employer.id,
        "Invalid",
        "Test Company",
        "Invalid application",
        "unsupported",
        "2099-12-31",
    )
    unauthorized = service.submit_listing(
        graduate.id,
        "Unauthorized",
        "Test Company",
        "Unauthorized submission",
        ApplyMode.ON_PLATFORM_COLLECT.value,
        "2099-12-31",
    )

    assert internal["ok"] is True
    assert external["ok"] is True
    assert service.listings.get(internal["listing_id"]).status == ListingStatus.PENDING
    assert service.listings.get(internal["listing_id"]).external_url is None
    assert service.listings.get(external["listing_id"]).external_url == "https://example.com/apply"
    assert external_missing_url == {
        "ok": False,
        "error": "external_url required",
    }
    assert invalid_mode == {
        "ok": False,
        "error": "apply_mode must be external-link|on-platform-collect",
    }
    assert unauthorized == {"ok": False, "error": "employers only"}


def test_listing_moderation_and_notifications_use_eligible_subscribers(
    test_session,
):
    admin = _create_user(test_session, "admin", "admin")
    employer = _create_user(test_session, "employer", "employer")
    graduate = _create_user(test_session, "dcit", "graduate", "DCIT")
    other_graduate = _create_user(test_session, "other", "graduate", "Other")
    service = _listing_service(test_session)
    assert service.subscribe(graduate.id) == {"ok": True}
    assert service.subscribe(other_graduate.id)["ok"] is False

    internal = _create_listing(test_session, employer.id, "Internal")
    external = _create_listing(
        test_session,
        employer.id,
        "External",
        apply_mode=ApplyMode.EXTERNAL_LINK,
        external_url="https://example.com/apply",
    )
    denied = _create_listing(test_session, employer.id, "Denied")

    published = service.publish_listing(admin.id, internal.id)
    assert published == {"ok": True, "notified": 1, "count": 1}
    assert service.publish_listing(admin.id, internal.id) == {
        "ok": True,
        "notified": 0,
        "count": 0,
    }
    subscriber_notifications = NotificationRepository(
        test_session
    ).list_for_user(graduate.id)
    assert len(subscriber_notifications) == 1
    assert subscriber_notifications[0].listing_id == internal.id
    assert NotificationRepository(test_session).list_for_user(
        other_graduate.id
    ) == []

    assert service.publish_listing(admin.id, external.id) == {
        "ok": True,
        "notified": 0,
        "count": 0,
    }
    assert service.notify_subscribers(admin.id, external.id) == {
        "ok": True,
        "count": 0,
    }
    assert service.deny_listing(admin.id, denied.id) == {
        "ok": True,
        "listing_id": denied.id,
        "status": "denied",
    }
    assert service.deny_listing(admin.id, internal.id) == {
        "ok": False,
        "error": "cannot deny listing with status published",
    }
    assert service.unpublish_listing(admin.id, internal.id) == {
        "ok": True,
        "listing_id": internal.id,
        "status": "unpublished",
    }
    assert service.unpublish_listing(admin.id, denied.id) == {
        "ok": False,
        "error": "cannot unpublish listing with status denied",
    }
    assert service.deny_listing(employer.id, denied.id) == {
        "ok": False,
        "error": "admin only",
    }
    assert service.unpublish_listing(employer.id, internal.id) == {
        "ok": False,
        "error": "admin only",
    }
    assert service.notify_subscribers(employer.id, external.id) == {
        "ok": False,
        "error": "admin only",
    }
    assert service.notify_subscribers(admin.id, internal.id) == {
        "ok": False,
        "error": "listing not found or unpublished",
    }
    assert service.publish_listing(employer.id, denied.id) == {
        "ok": False,
        "error": "admin only",
    }


def test_notification_service_lists_only_graduate_notifications(test_session):
    graduate = _create_user(test_session, "graduate", "graduate", "DCIT")
    employer = _create_user(test_session, "employer", "employer")
    notification = Notification(
        user_id=graduate.id,
        text="Application reviewed",
        channel=NotificationChannel.EMAIL,
    )
    test_session.add(notification)
    test_session.commit()
    service = NotificationService(
        notifications=NotificationRepository(test_session),
        users=UserRepository(test_session),
    )

    result = service.list_notifications(graduate.id)

    assert result == {
        "ok": True,
        "notifications": [notification.model_dump()],
    }
    assert service.list_notifications(employer.id) == {
        "ok": False,
        "error": "graduates only",
    }
    assert service.list_notifications(9999) == {
        "ok": False,
        "error": "unknown user",
    }


def test_board_auth_service_verifies_credentials_and_returns_public_user(
    test_session,
):
    user = _create_user(test_session, "graduate", "graduate", "DCIT")
    test_session.commit()
    service = BoardAuthService(UserRepository(test_session))

    result = service.login(user.email, "secret")
    public = service.get_user(user.id)

    assert result is not None
    assert result["username"] == user.username
    assert "password" not in result
    assert service.login(user.email, "wrong") is None
    assert service.login("missing@example.com", "secret") is None
    assert public is not None
    assert public["username"] == user.username
    assert "password" not in public
    assert service.get_user(9999) is None
