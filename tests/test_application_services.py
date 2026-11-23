
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

import app.models
from app.models.user import User
from app.models.listing import Listing, ApplyMode
from app.models.application import (
    Application,
    ApplicationAction,
    ApplicationHistory,
    ApplicationStatus,
)
from app.models.notification import Notification, NotificationChannel


@pytest.fixture
def application_context(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    monkeypatch.setattr(
        "app.services.applications.engine", test_engine
    )
    monkeypatch.setattr(
        "app.services.board_auth.engine", test_engine
    )

    with Session(test_engine) as session:
        graduate = User(
            username="graduate",
            email="graduate@example.com",
            password="test-password",
            role="graduate",
            programme="DCIT",
        )

        employer = User(
            username="employer",
            email="employer@example.com",
            password="test-password",
            role="employer",
        )

        other_employer = User(
            username="other_employer",
            email="other@example.com",
            password="test-password",
            role="employer",
        )

        admin = User(
            username="admin",
            email="admin@example.com",
            password="test-password",
            role="admin",
        )

        session.add_all([
            graduate,
            employer,
            other_employer,
            admin,
        ])
        session.commit()

        listing = Listing(
            employer_id=employer.id,
            title="Junior Developer",
            company="Test Company",
            description="Test job listing",
            apply_mode=ApplyMode.ON_PLATFORM_COLLECT,
            deadline="2099-12-31",
            status="published",
        )

        session.add(listing)
        session.commit()
        session.refresh(listing)

        application = Application(
            listing_id=listing.id,
            graduate_id=graduate.id,
            cover_letter="Test cover letter",
            resume_text="Test resume",
            status="submitted",
        )

        session.add(application)
        session.commit()
        session.refresh(application)

        context = {
            "engine": test_engine,
            "graduate_id": graduate.id,
            "employer_id": employer.id,
            "other_employer_id": other_employer.id,
            "admin_id": admin.id,
            "listing_id": listing.id,
            "application_id": application.id,
        }

    yield context

    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_status_change_creates_history_and_notification(
    application_context,
):
    from app.services.applications import transition_application

    result = transition_application(
        application_context["employer_id"],
        application_context["application_id"],
        "mark_reviewed",
    )

    assert result["ok"] is True
    assert result["application"]["status"] == "reviewed"

    with Session(application_context["engine"]) as session:
        history = session.exec(
            select(ApplicationHistory)
        ).all()

        notifications = session.exec(
            select(Notification)
        ).all()

        assert len(history) == 1
        assert history[0].from_status == ApplicationStatus.SUBMITTED
        assert history[0].to_status == ApplicationStatus.REVIEWED
        assert history[0].action == ApplicationAction.MARK_REVIEWED
        assert history[0].actor_id == application_context["employer_id"]
        assert history[0].occurred_at is not None

        assert len(notifications) == 1
        assert notifications[0].user_id == application_context["graduate_id"]
        assert notifications[0].application_id == application_context["application_id"]
        assert notifications[0].channel == NotificationChannel.EMAIL
        assert "reviewed" in notifications[0].message.lower()


def test_other_employer_cannot_change_application(
    application_context,
):
    from app.services.applications import transition_application

    result = transition_application(
        application_context["other_employer_id"],
        application_context["application_id"],
        "mark_reviewed",
    )

    assert result["ok"] is False
    assert "only the listing employer" in result["error"]

    with Session(application_context["engine"]) as session:
        application = session.get(
            Application,
            application_context["application_id"],
        )

        history = session.exec(
            select(ApplicationHistory)
        ).all()

        notifications = session.exec(
            select(Notification)
        ).all()

        assert application.status == ApplicationStatus.SUBMITTED
        assert len(history) == 0
        assert len(notifications) == 0


def test_admin_reopening_creates_history_and_notification(
    application_context,
):
    from app.services.applications import reopen_application

    with Session(application_context["engine"]) as session:
        application = session.get(
            Application,
            application_context["application_id"],
        )
        application.status = ApplicationStatus.REJECTED
        session.add(application)
        session.commit()

    result = reopen_application(
        application_context["admin_id"],
        application_context["application_id"],
    )

    assert result["ok"] is True
    assert result["application"]["status"] == "reviewed"

    with Session(application_context["engine"]) as session:
        history = session.exec(
            select(ApplicationHistory)
        ).all()

        notifications = session.exec(
            select(Notification)
        ).all()

        assert len(history) == 1
        assert history[0].from_status == ApplicationStatus.REJECTED
        assert history[0].to_status == ApplicationStatus.REVIEWED
        assert history[0].action == ApplicationAction.REOPEN
        assert history[0].actor_id == application_context["admin_id"]
        assert history[0].occurred_at is not None

        assert len(notifications) == 1
        assert notifications[0].user_id == application_context["graduate_id"]
        assert notifications[0].application_id == application_context["application_id"]
        assert notifications[0].channel == NotificationChannel.EMAIL


def test_graduate_cannot_submit_duplicate_application(
    application_context,
):
    from app.services.applications import apply

    result = apply(
        application_context["graduate_id"],
        application_context["listing_id"],
        "Another cover letter",
    )

    assert result["ok"] is False
    assert result["error"] == "application already submitted"

    with Session(application_context["engine"]) as session:
        applications = session.exec(
            select(Application)
        ).all()

        assert len(applications) == 1


def test_non_dcit_graduate_cannot_apply(
    application_context,
):
    from app.services.applications import apply

    with Session(application_context["engine"]) as session:
        graduate = User(
            username="other_graduate",
            email="othergraduate@example.com",
            password="test-password",
            role="graduate",
            programme="Other",
        )

        session.add(graduate)
        session.commit()
        session.refresh(graduate)

        graduate_id = graduate.id

    result = apply(
        graduate_id,
        application_context["listing_id"],
        "Test cover letter",
    )

    assert result["ok"] is False
    assert result["error"] == "only DCIT graduates may apply"


def test_external_link_listing_does_not_accept_applications(
    application_context,
):
    from app.services.applications import apply

    with Session(application_context["engine"]) as session:
        listing = Listing(
            employer_id=application_context["employer_id"],
            title="External Developer Position",
            company="External Company",
            description="Apply through the external website",
            apply_mode=ApplyMode.EXTERNAL_LINK,
            deadline="2099-12-31",
            status="published",
        )

        session.add(listing)
        session.commit()
        session.refresh(listing)

        listing_id = listing.id

    result = apply(
        application_context["graduate_id"],
        listing_id,
        "Test cover letter",
    )

    assert result["ok"] is False
    assert result["error"] == "external-link listings do not collect applications"

    with Session(application_context["engine"]) as session:
        applications = session.exec(
            select(Application).where(
                Application.listing_id == listing_id
            )
        ).all()

        assert len(applications) == 0
