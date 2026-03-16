from app.db.base import Base
from app.db.session import engine

# Import models so SQLAlchemy registers them with Base metadata.
from app.models import Asset, GenerationTask, PointsLedger, User  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

