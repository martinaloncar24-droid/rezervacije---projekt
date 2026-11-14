from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.reservation import Reservation


class DiningTable(Base):
    # Ne "tables": TABLE je rezervirana riječ u SQL-u
    __tablename__ = "dining_tables"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_table_capacity"),
        CheckConstraint("location IN ('terasa', 'ulica')", name="ck_table_location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Broj stola kakav piše na stolu u restoranu; ne smiju postojati dva ista
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(20), nullable=False)

    # 1:N: jedan stol ima više rezervacija
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="table")
