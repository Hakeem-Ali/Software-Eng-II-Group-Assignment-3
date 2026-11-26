"""Application creation, access, export, and lifecycle use cases."""

from __future__ import annotations

from typing import Any

from app.models.application import (
    Application,
    ApplicationAction,
    ApplicationHistory,
    ApplicationStatus,
)
from app.models.listing import ApplyMode
from app.models.notification import Notification, NotificationChannel
from app.models.export_audit import ExportAudit
from app.repositories.application import ApplicationRepository
from app.repositories.export_audit import ExportAuditRepository
from app.repositories.listing import ListingRepository
from app.repositories.notification import NotificationRepository
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user import UserRepository
from app.services.lifecycle import (
    ACTIONS,
    ListingOwnerPolicy,
    ReopenPolicy,
)


class ApplicationService:
    def __init__(
        self,
        applications: ApplicationRepository,
        listings: ListingRepository,
        users: UserRepository,
        notifications: NotificationRepository,
        export_audits: ExportAuditRepository,
        unit_of_work: UnitOfWork,
    ):
        self.applications = applications
        self.listings = listings
        self.users = users
        self.notifications = notifications
        self.export_audits = export_audits
        self.unit_of_work = unit_of_work

    def _record_status_change(
        self,
        application: Application,
        old_status: ApplicationStatus,
        action: str | ApplicationAction,
        actor_id: int,
    ) -> None:
        self.applications.add_history(
            ApplicationHistory(
                application_id=application.id,
                from_status=old_status,
                to_status=application.status,
                action=ApplicationAction(action),
                actor_id=actor_id,
            )
        )
        self.notifications.add(
            Notification(
                user_id=application.graduate_id,
                application_id=application.id,
                message=f"Your application status changed to {application.status}",
                channel=NotificationChannel.EMAIL,
            )
        )

    def apply(
        self,
        graduate_id: int,
        listing_id: int,
        cover_letter: str,
        resume_text: str | None = None,
    ) -> dict[str, Any]:
        graduate = self.users.get_by_id(graduate_id)
        if graduate is None or graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        if not graduate.is_eligible_graduate():
            return {"ok": False, "error": "only DCIT graduates may apply"}

        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if listing.status != "published" or not listing.is_published_and_live():
            return {"ok": False, "error": "listing is not open"}
        if listing.apply_mode == ApplyMode.EXTERNAL_LINK:
            return {
                "ok": False,
                "error": "external-link listings do not collect applications",
            }

        existing = self.applications.find_for_applicant_and_listing(
            graduate_id, listing_id
        )
        if existing is not None:
            return {"ok": False, "error": "application already submitted"}

        application = Application(
            listing_id=listing_id,
            graduate_id=graduate_id,
            cover_letter=cover_letter,
            resume_text=resume_text or graduate.resume_text or "",
            status=ApplicationStatus.SUBMITTED,
        )
        self.applications.save(application)
        self.unit_of_work.commit()
        return {
            "ok": True,
            "application_id": application.id,
            "status": str(application.status),
        }

    def my_applications(self, graduate_id: int) -> list[dict[str, Any]]:
        rows = self.applications.for_applicant(graduate_id)
        return [
            row.model_dump(exclude={"cover_letter", "resume_text"})
            for row in rows
        ]

    def listing_applicants(
        self, viewer_id: int, listing_id: int
    ) -> dict[str, Any]:
        viewer = self.users.get_by_id(viewer_id)
        if viewer is None:
            return {"ok": False, "error": "unknown user"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if not ListingOwnerPolicy.can_read(
            {"id": viewer.id, "role": viewer.role}, listing
        ):
            return {"ok": False, "error": "forbidden"}
        rows = self.applications.for_listing(listing_id)
        return {"ok": True, "applicants": [row.model_dump() for row in rows]}

    def export_applicants(
        self, admin_id: int, listing_id: int
    ) -> dict[str, Any]:
        admin = self.users.get_by_id(admin_id)
        if admin is None or admin.role != "admin":
            return {"ok": False, "error": "admin only"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        rows = self.applications.for_listing(listing_id)
        package = [row.model_dump() for row in rows]
        self.export_audits.add(
            ExportAudit(
                admin_id=admin_id,
                listing_id=listing_id,
                applicant_count=len(package),
            )
        )
        self.unit_of_work.commit()
        return {"ok": True, "format": "json", "package": package}

    def transition_application(
        self, actor_id: int, application_id: int, action: str
    ) -> dict[str, Any]:
        actor = self.users.get_by_id(actor_id)
        if actor is None:
            return {"ok": False, "error": "unknown user"}
        if action not in ACTIONS or action == ApplicationAction.REOPEN:
            return {"ok": False, "error": "use the admin reopen operation"}

        application = self.applications.get(application_id)
        if application is None:
            return {"ok": False, "error": "application not found"}
        listing = self.listings.get(application.listing_id)
        if not ListingOwnerPolicy.can_advance(
            {"id": actor.id, "role": actor.role}, listing
        ):
            return {
                "ok": False,
                "error": "only the listing employer may advance applications",
            }

        old_status = application.status
        try:
            application.apply(action)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        self.applications.save(application)
        self._record_status_change(application, old_status, action, actor_id)
        self.unit_of_work.commit()
        return {
            "ok": True,
            "application": application.model_dump(),
            "changed": True,
        }

    def reopen_application(
        self, actor_id: int, application_id: int
    ) -> dict[str, Any]:
        actor = self.users.get_by_id(actor_id)
        if actor is None or not ReopenPolicy.can_reopen({"role": actor.role}):
            return {"ok": False, "error": "admin reopen only"}
        application = self.applications.get(application_id)
        if application is None:
            return {"ok": False, "error": "application not found"}
        old_status = application.status
        try:
            application.apply(ApplicationAction.REOPEN)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        self.applications.save(application)
        self._record_status_change(
            application,
            old_status,
            ApplicationAction.REOPEN,
            actor_id,
        )
        self.unit_of_work.commit()
        return {
            "ok": True,
            "application": application.model_dump(),
            "changed": True,
        }
