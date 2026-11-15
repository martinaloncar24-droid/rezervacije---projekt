import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.reservation import Reservation
from app.models.user import User
from app.repositories import reservation_repo
from app.schemas.reservation import ReservationCreate
from app.services.table_service import get_table_or_404

logger = logging.getLogger(__name__)

# Poslovna pravila restorana Tinel na jednom mjestu
RESERVATION_DURATION = timedelta(hours=2)  # koliko gost sjedi za stolom
CANCEL_DEADLINE = timedelta(hours=2)  # otkazivanje najkasnije 2 h prije
NO_SHOW_GRACE = timedelta(minutes=30)  # stol se drži 30 min nakon dogovorenog


def _now() -> datetime:
    # Sat se čita na jednom mjestu; testovi ga "zamrzavaju" (freezegun)
    return datetime.now(timezone.utc)


def _check_owner(reservation: Reservation, current_user: User) -> None:
    # Vlasništvo: gost smije samo do svojih rezervacija, admin do svih
    if current_user.role == "guest" and reservation.user_id != current_user.id:
        raise AppError("forbidden", "Rezervacija ne pripada vama", 403)


def _check_active(reservation: Reservation) -> None:
    if reservation.status != "active":
        # Prijelaz je moguć samo iz stanja active; ponovljeni zahtjev se odbija
        raise AppError("not_active", "Rezervacija više nije aktivna", 400)


async def get_reservation(
    db: AsyncSession, reservation_id: int, current_user: User
) -> Reservation:
    # Prvo postoji li zapis (404), tek onda smije li ga pošiljatelj vidjeti (403)
    reservation = await reservation_repo.get_by_id(db, reservation_id)
    if not reservation:
        raise AppError("not_found", "Rezervacija nije pronađena", 404)
    _check_owner(reservation, current_user)
    return reservation


async def list_reservations(
    db: AsyncSession, current_user: User, status: str | None, limit: int, offset: int
) -> list[Reservation]:
    # Popis ne imenuje nijedan zapis, pa se gostu ne odbija nego sužava na njegove
    user_id = current_user.id if current_user.role == "guest" else None
    return await reservation_repo.list_reservations(db, user_id, status, limit, offset)


async def create_reservation(
    db: AsyncSession, body: ReservationCreate, current_user: User
) -> Reservation:
    table = await get_table_or_404(db, body.table_id)

    # Pravilo: rezervacija mora biti u budućnosti
    if body.start_time <= _now():
        raise AppError("start_in_past", "Vrijeme rezervacije je prošlo", 400)

    # Pravilo: kapacitet stola
    if body.guests > table.capacity:
        raise AppError(
            "over_capacity",
            f"Stol {table.number} ima {table.capacity} mjesta, a traženo je "
            f"{body.guests}",
            400,
        )

    # Pravilo: isti stol ne smije imati dvije aktivne rezervacije koje se preklapaju.
    # Svaka traje 2 h, pa se preklapaju ako im početci nisu barem 2 h razmaknuti
    overlap = await reservation_repo.find_overlapping(
        db,
        table.id,
        body.start_time - RESERVATION_DURATION,
        body.start_time + RESERVATION_DURATION,
    )
    if overlap:
        raise AppError("table_taken", "Stol je u tom terminu već rezerviran", 409)

    # Gost rezervira za sebe: user_id dolazi iz tokena, ne iz tijela zahtjeva
    reservation = Reservation(
        user_id=current_user.id,
        table=table,
        start_time=body.start_time,
        guests=body.guests,
    )
    reservation = await reservation_repo.create(db, reservation)
    logger.info("reservation created: id=%s table=%s", reservation.id, table.number)
    return reservation


async def cancel_reservation(
    db: AsyncSession, reservation_id: int, current_user: User
) -> Reservation:
    reservation = await get_reservation(db, reservation_id, current_user)
    _check_active(reservation)

    # Pravilo: gost otkazuje prije isteka roka (2 h prije dolaska); restoran uvijek.
    # Uvjet je strog: u samom trenutku roka otkazivanje više nije moguće
    deadline = reservation.start_time - CANCEL_DEADLINE
    if current_user.role == "guest" and not _now() < deadline:
        raise AppError(
            "cancel_deadline_passed",
            "Rezervacija se može otkazati najkasnije 2 sata prije dolaska",
            400,
        )

    reservation.status = "cancelled"
    await db.flush()
    logger.info("reservation cancelled: id=%s", reservation.id)
    return reservation


async def mark_no_show(db: AsyncSession, reservation_id: int) -> Reservation:
    # Samo admin dolazi ovdje (require_role u ruti), pa vlasništvo ne treba provjeravati
    reservation = await reservation_repo.get_by_id(db, reservation_id)
    if not reservation:
        raise AppError("not_found", "Rezervacija nije pronađena", 404)
    _check_active(reservation)

    # Pravilo: stol se drži 30 min; od tog trenutka gost se smije označiti kao nedošao
    if _now() < reservation.start_time + NO_SHOW_GRACE:
        raise AppError(
            "too_early",
            "Gost se može označiti kao nedošao tek 30 minuta nakon dogovorenog vremena",
            400,
        )

    reservation.status = "no_show"
    await db.flush()
    logger.info("reservation no-show: id=%s", reservation.id)
    return reservation
