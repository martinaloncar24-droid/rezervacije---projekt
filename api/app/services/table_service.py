import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.dining_table import DiningTable
from app.repositories import table_repo
from app.schemas.table import TableCreate, TableUpdate

logger = logging.getLogger(__name__)


async def get_table_or_404(db: AsyncSession, table_id: int) -> DiningTable:
    table = await table_repo.get_by_id(db, table_id)
    if not table:
        raise AppError("not_found", "Stol nije pronađen", 404)
    return table


async def list_tables(
    db: AsyncSession, location: str | None, limit: int, offset: int
) -> list[DiningTable]:
    return await table_repo.get_all(db, location, limit, offset)


async def create_table(db: AsyncSession, body: TableCreate) -> DiningTable:
    # Provjera unaprijed daje jasnu poruku za uobičajen slučaj
    if await table_repo.get_by_number(db, body.number):
        raise AppError("duplicate", f"Stol broj {body.number} već postoji", 409)
    try:
        table = await table_repo.create(db, DiningTable(**body.model_dump()))
    except IntegrityError:
        # UNIQUE u bazi hvata i dva istodobna zahtjeva koja prođu provjeru
        raise AppError("duplicate", f"Stol broj {body.number} već postoji", 409)
    logger.info("table created: id=%s number=%s", table.id, table.number)
    return table


async def update_table(
    db: AsyncSession, table_id: int, body: TableUpdate
) -> DiningTable:
    table = await get_table_or_404(db, table_id)
    # exclude_unset: u izmjenu ulaze samo polja koja je klijent poslao
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(table, field, value)
    try:
        await db.flush()
    except IntegrityError:
        raise AppError("duplicate", "Stol s tim brojem već postoji", 409)
    return table


async def delete_table(db: AsyncSession, table_id: int) -> None:
    table = await get_table_or_404(db, table_id)
    # Stol s rezervacijama ne smije nestati: rezervacije pokazuju na njega (FOREIGN KEY)
    if await table_repo.has_reservations(db, table_id):
        raise AppError("table_has_reservations", "Stol ima rezervacije", 409)
    await table_repo.delete(db, table)
    logger.info("table deleted: id=%s", table_id)
