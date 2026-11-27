"""Shared mapping from service error messages to HTTP responses."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def status_for(error: str | None) -> int:
    """Map a service error message to the right HTTP status code."""
    e = (error or "").lower()
    if "not found" in e:
        return 404
    if "unknown user" in e:
        return 401
    if (
        "admin only" in e
        or "admin reopen only" in e
        or "forbidden" in e
        or "only the listing employer" in e
        or "graduates only" in e
        or "employers only" in e
        or "only dcit" in e
    ):
        return 403
    if (
        "illegal" in e
        or "already submitted" in e
        or "not open" in e
        or "do not collect" in e
        or "cannot " in e
    ):
        return 409
    if (
        "use the admin reopen" in e
        or "unknown application action" in e
        or "apply_mode must" in e
        or "external_url required" in e
    ):
        return 422
    return 400


def fail(result: dict[str, Any]) -> HTTPException:
    """Turn a failed service result into an HTTPException."""
    return HTTPException(
        status_code=status_for(result.get("error")),
        detail=result.get("error"),
    )
