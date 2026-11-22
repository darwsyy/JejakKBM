from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassOfficerAssignment, Classroom, ScheduleSlot, ScheduleTeacherAssignment, User
from app.schemas import (
    ClassOfficerResponse,
    ClassroomCreate,
    ClassroomResponse,
    UserCreate,
    UserResponse,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
    ScheduleSlotUpdate,
    ScheduleTeacherResponse,
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


@app.post(
    "/classes/{class_id}/schedule-slots",
    response_model=ScheduleSlotResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Schedule"],
)
def create_schedule_slot(
    class_id: int,
    data: ScheduleSlotCreate,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kelas tidak ditemukan.",
        )

    slot = ScheduleSlot(class_id=class_id, **data.model_dump())
    db.add(slot)

    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Urutan slot atau nomor JP pada hari tersebut sudah digunakan.",
        )

    return slot


@app.get(
    "/classes/{class_id}/schedule-slots",
    response_model=list[ScheduleSlotResponse],
    tags=["Schedule"],
)
def get_schedule_slots(
    class_id: int,
    day: str | None = None,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kelas tidak ditemukan.",
        )

    query = db.query(ScheduleSlot).filter(ScheduleSlot.class_id == class_id)
    if day is not None:
        valid_days = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        if day not in valid_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nama hari tidak valid.",
            )
        query = query.filter(ScheduleSlot.day_of_week == day)

    return query.order_by(
        ScheduleSlot.day_of_week,
        ScheduleSlot.slot_order,
    ).all()


@app.put(
    "/schedule-slots/{slot_id}",
    response_model=ScheduleSlotResponse,
    tags=["Schedule"],
)
def update_schedule_slot(
    slot_id: int,
    data: ScheduleSlotUpdate,
    db: Session = Depends(get_db),
):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot jadwal tidak ditemukan.",
        )

    for field, value in data.model_dump().items():
        setattr(slot, field, value)

    if slot.slot_type != "LESSON":
        assignment = db.query(ScheduleTeacherAssignment).filter(
            ScheduleTeacherAssignment.slot_id == slot_id
        ).first()
        if assignment is not None:
            db.delete(assignment)

    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Urutan slot atau nomor JP pada hari tersebut sudah digunakan.",
        )

    return slot


@app.put(
    "/schedule-slots/{slot_id}/teacher/{teacher_id}",
    response_model=ScheduleTeacherResponse,
    tags=["Schedule"],
)
def assign_schedule_teacher(
    slot_id: int,
    teacher_id: int,
    db: Session = Depends(get_db),
):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")
    if slot.slot_type != "LESSON":
        raise HTTPException(status_code=400, detail="Guru hanya dapat ditugaskan pada slot LESSON.")

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if teacher is None:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan.")
    if teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Pengguna harus merupakan guru yang aktif.")

    assignment = db.query(ScheduleTeacherAssignment).filter(
        ScheduleTeacherAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        assignment = ScheduleTeacherAssignment(slot_id=slot_id, teacher_id=teacher_id)
        db.add(assignment)
    else:
        assignment.teacher_id = teacher_id

    db.commit()
    return ScheduleTeacherResponse(
        slot_id=slot_id,
        teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        username=teacher.username,
    )


@app.get(
    "/schedule-slots/{slot_id}/teacher",
    response_model=ScheduleTeacherResponse,
    tags=["Schedule"],
)
def get_schedule_teacher(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")

    assignment = db.query(ScheduleTeacherAssignment).filter(
        ScheduleTeacherAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Slot belum memiliki guru pengajar.")

    teacher = db.query(User).filter(User.id == assignment.teacher_id).first()
    return ScheduleTeacherResponse(
        slot_id=slot_id,
        teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        username=teacher.username,
    )


@app.delete(
    "/schedule-slots/{slot_id}/teacher",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Schedule"],
)
def remove_schedule_teacher(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")

    assignment = db.query(ScheduleTeacherAssignment).filter(
        ScheduleTeacherAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Slot belum memiliki guru pengajar.")

    db.delete(assignment)
    db.commit()


@app.delete(
    "/schedule-slots/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Schedule"],
)
def delete_schedule_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot jadwal tidak ditemukan.",
        )

    assignment = db.query(ScheduleTeacherAssignment).filter(
        ScheduleTeacherAssignment.slot_id == slot_id
    ).first()
    if assignment is not None:
        db.delete(assignment)

    db.delete(slot)
    db.commit()
