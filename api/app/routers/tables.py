from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.table import TableCreate, TableResponse, TableUpdate
from app.services import table_service

router = APIRouter()


@router.get("/", response_model=list[TableResponse])
async def list_tables(
    db: AsyncSession = Depends(get_db),
    # Popis stolova vidi svaki prijavljeni korisnik: gost bira stol za rezervaciju
    user: User = Depends(get_current_user),
    location: Literal["terasa", "ulica"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await table_service.list_tables(db, location, limit, offset)


@router.get("/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await table_service.get_table_or_404(db, table_id)


@router.post("/", response_model=TableResponse, status_code=201)
async def create_table(
    body: TableCreate,
    db: AsyncSession = Depends(get_db),
    # Stolove dodaje samo restoran; gost dobiva 403
    admin: User = Depends(require_role("admin")),
):
    return await table_service.create_table(db, body)


@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: int,
    body: TableUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return await table_service.update_table(db, table_id, body)


@router.delete("/{table_id}", status_code=204)
async def delete_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    await table_service.delete_table(db, table_id)
