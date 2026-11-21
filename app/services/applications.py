"""Application creation, access, export, and lifecycle transitions."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.database import engine
from app.models.application import (
    Application,
    ApplicationAction,
    ApplicationHistory,
)
from app.models.export_audit import ExportAudit
from app.models.listing import ApplyMode, Listing
from app.models.notification import Notification, NotificationChannel
from app.models.user import User
from app.services.board_auth import get_user
from app.services.lifecycle import (
    ACTIONS,
    ListingOwnerPolicy,
    ReopenPolicy,
)


def _record_status_change(
    session: Session,
    application: Application,
    old_status: str,
    action: str | ApplicationAction,
    actor_id: int,
) -> None:
    session.add(ApplicationHistory(
        application_id=application.id,
        from_status=old_status,
        to_status=application.status,
        action=ApplicationAction(action),
        actor_id=actor_id,
    ))
    session.add(Notification(
        user_id=application.graduate_id,
        application_id=application.id,
        message=f"Your application status changed to {application.status}",
        channel=NotificationChannel.EMAIL,
    ))


def apply(
    graduate_id: int,
    listing_id: int,
    cover_letter: str,
    resume_text: str | None = None,
) -> dict[str, Any]:
    with Session(engine) as session:
        graduate = session.get(User, graduate_id)
        if graduate is None or graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        if not graduate.is_eligible_graduate():
            return {"ok": False, "error": "only DCIT graduates may apply"}

        listing = session.get(Listing, listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if listing.status != "published" or not listing.is_published_and_live():
            return {"ok": False, "error": "listing is not open"}
        if listing.apply_mode == ApplyMode.EXTERNAL_LINK:
            return {"ok": False, "error": "external-link listings do not collect applications"}

        existing = session.exec(
            select(Application).where(
                Application.graduate_id == graduate_id,
                Application.listing_id == listing_id,
            )
        ).first()
        if existing is not None:
            return {"ok": False, "error": "application already submitted"}

        application = Application(
            listing_id=listing_id,
            graduate_id=graduate_id,
            cover_letter=cover_letter,
            resume_text=resume_text or graduate.resume_text or "",
            status="submitted",
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        return {"ok": True, "application_id": application.id, "status": "submitted"}


def my_applications(graduate_id: int) -> list[dict[str, Any]]:
    with Session(engine) as session:
        rows = session.exec(
            select(Application)
            .where(Application.graduate_id == graduate_id)
            .order_by(Application.id)
        ).all()
        return [row.model_dump(exclude={"cover_letter", "resume_text"}) for row in rows]


def listing_applicants(viewer_id: int, listing_id: int) -> dict[str, Any]:
    viewer = get_user(viewer_id)
    if not viewer:
        return {"ok": False, "error": "unknown user"}
    with Session(engine) as session:
        listing = session.get(Listing, listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if not ListingOwnerPolicy.can_read(viewer, listing):
            return {"ok": False, "error": "forbidden"}
        rows = session.exec(
            select(Application)
            .where(Application.listing_id == listing_id)
            .order_by(Application.id)
        ).all()
        return {"ok": True, "applicants": [row.model_dump() for row in rows]}


def export_applicants(admin_id: int, listing_id: int) -> dict[str, Any]:
    admin = get_user(admin_id)
    if not admin or admin["role"] != "admin":
        return {"ok": False, "error": "admin only"}
    with Session(engine) as session:
        listing = session.get(Listing, listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        rows = session.exec(
            select(Application)
            .where(Application.listing_id == listing_id)
            .order_by(Application.id)
        ).all()
        package = [row.model_dump() for row in rows]
        session.add(ExportAudit(
            admin_id=admin_id,
            listing_id=listing_id,
            applicant_count=len(package),
        ))
        session.commit()
        return {"ok": True, "format": "json", "package": package}


def transition_application(
    actor_id: int, application_id: int, action: str
) -> dict[str, Any]:
    actor = get_user(actor_id)
    if not actor:
        return {"ok": False, "error": "unknown user"}
    if action not in ACTIONS or action == ApplicationAction.REOPEN:
        return {"ok": False, "error": "use the admin reopen operation"}

    with Session(engine) as session:
        row = session.get(Application, application_id)
        if row is None:
            return {"ok": False, "error": "application not found"}
        listing = session.get(Listing, row.listing_id)
        if not ListingOwnerPolicy.can_advance(actor, listing):
            return {"ok": False, "error": "only the listing employer may advance applications"}

        old_status = row.status
        try:
            row.apply(action)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        session.add(row)
        _record_status_change(session, row, old_status, action, actor_id)
        session.commit()
        session.refresh(row)
        return {"ok": True, "application": row.model_dump(), "changed": True}


def reopen_application(actor_id: int, application_id: int) -> dict[str, Any]:
    actor = get_user(actor_id)
    if not actor or not ReopenPolicy.can_reopen(actor):
        return {"ok": False, "error": "admin reopen only"}
    with Session(engine) as session:
        row = session.get(Application, application_id)
        if row is None:
            return {"ok": False, "error": "application not found"}
        old_status = row.status
        try:
            row.apply(ApplicationAction.REOPEN)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        session.add(row)
        _record_status_change(
            session,
            row,
            old_status,
            ApplicationAction.REOPEN,
            actor_id,
        )
        session.commit()
        session.refresh(row)
        return {"ok": True, "application": row.model_dump(), "changed": True}
