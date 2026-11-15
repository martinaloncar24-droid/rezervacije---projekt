from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import reject_null

# Lokacija je ograničena i u bazi (CHECK); ovdje je provjera za jasnu poruku 422
Location = Literal["terasa", "ulica"]


class TableCreate(BaseModel):
    number: int = Field(ge=1)
    capacity: int = Field(ge=1, le=20)
    location: Location


class TableUpdate(BaseModel):
    # PATCH: svako polje je neobavezno, mijenja se samo ono što je poslano
    number: int | None = Field(default=None, ge=1)
    capacity: int | None = Field(default=None, ge=1, le=20)
    location: Location | None = None

    _not_null = field_validator("number", "capacity", "location", mode="before")(
        reject_null
    )


class TableResponse(BaseModel):
    id: int
    number: int
    capacity: int
    location: str

    model_config = {"from_attributes": True}
