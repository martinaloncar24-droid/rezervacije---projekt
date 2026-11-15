from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field


class ReservationCreate(BaseModel):
    table_id: int
    # AwareDatetime: vrijeme mora nositi zonu (npr. 2026-12-20T19:00:00+01:00),
    # inače se ne zna o kojem je trenutku riječ
    start_time: AwareDatetime
    guests: int = Field(ge=1, le=20)


class TableBrief(BaseModel):
    """Suženi stol unutar odgovora o rezervaciji: samo ono što popis treba."""

    number: int
    location: str

    model_config = {"from_attributes": True}


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    table_id: int
    start_time: datetime
    guests: int
    status: str
    created_at: datetime
    table: TableBrief

    model_config = {"from_attributes": True}
