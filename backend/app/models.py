from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
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


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    nip: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClassOfficerPeriod(Base):
    __tablename__ = "class_officer_periods"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_date: Mapped[object] = mapped_column(Date, nullable=False)
    end_date: Mapped[object | None] = mapped_column(Date, nullable=True)


class DailyJournal(Base):
    __tablename__ = "daily_journals"
    __table_args__ = (
        UniqueConstraint("class_id", "journal_date", name="unique_class_journal_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    journal_date: Mapped[object] = mapped_column(Date, nullable=False)
    officer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)


class JournalSession(Base):
    __tablename__ = "journal_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey("daily_journals.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    material: Mapped[str] = mapped_column(String(1000), nullable=False)
    actual_start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    actual_end_time: Mapped[str] = mapped_column(String(5), nullable=False)


class JournalSessionSlot(Base):
    __tablename__ = "journal_session_slots"
    __table_args__ = (
        UniqueConstraint("session_id", "slot_id", name="unique_session_schedule_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("journal_sessions.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("schedule_slots.id"), nullable=False)
