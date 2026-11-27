"""Subscription endpoints for graduates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies.services import get_listing_service
from app.routers.board import ActorBody
from app.routers.errors import fail
from app.services.listings import ListingService

router = APIRouter(tags=["job-board"])


@router.post("/graduates/unsubscribe")
def unsubscribe(
    body: ActorBody,
    service: ListingService = Depends(get_listing_service),
) -> dict[str, Any]:
    result = service.unsubscribe(body.actor_id)
    if not result.get("ok"):
        raise fail(result)
    return result
