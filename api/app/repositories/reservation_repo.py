from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reservation import Reservation


async def get_by_id(db: AsyncSession, reservation_id: int) -> Reservation | None:
    # Stol se dohvaća unaprijed: u asinkronom radu lijeno učitavanje
    # reservation.table podiže iznimku tek pri popunjavanju odgovora
    stmt = (
        select(Reservation)
        .options(selectinload(Reservation.table))
        .where(Reservation.id == reservation_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_reservations(
    db: AsyncSession,
    user_id: int | None,
    status: str | None,
    limit: int,
    offset: int,
) -> list[Reservation]:
    # selectinload: dva upita ukupno (rezervacije + njihovi stolovi),
    # a ne po jedan upit za stol svake rezervacije (problem N+1)
    stmt = select(Reservation).options(selectinload(Reservation.table))
    if user_id is not None:
        # Sužavanje u upitu: tuđe rezervacije ni ne izlaze iz baze
        stmt = stmt.where(Reservation.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Reservation.status == status)
    stmt = stmt.order_by(Reservation.start_time, Reservation.id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_overlapping(
    db: AsyncSession, table_id: int, window_start: datetime, window_end: datetime
) -> Reservation | None:
    """Aktivna rezervacija istoga stola koja počinje unutar zadanog prozora."""
    stmt = (
        select(Reservation)
        .where(
            Reservation.table_id == table_id,
            Reservation.status == "active",
            Reservation.start_time > window_start,
            Reservation.start_time < window_end,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(db: AsyncSession, reservation: Reservation) -> Reservation:
    db.add(reservation)
    await db.flush()
    return reservation
