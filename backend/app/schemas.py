from datetime import datetime
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
