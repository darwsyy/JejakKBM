from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite dipakai untuk pengembangan lokal agar setup tetap sederhana.
DATABASE_URL = "sqlite:///./jejak_kbm.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """Membuka koneksi database untuk satu request API."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
