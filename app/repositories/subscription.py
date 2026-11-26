"""Persistence operations for graduate listing subscriptions."""

from sqlmodel import Session, select

from app.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_graduate(self, graduate_id: int) -> Subscription | None:
        return self.db.exec(
            select(Subscription).where(Subscription.graduate_id == graduate_id)
        ).one_or_none()

    def all(self) -> list[Subscription]:
        return self.db.exec(select(Subscription).order_by(Subscription.id)).all()

    def save(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription
