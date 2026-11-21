"""Listing submission, publication, visibility, and subscriber notifications."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.database import engine
from app.models.listing import ApplyMode, Listing
from app.models.notification import Notification, NotificationChannel
from app.models.subscription import Subscription
from app.models.user import User
from app.services.board_auth import get_user


def subscribe(graduate_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        graduate = session.get(User, graduate_id)
        if graduate is None or graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        if not graduate.is_eligible_graduate():
            return {"ok": False, "error": "only DCIT graduates may subscribe"}
        existing = session.exec(
            select(Subscription).where(Subscription.graduate_id == graduate_id)
        ).one_or_none()
        if existing is None:
            session.add(Subscription(graduate_id=graduate_id))
            session.commit()
    return {"ok": True}


def list_jobs_for_graduates() -> list[dict[str, Any]]:
    with Session(engine) as session:
        rows = session.exec(select(Listing).order_by(Listing.id)).all()
        return [row.model_dump() for row in rows if row.is_published_and_live()]


def list_pending_for_admin() -> list[dict[str, Any]]:
    with Session(engine) as session:
        rows = session.exec(
            select(Listing).where(Listing.status == "pending").order_by(Listing.id)
        ).all()
        return [row.model_dump() for row in rows]


def submit_listing(
    employer_id: int,
    title: str,
    company: str,
    description: str,
    apply_mode: str,
    deadline: str,
    external_url: str | None = None,
) -> dict[str, Any]:
    user = get_user(employer_id)
    if not user or user["role"] != "employer":
        return {"ok": False, "error": "employers only"}
    try:
        canonical_mode = ApplyMode(apply_mode)
    except ValueError:
        return {
            "ok": False,
            "error": "apply_mode must be external-link|on-platform-collect",
        }
    if canonical_mode == ApplyMode.EXTERNAL_LINK and not external_url:
        return {"ok": False, "error": "external_url required"}
    if canonical_mode == ApplyMode.ON_PLATFORM_COLLECT:
        external_url = None

    with Session(engine) as session:
        listing = Listing(
            employer_id=employer_id,
            title=title,
            company=company,
            description=description,
            apply_mode=canonical_mode,
            external_url=external_url,
            deadline=deadline,
            status="pending",
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        return {"ok": True, "listing_id": listing.id, "status": "pending"}


def publish_listing(admin_id: int, listing_id: int) -> dict[str, Any]:
    admin = get_user(admin_id)
    if not admin or admin["role"] != "admin":
        return {"ok": False, "error": "admin only"}
    with Session(engine) as session:
        listing = session.get(Listing, listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if listing.status == "published":
            return {"ok": True, "notified": 0, "count": 0}
        listing.publish()
        session.add(listing)
        count = 0
        if listing.apply_mode == ApplyMode.ON_PLATFORM_COLLECT:
            subscriptions = session.exec(select(Subscription)).all()
            for subscription in subscriptions:
                graduate = session.get(User, subscription.graduate_id)
                if graduate is not None and graduate.is_eligible_graduate():
                    session.add(Notification(
                        user_id=subscription.graduate_id,
                        listing_id=listing.id,
                        message=f"New job published: {listing.title} at {listing.company}",
                        channel=NotificationChannel.EMAIL,
                    ))
                    count += 1
        session.commit()
        return {"ok": True, "notified": count, "count": count}


def notify_subscribers(admin_id: int, listing_id: int) -> dict[str, Any]:
    admin = get_user(admin_id)
    if not admin or admin["role"] != "admin":
        return {"ok": False, "error": "admin only"}
    with Session(engine) as session:
        listing = session.get(Listing, listing_id)
        if listing is None or listing.status != "published":
            return {"ok": False, "error": "listing not found or unpublished"}
        if listing.apply_mode == ApplyMode.EXTERNAL_LINK:
            return {"ok": True, "count": 0}
        subscriptions = session.exec(select(Subscription)).all()
        count = 0
        for subscription in subscriptions:
            graduate = session.get(User, subscription.graduate_id)
            if graduate is not None and graduate.is_eligible_graduate():
                session.add(Notification(
                    user_id=subscription.graduate_id,
                    listing_id=listing.id,
                    message=f"New job published: {listing.title} at {listing.company}",
                    channel=NotificationChannel.EMAIL,
                ))
                count += 1
        session.commit()
        return {"ok": True, "count": count}
