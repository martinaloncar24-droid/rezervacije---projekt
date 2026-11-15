"""Zajednička testna infrastruktura.

Testovi rade nad zasebnom bazom rezervacije_test na istom PostgreSQL
poslužitelju, pa razvojni podatci u bazi rezervacije ostaju netaknuti.
Prije pokretanja: docker compose up -d db
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.deps import get_db
from app.main import create_app
from app.models import Base, DiningTable, Reservation, User


def _test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    url = make_url(settings.DATABASE_URL)
    url = url.set(database=f"{url.database}_test")
    return url.render_as_string(hide_password=False)


TEST_DATABASE_URL = _test_database_url()

# NullPool: svaki test ima svoju petlju događaja, pa veze ne smiju preživjeti test
engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def _prepare_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    server = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with server.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await server.dispose()

    # Shema iz modela, svaki put iznova
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    asyncio.run(_prepare_database())


@pytest.fixture(autouse=True)
async def clean_tables():
    """Svaki test počinje od praznih tablica."""
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP klijent nad aplikacijom, bez pokretanja poslužitelja."""
    app = create_app()
    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Sesija za pripremu podataka izravno u bazi."""
    async with TestSessionLocal() as session:
        yield session


def fast_hash(password: str) -> str:
    # Faktor rada 4 umjesto zadanih 12: hash je jednako valjan, a testovi brži
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


async def auth_header(client: AsyncClient, username: str, password: str) -> dict:
    resp = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _add_user(db, username, password, role, is_active=True) -> User:
    user = User(
        username=username,
        password_hash=fast_hash(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Restoran: testadmin / admin123."""
    return await _add_user(db, "testadmin", "admin123", "admin")


@pytest.fixture
async def guest(db: AsyncSession) -> User:
    """Gost: gost / gost1234."""
    return await _add_user(db, "gost", "gost1234", "guest")


@pytest.fixture
async def other_guest(db: AsyncSession) -> User:
    """Drugi gost, za provjere vlasništva: drugi / drugi123."""
    return await _add_user(db, "drugi", "drugi123", "guest")


@pytest.fixture
async def inactive_user(db: AsyncSession) -> User:
    """Deaktiviran račun: neaktivan / pass1234."""
    return await _add_user(db, "neaktivan", "pass1234", "guest", is_active=False)


@pytest.fixture
async def table(db: AsyncSession) -> DiningTable:
    """Stol broj 1 na terasi, za 4 osobe."""
    table = DiningTable(number=1, capacity=4, location="terasa")
    db.add(table)
    await db.commit()
    return table


# Stalno vrijeme dolaska u testovima: 20.12.2026. u 19:00 UTC
START = datetime(2026, 12, 20, 19, 0, tzinfo=timezone.utc)


async def add_reservation(
    db: AsyncSession,
    user: User,
    table: DiningTable,
    start_time: datetime = START,
    guests: int = 2,
    status: str = "active",
) -> Reservation:
    """Rezervacija upisana izravno u bazu, mimo API-ja."""
    reservation = Reservation(
        user_id=user.id,
        table_id=table.id,
        start_time=start_time,
        guests=guests,
        status=status,
    )
    db.add(reservation)
    await db.commit()
    return reservation
