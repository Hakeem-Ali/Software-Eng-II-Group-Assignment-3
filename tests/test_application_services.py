
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
from app.models.export_audit import ExportAudit
from app.models.notification import Notification, NotificationChannel


@pytest.fixture
def application_context():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

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

    service_session = Session(test_engine)
    from app.repositories.application import ApplicationRepository
    from app.repositories.export_audit import ExportAuditRepository
    from app.repositories.listing import ListingRepository
    from app.repositories.notification import NotificationRepository
    from app.repositories.unit_of_work import SqlModelUnitOfWork
    from app.repositories.user import UserRepository
    from app.services.applications import ApplicationService

    context["service"] = ApplicationService(
        applications=ApplicationRepository(service_session),
        listings=ListingRepository(service_session),
        users=UserRepository(service_session),
        notifications=NotificationRepository(service_session),
        export_audits=ExportAuditRepository(service_session),
        unit_of_work=SqlModelUnitOfWork(service_session),
    )
    yield context

    service_session.close()
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_status_change_creates_history_and_notification(
    application_context,
):
    result = application_context["service"].transition_application(
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
        assert "reviewed" in notifications[0].text.lower()


def test_other_employer_cannot_change_application(
    application_context,
):
    result = application_context["service"].transition_application(
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
    with Session(application_context["engine"]) as session:
        application = session.get(
            Application,
            application_context["application_id"],
        )
        application.status = ApplicationStatus.REJECTED
        session.add(application)
        session.commit()

    result = application_context["service"].reopen_application(
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
    result = application_context["service"].apply(
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

    result = application_context["service"].apply(
        graduate_id,
        application_context["listing_id"],
        "Test cover letter",
    )

    assert result["ok"] is False
    assert result["error"] == "only DCIT graduates may apply"


def test_non_graduate_cannot_apply(application_context):
    result = application_context["service"].apply(
        application_context["employer_id"],
        application_context["listing_id"],
        "Test cover letter",
    )

    assert result == {"ok": False, "error": "graduates only"}


def test_application_cannot_be_submitted_to_pending_listing(
    application_context,
):
    with Session(application_context["engine"]) as session:
        listing = Listing(
            employer_id=application_context["employer_id"],
            title="Pending Developer Position",
            company="Test Company",
            description="Not published yet",
            apply_mode=ApplyMode.ON_PLATFORM_COLLECT,
            deadline="2099-12-31",
            status="pending",
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        listing_id = listing.id

    result = application_context["service"].apply(
        application_context["graduate_id"],
        listing_id,
        "Test cover letter",
    )

    assert result == {"ok": False, "error": "listing is not open"}
    with Session(application_context["engine"]) as session:
        applications = session.exec(
            select(Application).where(Application.listing_id == listing_id)
        ).all()
        assert applications == []


def test_external_link_listing_does_not_accept_applications(
    application_context,
):
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

    result = application_context["service"].apply(
        application_context["graduate_id"],
        listing_id,
        "Test cover letter",
    )

    assert result["ok"] is False
    assert result["error"] == "external-link listings do not collect applications"

    with Session(application_context["engine"]) as session:
        applications = session.exec(
            select(Application).where(Application.listing_id == listing_id)
        ).all()
        assert len(applications) == 0


def test_application_history_is_employer_or_admin_only(application_context):
    service = application_context["service"]
    transition = service.transition_application(
        application_context["employer_id"],
        application_context["application_id"],
        "mark_reviewed",
    )
    assert transition["ok"]

    history = service.application_history(
        application_context["employer_id"],
        application_context["application_id"],
    )
    denied = service.application_history(
        application_context["graduate_id"],
        application_context["application_id"],
    )
    admin_history = service.application_history(
        application_context["admin_id"],
        application_context["application_id"],
    )

    assert history["ok"]
    assert len(history["history"]) == 1
    assert history["history"][0]["from_status"] == "submitted"
    assert denied == {"ok": False, "error": "forbidden"}
    assert admin_history["ok"]


def test_active_applications_exclude_rejected_and_hired(application_context):
    service = application_context["service"]
    graduate_id = application_context["graduate_id"]

    with Session(application_context["engine"]) as session:
        rejected = Application(
            listing_id=application_context["listing_id"],
            graduate_id=graduate_id,
            cover_letter="Rejected applicant",
            resume_text="Resume",
            status=ApplicationStatus.REJECTED,
        )
        hired = Application(
            listing_id=application_context["listing_id"],
            graduate_id=graduate_id,
            cover_letter="Hired applicant",
            resume_text="Resume",
            status=ApplicationStatus.HIRED,
        )
        session.add_all([rejected, hired])
        session.commit()

    result = service.my_active_applications(graduate_id)

    assert result["ok"]
    assert len(result["applications"]) == 1
    assert result["applications"][0]["status"] == "submitted"


def test_apply_creates_application_using_graduate_resume_fallback(
    application_context,
):
    with Session(application_context["engine"]) as session:
        listing = Listing(
            employer_id=application_context["employer_id"],
            title="Another Developer Position",
            company="Another Company",
            description="Apply in platform",
            apply_mode=ApplyMode.ON_PLATFORM_COLLECT,
            deadline="2099-12-31",
            status="published",
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        listing_id = listing.id

    result = application_context["service"].apply(
        application_context["graduate_id"],
        listing_id,
        "Cover letter",
    )

    assert result["ok"] is True
    assert result["status"] == "submitted"
    with Session(application_context["engine"]) as session:
        application = session.exec(
            select(Application).where(Application.listing_id == listing_id)
        ).one()
        assert application.graduate_id == application_context["graduate_id"]
        assert application.cover_letter == "Cover letter"
        assert application.resume_text == ""
        assert application.status == ApplicationStatus.SUBMITTED


def test_my_applications_omits_private_application_text(application_context):
    result = application_context["service"].my_applications(
        application_context["graduate_id"]
    )

    assert len(result) == 1
    assert result[0]["id"] == application_context["application_id"]
    assert "cover_letter" not in result[0]
    assert "resume_text" not in result[0]


def test_read_application_allows_owner_and_admin_but_denies_other_employer(
    application_context,
):
    service = application_context["service"]

    owner_result = service.read_application(
        application_context["graduate_id"],
        application_context["application_id"],
    )
    employer_result = service.read_application(
        application_context["employer_id"],
        application_context["application_id"],
    )
    admin_result = service.read_application(
        application_context["admin_id"],
        application_context["application_id"],
    )
    denied_result = service.read_application(
        application_context["other_employer_id"],
        application_context["application_id"],
    )

    assert owner_result["ok"] is True
    assert employer_result["ok"] is True
    assert admin_result["ok"] is True
    assert denied_result == {"ok": False, "error": "forbidden"}


def test_listing_applicants_is_restricted_to_listing_employer(
    application_context,
):
    service = application_context["service"]

    allowed = service.listing_applicants(
        application_context["employer_id"],
        application_context["listing_id"],
    )
    denied = service.listing_applicants(
        application_context["other_employer_id"],
        application_context["listing_id"],
    )

    assert allowed["ok"] is True
    assert len(allowed["applicants"]) == 1
    assert denied == {"ok": False, "error": "forbidden"}


def test_admin_export_records_audit_and_returns_applicants(
    application_context,
):
    result = application_context["service"].export_applicants(
        application_context["admin_id"],
        application_context["listing_id"],
    )

    assert result["ok"] is True
    assert result["format"] == "json"
    assert len(result["package"]) == 1
    assert result["package"][0]["id"] == application_context["application_id"]
    with Session(application_context["engine"]) as session:
        audit = session.exec(select(ExportAudit)).one()
        assert audit.admin_id == application_context["admin_id"]
        assert audit.listing_id == application_context["listing_id"]
        assert audit.applicant_count == 1


def test_non_admin_cannot_export_applicants(application_context):
    result = application_context["service"].export_applicants(
        application_context["employer_id"],
        application_context["listing_id"],
    )

    assert result == {"ok": False, "error": "admin only"}
    with Session(application_context["engine"]) as session:
        assert session.exec(select(ExportAudit)).all() == []


@pytest.mark.parametrize(
    ("action", "expected_error"),
    [
        ("reopen", "use the admin reopen operation"),
        ("shortlist", "shortlist is illegal from submitted"),
        ("unknown", "use the admin reopen operation"),
    ],
)
def test_transition_application_rejects_invalid_action_without_side_effects(
    application_context,
    action,
    expected_error,
):
    result = application_context["service"].transition_application(
        application_context["employer_id"],
        application_context["application_id"],
        action,
    )

    assert result == {"ok": False, "error": expected_error}
    with Session(application_context["engine"]) as session:
        application = session.get(
            Application,
            application_context["application_id"],
        )
        history = session.exec(select(ApplicationHistory)).all()
        notifications = session.exec(select(Notification)).all()
        assert application.status == ApplicationStatus.SUBMITTED
        assert history == []
        assert notifications == []


def test_reopen_application_is_admin_only(application_context):
    result = application_context["service"].reopen_application(
        application_context["employer_id"],
        application_context["application_id"],
    )

    assert result == {"ok": False, "error": "admin reopen only"}
