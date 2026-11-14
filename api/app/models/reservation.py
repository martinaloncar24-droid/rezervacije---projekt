import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dining_table import DiningTable
    from app.models.user import User


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("guests > 0", name="ck_reservation_guests"),
        CheckConstraint(
            "status IN ('active', 'cancelled', 'no_show')",
            name="ck_reservation_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Strani ključevi: rezervacija pripada jednom gostu i jednom stolu.
    # index=True jer se rezervacije često traže po gostu i po stolu
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(
        ForeignKey("dining_tables.id"), nullable=False, index=True
    )
    # timestamptz: trenutak na vremenskoj osi, neovisno o vremenskoj zoni čitatelja
    start_time: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    guests: Mapped[int] = mapped_column(Integer, nullable=False)
    # Otkazana rezervacija se ne briše nego mijenja status, pa ostaje trag
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    # Vrijeme upisa daje baza, pa ne ovisi o satu poslužitelja
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="reservations")
    table: Mapped["DiningTable"] = relationship(back_populates="reservations")
