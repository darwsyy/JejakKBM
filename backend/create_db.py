from app.database import Base, engine
from app import models  # noqa: F401 - memastikan model User terdaftar

Base.metadata.create_all(bind=engine)

print("Database berhasil disiapkan.")
print("Tabel yang tersedia:", ", ".join(Base.metadata.tables.keys()))
