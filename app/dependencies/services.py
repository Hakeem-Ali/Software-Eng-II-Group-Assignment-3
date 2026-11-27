"""FastAPI composition providers for repository-backed application services."""

from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.repositories.application import ApplicationRepository
from app.repositories.export_audit import ExportAuditRepository
from app.repositories.listing import ListingRepository
from app.repositories.notification import NotificationRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.unit_of_work import SqlModelUnitOfWork
from app.repositories.user import UserRepository
from app.services.applications import ApplicationService
from app.services.board_auth import BoardAuthService
from app.services.listings import ListingService
from app.services.notifications import NotificationService


def get_board_auth_service(
    session: Session = Depends(get_session),
) -> BoardAuthService:
    return BoardAuthService(UserRepository(session))


def get_listing_service(
    session: Session = Depends(get_session),
) -> ListingService:
    return ListingService(
        listings=ListingRepository(session),
        subscriptions=SubscriptionRepository(session),
        notifications=NotificationRepository(session),
        users=UserRepository(session),
        unit_of_work=SqlModelUnitOfWork(session),
    )


def get_application_service(
    session: Session = Depends(get_session),
) -> ApplicationService:
    return ApplicationService(
        applications=ApplicationRepository(session),
        listings=ListingRepository(session),
        users=UserRepository(session),
        notifications=NotificationRepository(session),
        export_audits=ExportAuditRepository(session),
        unit_of_work=SqlModelUnitOfWork(session),
    )


def get_notification_service(
    session: Session = Depends(get_session),
) -> NotificationService:
    return NotificationService(
        notifications=NotificationRepository(session),
        users=UserRepository(session),
    )
