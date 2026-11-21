"""Application lifecycle state machine and authorization policies."""

from __future__ import annotations

from typing import Any

from app.models.application import (
    ApplicationAction,
    IllegalTransitionError,
    StateFactory,
)

ACTIONS = tuple(action.value for action in ApplicationAction)


def snapshot(app: dict[str, Any]) -> dict[str, Any]:
    return {"id": app["id"], "status": app["status"]}


def apply_action(app: dict[str, Any], action: str) -> dict[str, Any]:
    try:
        parsed_action = ApplicationAction(action)
        old_status = str(app["status"])
        new_status = StateFactory.from_status(old_status).handle(parsed_action).name()
    except (IllegalTransitionError, ValueError, KeyError) as exc:
        return {"ok": False, "error": str(exc)}
    updated = dict(app)
    updated["status"] = str(new_status)
    return {
        "ok": True,
        "application": snapshot(updated),
        "row": updated,
        "changed": old_status != str(new_status),
    }


def derived_status_from_flags(app: dict[str, Any]) -> str:
    """Deprecated compatibility reader; status is the only source of truth."""
    return str(app["status"])


class ListingOwnerPolicy:
    @staticmethod
    def can_advance(actor: dict[str, Any], listing: Any) -> bool:
        return (
            actor.get("role") == "employer"
            and listing is not None
            and actor.get("id") == listing.employer_id
        )

    @staticmethod
    def can_read(actor: dict[str, Any], listing: Any) -> bool:
        return ListingOwnerPolicy.can_advance(actor, listing)


class ReopenPolicy:
    @staticmethod
    def can_reopen(actor: dict[str, Any]) -> bool:
        return actor.get("role") == "admin"
