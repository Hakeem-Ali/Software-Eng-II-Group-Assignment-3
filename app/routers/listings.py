"""Listing endpoints: employer's own listings, job detail, deny and unpublish."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies.services import get_listing_service
from app.routers.board import ActorBody
from app.routers.errors import fail
from app.services.listings import ListingService

router = APIRouter(tags=["job-board"])


@router.get("/employer/listings")
def employer_listings(
    actor_id: int,
    service: ListingService = Depends(get_listing_service),
) -> dict[str, Any]:
    result = service.employer_listings(actor_id)
    if not result.get("ok"):
        raise fail(result)
    return result


@router.get("/jobs/{listing_id}")
def job_detail(
    listing_id: int,
    actor_id: int,
    service: ListingService = Depends(get_listing_service),
) -> dict[str, Any]:
    result = service.get_job(actor_id, listing_id)
    if not result.get("ok"):
        raise fail(result)
    return result


@router.post("/admin/listings/{listing_id}/deny")
def deny_listing(
    listing_id: int,
    body: ActorBody,
    service: ListingService = Depends(get_listing_service),
) -> dict[str, Any]:
    result = service.deny_listing(body.actor_id, listing_id)
    if not result.get("ok"):
        raise fail(result)
    return result


@router.post("/admin/listings/{listing_id}/unpublish")
def unpublish_listing(
    listing_id: int,
    body: ActorBody,
    service: ListingService = Depends(get_listing_service),
) -> dict[str, Any]:
    result = service.unpublish_listing(body.actor_id, listing_id)
    if not result.get("ok"):
        raise fail(result)
    return result
