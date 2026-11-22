from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Classroom(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)


class ClassOfficerAssignment(Base):
    __tablename__ = "class_officer_assignments"

    # class_id sebagai primary key: satu kelas hanya punya satu petugas utama.
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id"),
        primary_key=True,
    )
    # unique=True: satu petugas hanya boleh ditugaskan ke satu kelas.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
