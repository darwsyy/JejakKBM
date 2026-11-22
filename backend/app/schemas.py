from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    role: Literal["admin", "class_officer", "teacher"]


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    academic_year: str = Field(min_length=4, max_length=20)


class ClassroomResponse(BaseModel):
    id: int
    name: str
    academic_year: str

    model_config = ConfigDict(from_attributes=True)


class ClassOfficerResponse(BaseModel):
    class_id: int
    class_name: str
    user_id: int
    username: str
    full_name: str


class ScheduleSlotData(BaseModel):
    day_of_week: Literal[
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    slot_order: int = Field(ge=1)
    jp_number: int | None = Field(default=None, ge=1)
    start_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    slot_type: Literal[
        "LESSON", "ASSEMBLY", "COCURRICULAR",
        "BREAK", "FREE", "SPECIAL_EVENT",
    ]

    @model_validator(mode="after")
    def validate_schedule_time(self):
        start = datetime.strptime(self.start_time, "%H:%M")
        end = datetime.strptime(self.end_time, "%H:%M")

        if end <= start:
            raise ValueError("Jam selesai harus setelah jam mulai.")

        if self.jp_number is not None:
            duration = (end - start).total_seconds() / 60
            if duration != 45:
                raise ValueError("Slot yang memiliki nomor JP harus berdurasi 45 menit.")

        return self


class ScheduleSlotCreate(ScheduleSlotData):
    pass


class ScheduleSlotUpdate(ScheduleSlotData):
    pass


class ScheduleTeacherResponse(BaseModel):
    slot_id: int
    teacher_id: int
    teacher_name: str
    username: str


class ScheduleSlotResponse(ScheduleSlotData):
    id: int
    class_id: int

    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class SubjectResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleSubjectResponse(BaseModel):
    slot_id: int
    subject_id: int
    subject_name: str


class StudentCreate(BaseModel):
    nis: str = Field(min_length=1, max_length=20)
    full_name: str = Field(min_length=2, max_length=100)
    class_id: int = Field(ge=1)


class StudentUpdate(BaseModel):
    nis: str = Field(min_length=1, max_length=20)
    full_name: str = Field(min_length=2, max_length=100)
    class_id: int = Field(ge=1)


class StudentResponse(BaseModel):
    id: int
    nis: str
    full_name: str
    class_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TeacherCreate(BaseModel):
    user_id: int = Field(ge=1)
    nip: str | None = Field(default=None, max_length=30)


class TeacherUpdate(BaseModel):
    nip: str | None = Field(default=None, max_length=30)


class TeacherResponse(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: str
    nip: str | None
    is_active: bool


class ClassOfficerPeriodCreate(BaseModel):
    user_id: int = Field(ge=1)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("Tanggal akhir tidak boleh sebelum tanggal mulai.")
        return self


class ClassOfficerPeriodResponse(BaseModel):
    id: int
    class_id: int
    class_name: str
    user_id: int
    username: str
    full_name: str
    start_date: date
    end_date: date | None


class DailyJournalCreate(BaseModel):
    class_id: int = Field(ge=1)
    journal_date: date
    officer_user_id: int = Field(ge=1)


class DailyJournalResponse(BaseModel):
    id: int
    class_id: int
    journal_date: date
    officer_user_id: int
    status: Literal["DRAFT", "SUBMITTED", "UNDER_REVIEW", "REVISION_REQUIRED", "RESUBMITTED", "APPROVED"]

    model_config = ConfigDict(from_attributes=True)


class JournalSessionCreate(BaseModel):
    slot_ids: list[int] = Field(min_length=1)
    teacher_id: int = Field(ge=1)
    material: str = Field(min_length=3, max_length=1000)
    actual_start_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    actual_end_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")

    @model_validator(mode="after")
    def validate_actual_time(self):
        start = datetime.strptime(self.actual_start_time, "%H:%M")
        end = datetime.strptime(self.actual_end_time, "%H:%M")
        if end <= start:
            raise ValueError("Waktu selesai harus setelah waktu mulai.")
        if len(set(self.slot_ids)) != len(self.slot_ids):
            raise ValueError("JP yang sama tidak boleh dipilih lebih dari sekali.")
        return self


class JournalSessionResponse(BaseModel):
    id: int
    journal_id: int
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_name: str
    slot_ids: list[int]
    jp_numbers: list[int]
    material: str
    actual_start_time: str
    actual_end_time: str


class AttendanceCreate(BaseModel):
    slot_id: int = Field(ge=1)
    student_id: int = Field(ge=1)
    teacher_id: int = Field(ge=1)
    attendance_status: Literal["PRESENT", "SICK", "PERMITTED", "ABSENT"]


class AttendanceResponse(BaseModel):
    id: int
    session_id: int
    slot_id: int
    jp_number: int
    student_id: int
    student_name: str
    teacher_id: int
    teacher_name: str
    attendance_status: Literal["PRESENT", "SICK", "PERMITTED", "ABSENT"]
    recorded_at: datetime


class AttendanceBatchItem(BaseModel):
    student_id: int = Field(ge=1)
    attendance_status: Literal["PRESENT", "SICK", "PERMITTED", "ABSENT"]


class AttendanceBatchCreate(BaseModel):
    slot_id: int = Field(ge=1)
    teacher_id: int = Field(ge=1)
    records: list[AttendanceBatchItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_students(self):
        student_ids = [item.student_id for item in self.records]
        if len(student_ids) != len(set(student_ids)):
            raise ValueError("Siswa yang sama tidak boleh dikirim lebih dari sekali.")
        return self


class AttendanceCompletenessResponse(BaseModel):
    session_id: int
    slot_id: int
    jp_number: int
    total_students: int
    recorded_count: int
    missing_count: int
    missing_students: list[dict]


class JournalSubmitRequest(BaseModel):
    officer_user_id: int = Field(ge=1)
