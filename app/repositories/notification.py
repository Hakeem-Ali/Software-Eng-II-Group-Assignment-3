"""Persistence operations for in-platform notification records."""

from sqlmodel import Session, select

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def add_many(self, notifications: list[Notification]) -> list[Notification]:
        self.db.add_all(notifications)
        self.db.flush()
        return notifications

    def list_for_user(self, user_id: int) -> list[Notification]:
        return self.db.exec(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.id)
        ).all()
