from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str = Field(exclude=True, repr=False)
    role: str = ""
    programme: Optional[str] = None
    field_preference: Optional[str] = None
    resume_text: Optional[str] = None


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    def is_eligible_graduate(self) -> bool:
        return self.role == "graduate" and self.programme == "DCIT"

    def model_dump(self, *args, **kwargs):
        kwargs["exclude"] = set(kwargs.get("exclude") or ()) | {"password"}
        return super().model_dump(*args, **kwargs)
