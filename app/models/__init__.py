"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.application import (
    Application,
    ApplicationHistory,
    ApplicationStatus,
    IllegalTransitionError,
    UnauthorizedTransitionError,
)
from app.models.listing import ApplyMode, Listing, ListingStatus
from app.models.notification import Notification, NotificationChannel
from app.models.subscription import Subscription
from app.models.user import User
from app.models.export_audit import ExportAudit

__all__ = [
    "User",
    "Listing",
    "Application",
    "Subscription",
    "Notification",
    "ApplicationHistory",
    "ApplicationStatus",
    "ApplyMode",
    "ListingStatus",
    "NotificationChannel",
    "IllegalTransitionError",
    "UnauthorizedTransitionError",
    "ExportAudit",
]
