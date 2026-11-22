from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassOfficerAssignment, Classroom, User
from app.schemas import (
    ClassOfficerResponse,
    ClassroomCreate,
    ClassroomResponse,
    UserCreate,
    UserResponse,
)

app = FastAPI(
    title="JejakKBM API",
    description="Backend API untuk sistem jurnal kegiatan belajar mengajar.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return the basic availability status of the API."""
    return {"status": "ok", "service": "jejak-kbm-api"}


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    user = User(
        username=data.username,
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username sudah digunakan.",
        )

    return user


@app.get("/users", response_model=list[UserResponse], tags=["Users"])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@app.post(
    "/classes",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Classes"],
)
def create_classroom(data: ClassroomCreate, db: Session = Depends(get_db)):
    classroom = Classroom(
        name=data.name,
        academic_year=data.academic_year,
    )
    db.add(classroom)

    try:
        db.commit()
        db.refresh(classroom)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nama kelas sudah digunakan.",
        )

    return classroom


@app.get("/classes", response_model=list[ClassroomResponse], tags=["Classes"])
def get_classrooms(db: Session = Depends(get_db)):
    return db.query(Classroom).order_by(Classroom.id).all()


@app.put(
    "/classes/{class_id}/officer/{user_id}",
    response_model=ClassOfficerResponse,
    tags=["Class Officer"],
)
def assign_class_officer(
    class_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kelas tidak ditemukan.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pengguna tidak ditemukan.",
        )

    if user.role != "class_officer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pengguna harus memiliki role class_officer.",
        )

    existing_class_assignment = (
        db.query(ClassOfficerAssignment)
        .filter(ClassOfficerAssignment.class_id == class_id)
        .first()
    )
    if existing_class_assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kelas sudah memiliki petugas jurnal utama.",
        )

    existing_user_assignment = (
        db.query(ClassOfficerAssignment)
        .filter(ClassOfficerAssignment.user_id == user_id)
        .first()
    )
    if existing_user_assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Petugas sudah ditugaskan ke kelas lain.",
        )

    assignment = ClassOfficerAssignment(class_id=class_id, user_id=user_id)
    db.add(assignment)
    db.commit()

    return ClassOfficerResponse(
        class_id=classroom.id,
        class_name=classroom.name,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )


@app.get(
    "/classes/{class_id}/officer",
    response_model=ClassOfficerResponse,
    tags=["Class Officer"],
)
def get_class_officer(class_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kelas tidak ditemukan.",
        )

    assignment = (
        db.query(ClassOfficerAssignment)
        .filter(ClassOfficerAssignment.class_id == class_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kelas belum memiliki petugas jurnal utama.",
        )

    user = db.query(User).filter(User.id == assignment.user_id).first()

    return ClassOfficerResponse(
        class_id=classroom.id,
        class_name=classroom.name,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )
