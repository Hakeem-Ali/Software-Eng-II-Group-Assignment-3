from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import StrEnum
from typing import FrozenSet, Optional

from sqlmodel import Field, SQLModel


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class ApplicationAction(StrEnum):
    MARK_REVIEWED = "mark_reviewed"
    SHORTLIST = "shortlist"
    REJECT = "reject"
    HIRE = "hire"
    REOPEN = "reopen"


class IllegalTransitionError(ValueError):
    pass


class UnauthorizedTransitionError(PermissionError):
    pass


class ApplicationState(ABC):
    @abstractmethod
    def name(self) -> ApplicationStatus:
        raise NotImplementedError

    @abstractmethod
    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        raise NotImplementedError

    @abstractmethod
    def handle(self, action: ApplicationAction) -> "ApplicationState":
        raise NotImplementedError

    def is_active(self) -> bool:
        return True


class SubmittedState(ApplicationState):
    def name(self) -> ApplicationStatus:
        return ApplicationStatus.SUBMITTED

    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        return frozenset({ApplicationAction.MARK_REVIEWED})

    def handle(self, action: ApplicationAction) -> ApplicationState:
        if action == ApplicationAction.MARK_REVIEWED:
            return ReviewedState()
        raise IllegalTransitionError(f"{action} is illegal from submitted")


class ReviewedState(ApplicationState):
    def name(self) -> ApplicationStatus:
        return ApplicationStatus.REVIEWED

    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        return frozenset({ApplicationAction.SHORTLIST, ApplicationAction.REJECT})

    def handle(self, action: ApplicationAction) -> ApplicationState:
        if action == ApplicationAction.SHORTLIST:
            return ShortlistedState()
        if action == ApplicationAction.REJECT:
            return RejectedState()
        raise IllegalTransitionError(f"{action} is illegal from reviewed")


class ShortlistedState(ApplicationState):
    def name(self) -> ApplicationStatus:
        return ApplicationStatus.SHORTLISTED

    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        return frozenset({ApplicationAction.HIRE, ApplicationAction.REJECT})

    def handle(self, action: ApplicationAction) -> ApplicationState:
        if action == ApplicationAction.HIRE:
            return HiredState()
        if action == ApplicationAction.REJECT:
            return RejectedState()
        raise IllegalTransitionError(f"{action} is illegal from shortlisted")


class RejectedState(ApplicationState):
    def name(self) -> ApplicationStatus:
        return ApplicationStatus.REJECTED

    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        return frozenset({ApplicationAction.REOPEN})

    def handle(self, action: ApplicationAction) -> ApplicationState:
        if action == ApplicationAction.REOPEN:
            return ReviewedState()
        raise IllegalTransitionError(f"{action} is illegal from rejected")

    def is_active(self) -> bool:
        return False


class HiredState(ApplicationState):
    def name(self) -> ApplicationStatus:
        return ApplicationStatus.HIRED

    def allowed_actions(self) -> FrozenSet[ApplicationAction]:
        return frozenset()

    def handle(self, action: ApplicationAction) -> ApplicationState:
        raise IllegalTransitionError(f"{action} is illegal from terminal hired")

    def is_active(self) -> bool:
        return False


class StateFactory:
    @staticmethod
    def from_status(status: str | ApplicationStatus) -> ApplicationState:
        try:
            canonical = ApplicationStatus(status)
        except ValueError as exc:
            raise IllegalTransitionError(f"unknown application status {status!r}") from exc
        return {
            ApplicationStatus.SUBMITTED: SubmittedState,
            ApplicationStatus.REVIEWED: ReviewedState,
            ApplicationStatus.SHORTLISTED: ShortlistedState,
            ApplicationStatus.REJECTED: RejectedState,
            ApplicationStatus.HIRED: HiredState,
        }[canonical]()


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    graduate_id: int = Field(foreign_key="user.id", index=True)
    cover_letter: str
    resume_text: str
    status: ApplicationStatus = Field(default=ApplicationStatus.SUBMITTED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        self.status = ApplicationStatus(data.get("status", ApplicationStatus.SUBMITTED))

    def current_state(self) -> ApplicationState:
        return StateFactory.from_status(self.status)

    def apply(self, action: str | ApplicationAction) -> str:
        try:
            parsed = ApplicationAction(action)
        except ValueError as exc:
            raise IllegalTransitionError(f"unknown application action {action!r}") from exc
        next_state = self.current_state().handle(parsed)
        self.status = next_state.name()
        return str(next_state.name())

    def is_active(self) -> bool:
        return self.current_state().is_active()


class ApplicationHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    action: ApplicationAction
    actor_id: int = Field(foreign_key="user.id", index=True)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
