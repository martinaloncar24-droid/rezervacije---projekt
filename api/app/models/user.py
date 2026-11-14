from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.reservation import Reservation


class User(Base):
    __tablename__ = "users"
    # Skup uloga provodi baza, pa ni upis mimo aplikacije ne prolazi s krivom ulogom
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'guest')", name="ck_user_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Korisničko ime je e-mail; dva računa ne smiju imati isto
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Čuva se samo hash lozinke, nikad sama lozinka
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Deaktiviran račun ne prolazi prijavu
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    # 1:N: jedan gost ima više rezervacija
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")
