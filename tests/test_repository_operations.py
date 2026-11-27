from app.models.application import (
    Application,
    ApplicationHistory,
    ApplicationStatus,
)
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.repositories.application import ApplicationRepository
from app.repositories.notification import NotificationRepository
from app.repositories.subscription import SubscriptionRepository


def test_application_repository_lists_active_applications_and_history(test_session):
    applications = [
        Application(
            listing_id=1,
            graduate_id=10,
            cover_letter="Submitted",
            resume_text="Resume",
            status=ApplicationStatus.SUBMITTED,
        ),
        Application(
            listing_id=2,
            graduate_id=10,
            cover_letter="Rejected",
            resume_text="Resume",
            status=ApplicationStatus.REJECTED,
        ),
        Application(
            listing_id=3,
            graduate_id=10,
            cover_letter="Hired",
            resume_text="Resume",
            status=ApplicationStatus.HIRED,
        ),
        Application(
            listing_id=4,
            graduate_id=20,
            cover_letter="Other graduate",
            resume_text="Resume",
            status=ApplicationStatus.REVIEWED,
        ),
    ]
    test_session.add_all(applications)
    test_session.commit()
    test_session.refresh(applications[0])

    history = ApplicationHistory(
        application_id=applications[0].id,
        from_status=ApplicationStatus.SUBMITTED,
        to_status=ApplicationStatus.REVIEWED,
        action="mark_reviewed",
        actor_id=30,
    )
    test_session.add(history)
    test_session.commit()

    repository = ApplicationRepository(test_session)
    active = repository.active_for_applicant(10)
    application_history = repository.history_for_application(applications[0].id)

    assert [application.status for application in active] == [
        ApplicationStatus.SUBMITTED
    ]
    assert len(application_history) == 1
    assert application_history[0].to_status == ApplicationStatus.REVIEWED


def test_notification_and_subscription_repositories_filter_and_delete(test_session):
    test_session.add_all([
        Notification(user_id=10, text="Status updated"),
        Notification(user_id=20, text="Other user"),
        Subscription(graduate_id=10),
    ])
    test_session.commit()

    notifications = NotificationRepository(test_session).list_for_user(10)
    subscriptions = SubscriptionRepository(test_session)

    assert len(notifications) == 1
    assert notifications[0].text == "Status updated"
    assert subscriptions.delete_for_graduate(10)
    assert not subscriptions.delete_for_graduate(10)
