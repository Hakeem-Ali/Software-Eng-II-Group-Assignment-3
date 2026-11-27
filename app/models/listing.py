from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel


class ApplyMode(StrEnum):
    EXTERNAL_LINK = "external-link"
    ON_PLATFORM_COLLECT = "on-platform-collect"


class ListingStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    DENIED = "denied"


class Listing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employer_id: int = Field(foreign_key="user.id", index=True)
    title: str
    company: str
    description: str
    apply_mode: ApplyMode
    external_url: Optional[str] = None
    deadline: str
    status: ListingStatus = Field(default=ListingStatus.PENDING)
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        self.apply_mode = ApplyMode(data["apply_mode"])
        self.status = ListingStatus(data.get("status", ListingStatus.PENDING))

    def publish(self) -> None:
        if self.status == ListingStatus.PUBLISHED:
            return
        if self.status != ListingStatus.PENDING:
            raise ValueError(f"cannot publish listing with status {self.status}")
        self.status = ListingStatus.PUBLISHED
        self.published_at = datetime.now(timezone.utc)

    def deny(self) -> None:
        if self.status != ListingStatus.PENDING:
            raise ValueError(f"cannot deny listing with status {self.status}")
        self.status = ListingStatus.DENIED

    def unpublish(self) -> None:
        if self.status != ListingStatus.PUBLISHED:
            raise ValueError(f"cannot unpublish listing with status {self.status}")
        self.status = ListingStatus.UNPUBLISHED

    def is_published_and_live(self, now: datetime | None = None) -> bool:
        if self.status != ListingStatus.PUBLISHED:
            return False
        try:
            deadline = datetime.strptime(self.deadline, "%Y-%m-%d").date()
        except ValueError:
            return False
        current = (now or datetime.now(timezone.utc)).date()
        return current <= deadline
