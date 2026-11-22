from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ClassOfficerAssignment, Classroom, ScheduleSlot, ScheduleTeacherAssignment,
    ScheduleSubjectAssignment, Student, Subject, User,
)
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
    ScheduleSubjectResponse,
    SubjectCreate,
    SubjectResponse,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
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

        subject_assignment = db.query(ScheduleSubjectAssignment).filter(
            ScheduleSubjectAssignment.slot_id == slot_id
        ).first()
        if subject_assignment is not None:
            db.delete(subject_assignment)

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

    subject_assignment = db.query(ScheduleSubjectAssignment).filter(
        ScheduleSubjectAssignment.slot_id == slot_id
    ).first()
    if subject_assignment is not None:
        db.delete(subject_assignment)

    db.delete(slot)
    db.commit()


@app.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Subjects"],
)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(name=data.name.strip())
    if len(subject.name) < 2:
        raise HTTPException(status_code=422, detail="Nama mata pelajaran minimal 2 karakter.")

    db.add(subject)
    try:
        db.commit()
        db.refresh(subject)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mata pelajaran sudah terdaftar.",
        )
    return subject


@app.get("/subjects", response_model=list[SubjectResponse], tags=["Subjects"])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.name).all()


@app.put(
    "/schedule-slots/{slot_id}/subject/{subject_id}",
    response_model=ScheduleSubjectResponse,
    tags=["Schedule"],
)
def assign_schedule_subject(
    slot_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")
    if slot.slot_type != "LESSON":
        raise HTTPException(status_code=400, detail="Mata pelajaran hanya dapat ditetapkan pada slot LESSON.")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Mata pelajaran tidak ditemukan.")

    assignment = db.query(ScheduleSubjectAssignment).filter(
        ScheduleSubjectAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        assignment = ScheduleSubjectAssignment(slot_id=slot_id, subject_id=subject_id)
        db.add(assignment)
    else:
        assignment.subject_id = subject_id

    db.commit()
    return ScheduleSubjectResponse(
        slot_id=slot_id,
        subject_id=subject.id,
        subject_name=subject.name,
    )


@app.get(
    "/schedule-slots/{slot_id}/subject",
    response_model=ScheduleSubjectResponse,
    tags=["Schedule"],
)
def get_schedule_subject(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")

    assignment = db.query(ScheduleSubjectAssignment).filter(
        ScheduleSubjectAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Slot belum memiliki mata pelajaran.")

    subject = db.query(Subject).filter(Subject.id == assignment.subject_id).first()
    return ScheduleSubjectResponse(
        slot_id=slot_id,
        subject_id=subject.id,
        subject_name=subject.name,
    )


@app.delete(
    "/schedule-slots/{slot_id}/subject",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Schedule"],
)
def remove_schedule_subject(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan.")

    assignment = db.query(ScheduleSubjectAssignment).filter(
        ScheduleSubjectAssignment.slot_id == slot_id
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Slot belum memiliki mata pelajaran.")

    db.delete(assignment)
    db.commit()


@app.post(
    "/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Students"],
)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == data.class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    student = Student(
        nis=data.nis.strip(),
        full_name=data.full_name.strip(),
        class_id=data.class_id,
    )
    if not student.nis or len(student.full_name) < 2:
        raise HTTPException(status_code=422, detail="NIS dan nama siswa tidak valid.")

    db.add(student)
    try:
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NIS sudah terdaftar.",
        )
    return student


@app.get("/students", response_model=list[StudentResponse], tags=["Students"])
def get_students(class_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Student)
    if class_id is not None:
        classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
        if classroom is None:
            raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")
        query = query.filter(Student.class_id == class_id)
    return query.order_by(Student.full_name).all()


@app.put(
    "/students/{student_id}",
    response_model=StudentResponse,
    tags=["Students"],
)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan.")

    classroom = db.query(Classroom).filter(Classroom.id == data.class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    student.nis = data.nis.strip()
    student.full_name = data.full_name.strip()
    student.class_id = data.class_id
    if not student.nis or len(student.full_name) < 2:
        raise HTTPException(status_code=422, detail="NIS dan nama siswa tidak valid.")

    try:
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NIS sudah digunakan siswa lain.",
        )
    return student


@app.delete(
    "/students/{student_id}",
    response_model=StudentResponse,
    tags=["Students"],
)
def deactivate_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan.")

    # Data tidak dihapus permanen agar aman untuk riwayat absensi nantinya.
    student.is_active = False
    db.commit()
    db.refresh(student)
    return student
