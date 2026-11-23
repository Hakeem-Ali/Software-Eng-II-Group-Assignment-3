"""Job-board scenario JSON API (OpenAPI /docs)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import applications, listings
from app.services import board_auth as auth

router = APIRouter(tags=["job-board"])


def _status_for(error: str | None) -> int:
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


def _fail(result: dict[str, Any]) -> HTTPException:
    return HTTPException(
        status_code=_status_for(result.get("error")),
        detail=result.get("error"),
    )



class LoginBody(BaseModel):
    email: str
    password: str


class ListingBody(BaseModel):
    title: str
    company: str
    description: str
    apply_mode: str = Field(description="external-link | on-platform-collect")
    deadline: str = Field(description="ISO date YYYY-MM-DD")
    external_url: str | None = None
    actor_id: int = Field(description="Acting user id (demo auth)")


class ActorBody(BaseModel):
    actor_id: int


class ApplyBody(BaseModel):
    listing_id: int
    cover_letter: str
    resume_text: str | None = None
    actor_id: int


class TransitionBody(BaseModel):
    action: str = Field(
        description="mark_reviewed | shortlist | reject | hire | reopen"
    )
    actor_id: int


@router.post("/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    user = auth.login(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"user": user}


@router.post("/graduates/subscribe")
def subscribe(body: ActorBody) -> dict[str, Any]:
    result = listings.subscribe(body.actor_id)
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.get("/jobs")
def jobs() -> dict[str, Any]:
    return {"jobs": listings.list_jobs_for_graduates()}


@router.get("/admin/listings/pending")
def pending(actor_id: int) -> dict[str, Any]:
    actor = auth.get_user(actor_id)
    if not actor or actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return {"listings": listings.list_pending_for_admin()}


@router.post("/employer/listings", status_code=201)
def submit_listing(body: ListingBody) -> dict[str, Any]:
    result = listings.submit_listing(
        body.actor_id,
        body.title,
        body.company,
        body.description,
        body.apply_mode,
        body.deadline,
        body.external_url,
    )
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.post("/admin/listings/{listing_id}/publish")
def publish(listing_id: int, body: ActorBody) -> dict[str, Any]:
    result = listings.publish_listing(body.actor_id, listing_id)
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.post("/admin/listings/{listing_id}/notify")
def notify(listing_id: int, body: ActorBody) -> dict[str, Any]:
    result = listings.notify_subscribers(body.actor_id, listing_id)
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.post("/graduates/applications", status_code=201)
def apply(body: ApplyBody) -> dict[str, Any]:
    result = applications.apply(
        body.actor_id, body.listing_id, body.cover_letter, body.resume_text
    )
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.get("/graduates/applications")
def my_apps(actor_id: int) -> dict[str, Any]:
    return {"applications": applications.my_applications(actor_id)}


@router.get("/listings/{listing_id}/applicants")
def applicants(listing_id: int, actor_id: int) -> dict[str, Any]:
    result = applications.listing_applicants(actor_id, listing_id)
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.get("/admin/listings/{listing_id}/export")
def export(listing_id: int, actor_id: int) -> dict[str, Any]:
    result = applications.export_applicants(actor_id, listing_id)
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.post("/applications/{application_id}/transition")
def transition(application_id: int, body: TransitionBody) -> dict[str, Any]:
    result = applications.transition_application(
        body.actor_id, application_id, body.action
    )
    if not result.get("ok"):
        raise _fail(result)
    return result


@router.post("/applications/{application_id}/reopen")
def reopen_application(application_id: int, body: ActorBody) -> dict[str, Any]:
    result = applications.reopen_application(body.actor_id, application_id)
    if not result.get("ok"):
        raise _fail(result)
    return result
