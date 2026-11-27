"""Notification listing use cases."""

from typing import Any

from app.repositories.notification import NotificationRepository
from app.repositories.user import UserRepository


class NotificationService:
    def __init__(
        self,
        notifications: NotificationRepository,
        users: UserRepository,
    ):
        self.notifications = notifications
        self.users = users

    def list_notifications(self, graduate_id: int) -> dict[str, Any]:
        graduate = self.users.get_by_id(graduate_id)
        if graduate is None:
            return {"ok": False, "error": "unknown user"}
        if graduate.role != "graduate":
            return {"ok": False, "error": "graduates only"}
        rows = self.notifications.list_for_user(graduate_id)
        return {
            "ok": True,
            "notifications": [row.model_dump() for row in rows],
        }
