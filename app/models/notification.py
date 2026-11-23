from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel


class NotificationChannel(StrEnum):
    EMAIL = "EMAIL"
    ON_PLATFORM = "ON_PLATFORM"


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    application_id: Optional[int] = Field(default=None, foreign_key="application.id", index=True)
    listing_id: Optional[int] = Field(default=None, foreign_key="listing.id", index=True)
    text: str
    channel: NotificationChannel = Field(default=NotificationChannel.EMAIL)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        self.channel = NotificationChannel(data.get("channel", NotificationChannel.EMAIL))
