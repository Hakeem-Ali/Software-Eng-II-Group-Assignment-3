from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ExportAudit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    admin_id: int = Field(foreign_key="user.id", index=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    applicant_count: int
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
