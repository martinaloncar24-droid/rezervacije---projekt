from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dining_table import DiningTable
from app.models.reservation import Reservation


async def get_by_id(db: AsyncSession, table_id: int) -> DiningTable | None:
    return await db.get(DiningTable, table_id)


async def get_by_number(db: AsyncSession, number: int) -> DiningTable | None:
    result = await db.execute(select(DiningTable).where(DiningTable.number == number))
    return result.scalar_one_or_none()


async def get_all(
    db: AsyncSession, location: str | None, limit: int, offset: int
) -> list[DiningTable]:
    stmt = select(DiningTable)
    if location is not None:
        stmt = stmt.where(DiningTable.location == location)
    # order_by: bez njega redoslijed nije zajamčen, pa straničenje ne bi bilo stabilno
    stmt = stmt.order_by(DiningTable.number).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def has_reservations(db: AsyncSession, table_id: int) -> bool:
    stmt = select(Reservation.id).where(Reservation.table_id == table_id).limit(1)
    result = await db.execute(stmt)
    return result.first() is not None


async def create(db: AsyncSession, table: DiningTable) -> DiningTable:
    db.add(table)
    # flush, ne commit: transakciju potvrđuje get_db kad cijeli zahtjev prođe
    await db.flush()
    return table


async def delete(db: AsyncSession, table: DiningTable) -> None:
    await db.delete(table)
    await db.flush()
