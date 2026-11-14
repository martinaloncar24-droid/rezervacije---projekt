# Uvoz svih modela registrira ih u Base.metadata.
# autogenerate u Alembicu vidi samo modele koji su ovdje uvezeni.
from app.core.database import Base
from app.models.dining_table import DiningTable
from app.models.reservation import Reservation
from app.models.user import User

__all__ = ["Base", "DiningTable", "Reservation", "User"]
