"""Notification endpoints for graduates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies.services import get_notification_service
from app.routers.errors import fail
from app.services.notifications import NotificationService

router = APIRouter(tags=["job-board"])


@router.get("/notifications")
def list_notifications(
    actor_id: int,
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    result = service.list_notifications(actor_id)
    if not result.get("ok"):
        raise fail(result)
    return result
