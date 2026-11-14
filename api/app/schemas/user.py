from pydantic import BaseModel


class UserResponse(BaseModel):
    # password_hash namjerno nije ovdje: polje kojeg nema u shemi ne može izaći
    id: int
    username: str
    role: str
    is_active: bool

    # Dopušta čitanje iz SQLAlchemy objekta (user.id, user.username...)
    model_config = {"from_attributes": True}
