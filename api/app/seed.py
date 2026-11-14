"""Početni podatci za razvoj i obranu.

Pokreće se iz mape api/, nakon alembic upgrade head:
    python -m app.seed

Smije se pokrenuti bilo koliko puta: što već postoji, ne stvara se ponovno
(idempotentna skripta).
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models import DiningTable, Reservation, User

# Polja: korisničko ime, lozinka, uloga
DEMO_USERS = [
    ("admin@tinel.hr", "admin123", "admin"),
    ("ana@tinel.hr", "ana12345", "guest"),
    ("marko@tinel.hr", "marko123", "guest"),
]

# Stolovi restorana Tinel; polja: broj stola, kapacitet, lokacija
DEMO_TABLES = [
    (1, 2, "terasa"),
    (2, 4, "terasa"),
    (3, 6, "terasa"),
    (4, 2, "ulica"),
    (5, 4, "ulica"),
]

# Primjer rezervacije: Ana, stol 2, 20.12.2026. u 19:00 po srednjoeuropskom vremenu
CET = timezone(timedelta(hours=1))
DEMO_RESERVATION = {
    "username": "ana@tinel.hr",
    "table_number": 2,
    "start_time": datetime(2026, 12, 20, 19, 0, tzinfo=CET),
    "guests": 3,
}


async def get_or_create_user(
    session: AsyncSession, username: str, password: str, role: str
) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        # U bazu ide samo hash lozinke
        user = User(username=username, password_hash=hash_password(password), role=role)
        session.add(user)
        # flush šalje upis prije commita, da korisnik dobije id
        await session.flush()
    return user


async def get_or_create_table(
    session: AsyncSession, number: int, capacity: int, location: str
) -> DiningTable:
    result = await session.execute(
        select(DiningTable).where(DiningTable.number == number)
    )
    table = result.scalar_one_or_none()
    if table is None:
        table = DiningTable(number=number, capacity=capacity, location=location)
        session.add(table)
        await session.flush()
    return table


async def get_or_create_reservation(
    session: AsyncSession, user: User, table: DiningTable, start_time, guests: int
) -> Reservation:
    result = await session.execute(
        select(Reservation).where(
            Reservation.table_id == table.id, Reservation.start_time == start_time
        )
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        reservation = Reservation(
            user_id=user.id, table_id=table.id, start_time=start_time, guests=guests
        )
        session.add(reservation)
        await session.flush()
    return reservation


async def seed() -> None:
    # Jedna transakcija: ili su svi retci upisani, ili nijedan
    async with AsyncSessionLocal() as session, session.begin():
        users = {}
        for username, password, role in DEMO_USERS:
            users[username] = await get_or_create_user(
                session, username, password, role
            )

        tables = {}
        for number, capacity, location in DEMO_TABLES:
            tables[number] = await get_or_create_table(
                session, number, capacity, location
            )

        await get_or_create_reservation(
            session,
            users[DEMO_RESERVATION["username"]],
            tables[DEMO_RESERVATION["table_number"]],
            DEMO_RESERVATION["start_time"],
            DEMO_RESERVATION["guests"],
        )

    await engine.dispose()
    print("Seed gotov.")
    for username, password, role in DEMO_USERS:
        print(f"  {role}: {username} / {password}")
    print(f"  stolova: {len(DEMO_TABLES)}, primjer rezervacije: 1")


if __name__ == "__main__":
    asyncio.run(seed())
