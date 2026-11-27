"""Listing submission, publication, visibility, and subscriber notifications."""

from __future__ import annotations

from typing import Any

from app.models.listing import ApplyMode, Listing, ListingStatus
from app.models.notification import Notification, NotificationChannel
from app.models.subscription import Subscription
from app.repositories.listing import ListingRepository
from app.repositories.notification import NotificationRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user import UserRepository


class ListingService:
    def __init__(
        self,
        listings: ListingRepository,
        subscriptions: SubscriptionRepository,
        notifications: NotificationRepository,
        users: UserRepository,
        unit_of_work: UnitOfWork,
    ):
        self.listings = listings
        self.subscriptions = subscriptions
        self.notifications = notifications
        self.users = users
        self.unit_of_work = unit_of_work

    def subscribe(self, graduate_id: int) -> dict[str, Any]:
        graduate = self.users.get_by_id(graduate_id)
        if graduate is None or graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        if not graduate.is_eligible_graduate():
            return {"ok": False, "error": "only DCIT graduates may subscribe"}

        if self.subscriptions.get_for_graduate(graduate_id) is None:
            self.subscriptions.save(Subscription(graduate_id=graduate_id))
            self.unit_of_work.commit()
        return {"ok": True}

    def unsubscribe(self, graduate_id: int) -> dict[str, Any]:
        graduate = self.users.get_by_id(graduate_id)
        if graduate is None:
            return {"ok": False, "error": "user not found"}
        if graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        if not self.subscriptions.delete_for_graduate(graduate_id):
            return {"ok": False, "error": "subscription not found"}
        self.unit_of_work.commit()
        return {"ok": True}

    def list_jobs_for_graduates(self) -> list[dict[str, Any]]:
        return [
            listing.model_dump()
            for listing in self.listings.for_graduates()
            if listing.is_published_and_live()
        ]

    def list_pending_for_admin(self) -> list[dict[str, Any]]:
        return [
            listing.model_dump()
            for listing in self.listings.pending_for_admin()
        ]

    def employer_listings(self, employer_id: int) -> dict[str, Any]:
        employer = self.users.get_by_id(employer_id)
        if employer is None or employer.role != "employer":
            return {"ok": False, "error": "employers only"}
        return {
            "ok": True,
            "listings": [
                listing.model_dump()
                for listing in self.listings.for_employer(employer_id)
            ],
        }

    def get_job(self, actor_id: int, listing_id: int) -> dict[str, Any]:
        actor = self.users.get_by_id(actor_id)
        if actor is None:
            return {"ok": False, "error": "unknown user"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if listing.status != ListingStatus.PUBLISHED or not listing.is_published_and_live():
            return {"ok": False, "error": "listing not found"}
        return {"ok": True, "listing": listing.model_dump()}

    def submit_listing(
        self,
        employer_id: int,
        title: str,
        company: str,
        description: str,
        apply_mode: str,
        deadline: str,
        external_url: str | None = None,
    ) -> dict[str, Any]:
        employer = self.users.get_by_id(employer_id)
        if employer is None or employer.role != "employer":
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

        listing = Listing(
            employer_id=employer_id,
            title=title,
            company=company,
            description=description,
            apply_mode=canonical_mode,
            external_url=external_url,
            deadline=deadline,
            status=ListingStatus.PENDING,
        )
        self.listings.save(listing)
        self.unit_of_work.commit()
        return {
            "ok": True,
            "listing_id": listing.id,
            "status": str(listing.status),
        }

    def _create_listing_notifications(self, listing: Listing) -> int:
        subscriptions = self.subscriptions.all()
        graduate_ids = {subscription.graduate_id for subscription in subscriptions}
        graduates = [
            graduate
            for graduate in self.users.get_by_ids(graduate_ids)
            if graduate.is_eligible_graduate() and graduate.id in graduate_ids
        ]
        notifications = [
            Notification(
                user_id=graduate.id,
                listing_id=listing.id,
                text=f"New job published: {listing.title} at {listing.company}",
                channel=NotificationChannel.EMAIL,
            )
            for graduate in graduates
        ]
        self.notifications.add_many(notifications)
        return len(notifications)

    def publish_listing(self, admin_id: int, listing_id: int) -> dict[str, Any]:
        admin = self.users.get_by_id(admin_id)
        if admin is None or admin.role != "admin":
            return {"ok": False, "error": "admin only"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        if listing.status == ListingStatus.PUBLISHED:
            return {"ok": True, "notified": 0, "count": 0}
        listing.publish()
        self.listings.save(listing)
        count = 0
        if listing.apply_mode == ApplyMode.ON_PLATFORM_COLLECT:
            count = self._create_listing_notifications(listing)
        self.unit_of_work.commit()
        return {"ok": True, "notified": count, "count": count}

    def deny_listing(self, admin_id: int, listing_id: int) -> dict[str, Any]:
        admin = self.users.get_by_id(admin_id)
        if admin is None or admin.role != "admin":
            return {"ok": False, "error": "admin only"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        try:
            listing.deny()
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        self.listings.save(listing)
        self.unit_of_work.commit()
        return {"ok": True, "listing_id": listing_id, "status": str(listing.status)}

    def unpublish_listing(self, admin_id: int, listing_id: int) -> dict[str, Any]:
        admin = self.users.get_by_id(admin_id)
        if admin is None or admin.role != "admin":
            return {"ok": False, "error": "admin only"}
        listing = self.listings.get(listing_id)
        if listing is None:
            return {"ok": False, "error": "listing not found"}
        try:
            listing.unpublish()
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        self.listings.save(listing)
        self.unit_of_work.commit()
        return {"ok": True, "listing_id": listing_id, "status": str(listing.status)}

    def notify_subscribers(self, admin_id: int, listing_id: int) -> dict[str, Any]:
        admin = self.users.get_by_id(admin_id)
        if admin is None or admin.role != "admin":
            return {"ok": False, "error": "admin only"}
        listing = self.listings.get(listing_id)
        if listing is None or listing.status != ListingStatus.PUBLISHED:
            return {"ok": False, "error": "listing not found or unpublished"}
        if listing.apply_mode == ApplyMode.EXTERNAL_LINK:
            return {"ok": True, "count": 0}
        count = self._create_listing_notifications(listing)
        self.unit_of_work.commit()
        return {"ok": True, "count": count}
