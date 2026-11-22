from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
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


class ScheduleTeacherAssignment(Base):
    __tablename__ = "schedule_teacher_assignments"

    # Satu slot hanya memiliki satu guru pengajar.
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_slots.id"),
        primary_key=True,
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint(
            "class_id", "day_of_week", "slot_order",
            name="unique_class_day_slot_order",
        ),
        UniqueConstraint(
            "class_id", "day_of_week", "jp_number",
            name="unique_class_day_jp",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id"),
        nullable=False,
    )
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    slot_order: Mapped[int] = mapped_column(nullable=False)
    jp_number: Mapped[int | None] = mapped_column(nullable=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    slot_type: Mapped[str] = mapped_column(String(20), nullable=False)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class ScheduleSubjectAssignment(Base):
    __tablename__ = "schedule_subject_assignments"

    # Satu slot pelajaran hanya memiliki satu mata pelajaran.
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_slots.id"),
        primary_key=True,
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id"),
        nullable=False,
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nis: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
