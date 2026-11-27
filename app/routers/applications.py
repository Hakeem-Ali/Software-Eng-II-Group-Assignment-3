"""Application read endpoints: one application, its history, and my active list."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies.services import get_application_service
from app.routers.errors import fail
from app.services.applications import ApplicationService

router = APIRouter(tags=["job-board"])


@router.get("/graduates/applications/active")
def my_active_applications(
    actor_id: int,
    service: ApplicationService = Depends(get_application_service),
) -> dict[str, Any]:
    result = service.my_active_applications(actor_id)
    if not result.get("ok"):
        raise fail(result)
    return result


@router.get("/applications/{application_id}")
def read_application(
    application_id: int,
    actor_id: int,
    service: ApplicationService = Depends(get_application_service),
) -> dict[str, Any]:
    result = service.read_application(actor_id, application_id)
    if not result.get("ok"):
        raise fail(result)
    return result


@router.get("/applications/{application_id}/history")
def application_history(
    application_id: int,
    actor_id: int,
    service: ApplicationService = Depends(get_application_service),
) -> dict[str, Any]:
    result = service.application_history(actor_id, application_id)
    if not result.get("ok"):
        raise fail(result)
    return result
