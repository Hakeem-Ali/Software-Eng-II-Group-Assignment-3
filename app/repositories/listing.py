"""Persistence operations for job listings."""

from sqlmodel import Session, select

from app.models.listing import Listing, ListingStatus


class ListingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, listing_id: int) -> Listing | None:
        return self.db.get(Listing, listing_id)

    def for_graduates(self) -> list[Listing]:
        return self.db.exec(select(Listing).order_by(Listing.id)).all()

    def for_employer(self, employer_id: int) -> list[Listing]:
        return self.db.exec(
            select(Listing)
            .where(Listing.employer_id == employer_id)
            .order_by(Listing.id)
        ).all()

    def pending_for_admin(self) -> list[Listing]:
        return self.db.exec(
            select(Listing)
            .where(Listing.status == ListingStatus.PENDING)
            .order_by(Listing.id)
        ).all()

    def save(self, listing: Listing) -> Listing:
        self.db.add(listing)
        self.db.flush()
        return listing
