from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite dipakai untuk pengembangan lokal agar setup tetap sederhana.
DATABASE_URL = "sqlite:///./jejak_kbm.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    """Aktifkan pemeriksaan relasi agar data terkait tidak terhapus sembarangan."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
