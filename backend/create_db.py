from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  


Base.metadata.create_all(bind=engine)

# create_all membuat tabel baru, tetapi tidak menambah kolom pada tabel lama.
# Penyesuaian kecil ini menjaga database SQLite yang sudah dipakai tetap bisa digunakan.
user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
with engine.begin() as connection:
    connection.execute(text("DROP TABLE IF EXISTS teacher_absence_reports"))
    if "password_hash" not in user_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
    if "token_version" not in user_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")
        )

print("Database berhasil disiapkan.")
print("Tabel yang tersedia:", ", ".join(Base.metadata.tables.keys()))
