from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
