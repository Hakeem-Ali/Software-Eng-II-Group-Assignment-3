"""Scenario authentication use cases backed by injected user persistence."""

from __future__ import annotations

from typing import Any

from app.models.user import User
from app.repositories.user import UserRepository
from app.utilities.security import verify_password


def public_user(user: User | dict[str, Any] | None) -> dict[str, Any] | None:
    if user is None:
        return None
    data = user.model_dump() if isinstance(user, User) else dict(user)
    data.pop("password", None)
    data.pop("password_hash", None)
    return data


class BoardAuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def login(self, email: str, password: str) -> dict[str, Any] | None:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password):
            return None
        return public_user(user)

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        return public_user(self.users.get_by_id(user_id))
