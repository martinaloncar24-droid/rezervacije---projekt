from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services import reservation_service

router = APIRouter()


@router.get("/", response_model=list[ReservationResponse])
async def list_reservations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "guest")),
    status: Literal["active", "cancelled", "no_show"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await reservation_service.list_reservations(db, user, status, limit, offset)


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "guest")),
):
    return await reservation_service.get_reservation(db, reservation_id, user)


@router.post("/", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    body: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    # Rezervira gost; restoran ne rezervira sam sebi
    guest: User = Depends(require_role("guest")),
):
    return await reservation_service.create_reservation(db, body, guest)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "guest")),
):
    return await reservation_service.cancel_reservation(db, reservation_id, user)


@router.post("/{reservation_id}/no-show", response_model=ReservationResponse)
async def mark_no_show(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return await reservation_service.mark_no_show(db, reservation_id)
