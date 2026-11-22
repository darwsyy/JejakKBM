from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AttendanceRecord, ClassOfficerAssignment, ClassOfficerPeriod, Classroom, DailyJournal, DutyRoster, JournalReview, JournalSession, JournalSessionSlot, ScheduleSlot, ScheduleTeacherAssignment,
    ScheduleSubjectAssignment, Student, Subject, Teacher, User,
)
from app.schemas import (
    ClassDashboardResponse,
    ClassDashboardSessionResponse,
    ClassDashboardReviewResponse,
    DailyDashboardResponse,
    ClassOfficerResponse,
    DailyJournalCreate,
    DailyJournalResponse,
    JournalSubmitRequest,
    JournalReviewCreate,
    JournalReviewResponse,
    DutyRosterCreate,
    DutyRosterResponse,
    JournalRevisionStart,
    JournalSessionUpdate,
    AttendanceUpdate,
    JournalSessionCreate,
    JournalSessionResponse,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceBatchCreate,
    AttendanceCompletenessResponse,
    ClassOfficerPeriodCreate,
    ClassOfficerPeriodResponse,
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
    TeacherCreate,
    TeacherResponse,
    TeacherUpdate,
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


@app.post(
    "/teachers",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Teachers"],
)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Akun pengguna tidak ditemukan.")
    if user.role != "teacher":
        raise HTTPException(status_code=400, detail="Akun harus memiliki role teacher.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Akun guru tidak aktif.")

    teacher = Teacher(user_id=data.user_id, nip=data.nip.strip() if data.nip else None)
    if teacher.nip == "":
        teacher.nip = None
    db.add(teacher)
    try:
        db.commit()
        db.refresh(teacher)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun guru atau NIP sudah terdaftar.",
        )

    return TeacherResponse(
        id=teacher.id, user_id=user.id, username=user.username,
        full_name=user.full_name, nip=teacher.nip, is_active=teacher.is_active,
    )


@app.get("/teachers", response_model=list[TeacherResponse], tags=["Teachers"])
def get_teachers(db: Session = Depends(get_db)):
    records = db.query(Teacher, User).join(User, Teacher.user_id == User.id).order_by(User.full_name).all()
    return [
        TeacherResponse(
            id=teacher.id, user_id=user.id, username=user.username,
            full_name=user.full_name, nip=teacher.nip, is_active=teacher.is_active,
        )
        for teacher, user in records
    ]


@app.put(
    "/teachers/{teacher_id}",
    response_model=TeacherResponse,
    tags=["Teachers"],
)
def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher is None:
        raise HTTPException(status_code=404, detail="Data guru tidak ditemukan.")

    user = db.query(User).filter(User.id == teacher.user_id).first()
    teacher.nip = data.nip.strip() if data.nip else None
    try:
        db.commit()
        db.refresh(teacher)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="NIP sudah digunakan guru lain.")

    return TeacherResponse(
        id=teacher.id, user_id=user.id, username=user.username,
        full_name=user.full_name, nip=teacher.nip, is_active=teacher.is_active,
    )


@app.delete(
    "/teachers/{teacher_id}",
    response_model=TeacherResponse,
    tags=["Teachers"],
)
def deactivate_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher is None:
        raise HTTPException(status_code=404, detail="Data guru tidak ditemukan.")

    teacher.is_active = False
    db.commit()
    db.refresh(teacher)
    user = db.query(User).filter(User.id == teacher.user_id).first()
    return TeacherResponse(
        id=teacher.id, user_id=user.id, username=user.username,
        full_name=user.full_name, nip=teacher.nip, is_active=teacher.is_active,
    )


@app.post(
    "/classes/{class_id}/officer-periods",
    response_model=ClassOfficerPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Class Officer"],
)
def create_class_officer_period(
    class_id: int,
    data: ClassOfficerPeriodCreate,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    user = db.query(User).filter(User.id == data.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan.")
    if user.role != "class_officer":
        raise HTTPException(status_code=400, detail="Pengguna harus memiliki role class_officer.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Akun petugas tidak aktif.")

    # Cek apakah tanggal penugasan bertabrakan dengan periode lama di kelas ini.
    existing_periods = db.query(ClassOfficerPeriod).filter(
        ClassOfficerPeriod.class_id == class_id
    ).all()
    for period in existing_periods:
        new_ends_after_old_starts = (
            data.end_date is None or period.start_date <= data.end_date
        )
        old_ends_after_new_starts = (
            period.end_date is None or period.end_date >= data.start_date
        )
        if new_ends_after_old_starts and old_ends_after_new_starts:
            raise HTTPException(
                status_code=409,
                detail="Periode petugas bertabrakan dengan penugasan yang sudah ada.",
            )

    assignment = ClassOfficerPeriod(
        class_id=class_id,
        user_id=data.user_id,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return ClassOfficerPeriodResponse(
        id=assignment.id, class_id=classroom.id, class_name=classroom.name,
        user_id=user.id, username=user.username, full_name=user.full_name,
        start_date=assignment.start_date, end_date=assignment.end_date,
    )


@app.get(
    "/classes/{class_id}/officer-periods",
    response_model=list[ClassOfficerPeriodResponse],
    tags=["Class Officer"],
)
def get_class_officer_periods(class_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    records = (
        db.query(ClassOfficerPeriod, User)
        .join(User, ClassOfficerPeriod.user_id == User.id)
        .filter(ClassOfficerPeriod.class_id == class_id)
        .order_by(ClassOfficerPeriod.start_date)
        .all()
    )
    return [
        ClassOfficerPeriodResponse(
            id=period.id, class_id=classroom.id, class_name=classroom.name,
            user_id=user.id, username=user.username, full_name=user.full_name,
            start_date=period.start_date, end_date=period.end_date,
        )
        for period, user in records
    ]


@app.get(
    "/classes/{class_id}/officer-current",
    response_model=ClassOfficerPeriodResponse,
    tags=["Class Officer"],
)
def get_current_class_officer(
    class_id: int,
    on_date: date | None = None,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    selected_date = on_date or date.today()
    period = db.query(ClassOfficerPeriod).filter(
        ClassOfficerPeriod.class_id == class_id,
        ClassOfficerPeriod.start_date <= selected_date,
    ).filter(
        (ClassOfficerPeriod.end_date.is_(None))
        | (ClassOfficerPeriod.end_date >= selected_date)
    ).first()
    if period is None:
        raise HTTPException(status_code=404, detail="Tidak ada petugas untuk tanggal tersebut.")

    user = db.query(User).filter(User.id == period.user_id).first()
    return ClassOfficerPeriodResponse(
        id=period.id, class_id=classroom.id, class_name=classroom.name,
        user_id=user.id, username=user.username, full_name=user.full_name,
        start_date=period.start_date, end_date=period.end_date,
    )


@app.post(
    "/journals",
    response_model=DailyJournalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Daily Journals"],
)
def create_daily_journal(
    data: DailyJournalCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    # Satu kelas hanya memiliki satu jurnal untuk satu tanggal.
    existing = db.query(DailyJournal).filter(
        DailyJournal.class_id == data.class_id,
        DailyJournal.journal_date == data.journal_date,
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    classroom = db.query(Classroom).filter(Classroom.id == data.class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    officer = db.query(User).filter(User.id == data.officer_user_id).first()
    if officer is None:
        raise HTTPException(status_code=404, detail="Akun petugas tidak ditemukan.")
    if officer.role != "class_officer" or not officer.is_active:
        raise HTTPException(status_code=400, detail="Akun harus petugas kelas yang aktif.")

    assignment = db.query(ClassOfficerPeriod).filter(
        ClassOfficerPeriod.class_id == data.class_id,
        ClassOfficerPeriod.user_id == data.officer_user_id,
        ClassOfficerPeriod.start_date <= data.journal_date,
    ).filter(
        (ClassOfficerPeriod.end_date.is_(None))
        | (ClassOfficerPeriod.end_date >= data.journal_date)
    ).first()
    if assignment is None:
        raise HTTPException(
            status_code=403,
            detail="Akun ini bukan petugas jurnal kelas pada tanggal tersebut.",
        )

    journal = DailyJournal(
        class_id=data.class_id,
        journal_date=data.journal_date,
        officer_user_id=data.officer_user_id,
        status="DRAFT",
    )
    db.add(journal)
    try:
        db.commit()
        db.refresh(journal)
    except IntegrityError:
        db.rollback()
        # Melindungi dari dua request yang membuat jurnal bersamaan.
        journal = db.query(DailyJournal).filter(
            DailyJournal.class_id == data.class_id,
            DailyJournal.journal_date == data.journal_date,
        ).first()
        if journal is None:
            raise HTTPException(status_code=409, detail="Jurnal gagal dibuat.")
        response.status_code = status.HTTP_200_OK
    return journal


@app.get("/journals", response_model=list[DailyJournalResponse], tags=["Daily Journals"])
def get_daily_journals(
    class_id: int | None = None,
    journal_date: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(DailyJournal)
    if class_id is not None:
        query = query.filter(DailyJournal.class_id == class_id)
    if journal_date is not None:
        query = query.filter(DailyJournal.journal_date == journal_date)
    return query.order_by(DailyJournal.journal_date.desc(), DailyJournal.class_id).all()


@app.get("/dashboard/daily", response_model=DailyDashboardResponse, tags=["Dashboard"])
def get_daily_dashboard(report_date: date | None = None, db: Session = Depends(get_db)):
    selected_date = report_date or date.today()
    classrooms = db.query(Classroom).order_by(Classroom.name).all()
    journals = db.query(DailyJournal).filter(
        DailyJournal.journal_date == selected_date
    ).all()

    status_names = ["DRAFT", "SUBMITTED", "RESUBMITTED", "REVISION_REQUIRED", "APPROVED", "REJECTED"]
    status_counts = {name: 0 for name in status_names}
    submitted_class_ids = set()
    for journal in journals:
        if journal.status in status_counts:
            status_counts[journal.status] += 1
        submitted_class_ids.add(journal.class_id)

    missing_classes = [
        classroom.name for classroom in classrooms
        if classroom.id not in submitted_class_ids
    ]
    return DailyDashboardResponse(
        report_date=selected_date, total_classes=len(classrooms),
        total_journals=len(journals), status_counts=status_counts,
        missing_classes=missing_classes,
    )


@app.get(
    "/journals/{journal_id}",
    response_model=DailyJournalResponse,
    tags=["Daily Journals"],
)
def get_daily_journal(journal_id: int, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    return journal


def build_journal_session_response(db: Session, session: JournalSession):
    subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
    teacher = db.query(User).filter(User.id == session.teacher_id).first()
    links = db.query(JournalSessionSlot).filter(
        JournalSessionSlot.session_id == session.id
    ).all()
    slots = [
        db.query(ScheduleSlot).filter(ScheduleSlot.id == link.slot_id).first()
        for link in links
    ]
    slots.sort(key=lambda slot: slot.slot_order)
    return JournalSessionResponse(
        id=session.id,
        journal_id=session.journal_id,
        subject_id=subject.id,
        subject_name=subject.name,
        teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        slot_ids=[slot.id for slot in slots],
        jp_numbers=[slot.jp_number for slot in slots],
        material=session.material,
        actual_start_time=session.actual_start_time,
        actual_end_time=session.actual_end_time,
    )


@app.post(
    "/journals/{journal_id}/sessions",
    response_model=JournalSessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Journal Sessions"],
)
def create_journal_session(
    journal_id: int,
    data: JournalSessionCreate,
    db: Session = Depends(get_db),
):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Sesi hanya dapat ditambahkan saat jurnal berstatus DRAFT.")

    teacher = db.query(User).filter(User.id == data.teacher_id).first()
    if teacher is None:
        raise HTTPException(status_code=404, detail="Akun guru tidak ditemukan.")
    if teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Pengajar harus akun guru yang aktif.")

    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.id.in_(data.slot_ids),
        ScheduleSlot.class_id == journal.class_id,
        ScheduleSlot.day_of_week == journal.journal_date.strftime("%A"),
    ).all()
    if len(slots) != len(data.slot_ids):
        raise HTTPException(status_code=400, detail="Semua JP harus berasal dari jadwal kelas dan hari jurnal.")
    if any(slot.slot_type != "LESSON" or slot.jp_number is None for slot in slots):
        raise HTTPException(status_code=400, detail="Sesi hanya dapat menggunakan slot LESSON yang memiliki nomor JP.")

    slots.sort(key=lambda slot: slot.slot_order)
    for previous, current in zip(slots, slots[1:]):
        if current.slot_order != previous.slot_order + 1 or current.jp_number != previous.jp_number + 1:
            raise HTTPException(status_code=400, detail="JP harus berurutan dan tidak boleh melewati istirahat atau kegiatan lain.")

    subject_ids = set()
    for slot in slots:
        subject_assignment = db.query(ScheduleSubjectAssignment).filter(
            ScheduleSubjectAssignment.slot_id == slot.id
        ).first()
        teacher_assignment = db.query(ScheduleTeacherAssignment).filter(
            ScheduleTeacherAssignment.slot_id == slot.id
        ).first()
        if subject_assignment is None or teacher_assignment is None:
            raise HTTPException(status_code=400, detail="Setiap JP harus memiliki mata pelajaran dan guru pada jadwal.")
        subject_ids.add(subject_assignment.subject_id)
        if teacher_assignment.teacher_id != data.teacher_id:
            raise HTTPException(status_code=400, detail="Guru sesi harus sesuai dengan guru yang ditugaskan pada seluruh JP.")

    if len(subject_ids) != 1:
        raise HTTPException(status_code=400, detail="JP yang digabung harus memiliki mata pelajaran yang sama.")

    for slot in slots:
        already_used = db.query(JournalSessionSlot).join(
            JournalSession, JournalSession.id == JournalSessionSlot.session_id
        ).filter(
            JournalSession.journal_id == journal_id,
            JournalSessionSlot.slot_id == slot.id,
        ).first()
        if already_used is not None:
            raise HTTPException(status_code=409, detail="JP ini sudah tercatat dalam sesi lain.")

    session = JournalSession(
        journal_id=journal_id,
        subject_id=next(iter(subject_ids)),
        teacher_id=data.teacher_id,
        material=data.material.strip(),
        actual_start_time=data.actual_start_time,
        actual_end_time=data.actual_end_time,
    )
    if not session.material:
        raise HTTPException(status_code=422, detail="Materi pembelajaran tidak boleh kosong.")
    db.add(session)
    db.flush()
    for slot in slots:
        db.add(JournalSessionSlot(session_id=session.id, slot_id=slot.id))
    db.commit()
    db.refresh(session)
    return build_journal_session_response(db, session)


@app.get(
    "/journals/{journal_id}/sessions",
    response_model=list[JournalSessionResponse],
    tags=["Journal Sessions"],
)
def get_journal_sessions(journal_id: int, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    sessions = db.query(JournalSession).filter(
        JournalSession.journal_id == journal_id
    ).order_by(JournalSession.actual_start_time).all()
    return [build_journal_session_response(db, session) for session in sessions]


def build_attendance_response(db: Session, record: AttendanceRecord):
    student = db.query(Student).filter(Student.id == record.student_id).first()
    teacher = db.query(User).filter(User.id == record.teacher_id).first()
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == record.slot_id).first()
    return AttendanceResponse(
        id=record.id, session_id=record.session_id, slot_id=slot.id,
        jp_number=slot.jp_number, student_id=student.id,
        student_name=student.full_name, teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        attendance_status=record.attendance_status, recorded_at=record.recorded_at,
    )


@app.post(
    "/journal-sessions/{session_id}/attendance",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Attendance"],
)
def create_attendance(
    session_id: int,
    data: AttendanceCreate,
    db: Session = Depends(get_db),
):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi pembelajaran tidak ditemukan.")

    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Absensi hanya dapat diisi saat jurnal berstatus DRAFT.")

    if data.teacher_id != session.teacher_id:
        raise HTTPException(status_code=403, detail="Hanya guru pengajar sesi ini yang boleh mengisi absensi.")
    teacher = db.query(User).filter(User.id == data.teacher_id).first()
    if teacher is None or teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=403, detail="Akun pengisi harus guru yang aktif.")

    session_slot = db.query(JournalSessionSlot).filter(
        JournalSessionSlot.session_id == session_id,
        JournalSessionSlot.slot_id == data.slot_id,
    ).first()
    if session_slot is None:
        raise HTTPException(status_code=400, detail="JP tersebut tidak termasuk dalam sesi ini.")

    student = db.query(Student).filter(Student.id == data.student_id).first()
    if student is None or not student.is_active:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan atau tidak aktif.")
    if student.class_id != journal.class_id:
        raise HTTPException(status_code=400, detail="Siswa bukan anggota kelas pada jurnal ini.")

    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id,
        AttendanceRecord.slot_id == data.slot_id,
        AttendanceRecord.student_id == data.student_id,
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Absensi siswa untuk JP ini sudah diisi.")

    record = AttendanceRecord(
        session_id=session_id, slot_id=data.slot_id,
        student_id=data.student_id, teacher_id=data.teacher_id,
        attendance_status=data.attendance_status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return build_attendance_response(db, record)


@app.get(
    "/journal-sessions/{session_id}/attendance",
    response_model=list[AttendanceResponse],
    tags=["Attendance"],
)
def get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi pembelajaran tidak ditemukan.")
    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id
    ).order_by(AttendanceRecord.slot_id, AttendanceRecord.student_id).all()
    return [build_attendance_response(db, record) for record in records]


@app.post(
    "/journal-sessions/{session_id}/attendance/batch",
    response_model=list[AttendanceResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Attendance"],
)
def create_attendance_batch(
    session_id: int,
    data: AttendanceBatchCreate,
    db: Session = Depends(get_db),
):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi pembelajaran tidak ditemukan.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Absensi hanya dapat diisi saat jurnal berstatus DRAFT.")
    if data.teacher_id != session.teacher_id:
        raise HTTPException(status_code=403, detail="Hanya guru pengajar sesi ini yang boleh mengisi absensi.")
    teacher = db.query(User).filter(User.id == data.teacher_id).first()
    if teacher is None or teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=403, detail="Akun pengisi harus guru yang aktif.")

    session_slot = db.query(JournalSessionSlot).filter(
        JournalSessionSlot.session_id == session_id,
        JournalSessionSlot.slot_id == data.slot_id,
    ).first()
    if session_slot is None:
        raise HTTPException(status_code=400, detail="JP tersebut tidak termasuk dalam sesi ini.")

    student_ids = [item.student_id for item in data.records]
    students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    student_map = {student.id: student for student in students}
    if len(student_map) != len(student_ids):
        raise HTTPException(status_code=404, detail="Satu atau beberapa siswa tidak ditemukan.")
    for student in students:
        if not student.is_active:
            raise HTTPException(status_code=400, detail=f"Siswa {student.full_name} tidak aktif.")
        if student.class_id != journal.class_id:
            raise HTTPException(status_code=400, detail=f"Siswa {student.full_name} bukan anggota kelas jurnal.")

    existing_ids = {row.student_id for row in db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id,
        AttendanceRecord.slot_id == data.slot_id,
        AttendanceRecord.student_id.in_(student_ids),
    ).all()}
    if existing_ids:
        raise HTTPException(status_code=409, detail="Sebagian siswa sudah memiliki catatan absensi untuk JP ini.")

    records = [AttendanceRecord(
        session_id=session_id, slot_id=data.slot_id,
        student_id=item.student_id, teacher_id=data.teacher_id,
        attendance_status=item.attendance_status,
    ) for item in data.records]
    db.add_all(records)
    db.commit()
    for record in records:
        db.refresh(record)
    return [build_attendance_response(db, record) for record in records]


@app.get(
    "/journal-sessions/{session_id}/attendance/completeness",
    response_model=list[AttendanceCompletenessResponse],
    tags=["Attendance"],
)
def get_attendance_completeness(
    session_id: int,
    slot_id: int | None = None,
    db: Session = Depends(get_db),
):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi pembelajaran tidak ditemukan.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    links = db.query(JournalSessionSlot).filter(
        JournalSessionSlot.session_id == session_id
    ).all()
    slot_ids = [link.slot_id for link in links]
    if slot_id is not None and slot_id not in slot_ids:
        raise HTTPException(status_code=400, detail="JP tersebut tidak termasuk dalam sesi ini.")
    if slot_id is not None:
        slot_ids = [slot_id]

    students = db.query(Student).filter(
        Student.class_id == journal.class_id, Student.is_active.is_(True)
    ).order_by(Student.full_name).all()
    results = []
    for current_slot_id in slot_ids:
        slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == current_slot_id).first()
        attendance = db.query(AttendanceRecord).filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.slot_id == current_slot_id,
        ).all()
        recorded_ids = {record.student_id for record in attendance}
        missing = [
            {"student_id": student.id, "nis": student.nis, "full_name": student.full_name}
            for student in students if student.id not in recorded_ids
        ]
        results.append(AttendanceCompletenessResponse(
            session_id=session_id, slot_id=current_slot_id, jp_number=slot.jp_number,
            total_students=len(students), recorded_count=len(recorded_ids),
            missing_count=len(missing), missing_students=missing,
        ))
    return results


@app.post("/journals/{journal_id}/revision/start", response_model=DailyJournalResponse, tags=["Daily Journals"])
def start_journal_revision(journal_id: int, data: JournalRevisionStart, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status != "REVISION_REQUIRED":
        raise HTTPException(status_code=400, detail="Jurnal tidak sedang menunggu revisi.")
    if data.officer_user_id != journal.officer_user_id:
        raise HTTPException(status_code=403, detail="Hanya petugas jurnal yang ditetapkan yang dapat memperbaiki.")
    journal.status = "DRAFT"
    db.commit()
    db.refresh(journal)
    return journal


@app.put("/journal-sessions/{session_id}", response_model=JournalSessionResponse, tags=["Journal Sessions"])
def update_journal_session(session_id: int, data: JournalSessionUpdate, db: Session = Depends(get_db)):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Sesi hanya dapat diperbaiki saat jurnal DRAFT.")
    session.material = data.material.strip()
    session.actual_start_time = data.actual_start_time
    session.actual_end_time = data.actual_end_time
    db.commit()
    db.refresh(session)
    return build_journal_session_response(db, session)


@app.put("/attendance/{attendance_id}", response_model=AttendanceResponse, tags=["Attendance"])
def update_attendance(attendance_id: int, data: AttendanceUpdate, db: Session = Depends(get_db)):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == attendance_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Catatan absensi tidak ditemukan.")
    session = db.query(JournalSession).filter(JournalSession.id == record.session_id).first()
    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Absensi hanya dapat diperbaiki saat jurnal DRAFT.")
    if data.teacher_id != session.teacher_id:
        raise HTTPException(status_code=403, detail="Hanya guru pengajar sesi ini yang dapat memperbaiki absensi.")
    teacher = db.query(User).filter(User.id == data.teacher_id).first()
    if teacher is None or teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=403, detail="Akun pengisi harus guru yang aktif.")
    record.teacher_id = data.teacher_id
    record.attendance_status = data.attendance_status
    db.commit()
    db.refresh(record)
    return build_attendance_response(db, record)


@app.post(
    "/journals/{journal_id}/submit",
    response_model=DailyJournalResponse,
    tags=["Daily Journals"],
)
def submit_daily_journal(
    journal_id: int,
    data: JournalSubmitRequest,
    db: Session = Depends(get_db),
):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Hanya jurnal DRAFT yang dapat dikirim.")
    if data.officer_user_id != journal.officer_user_id:
        raise HTTPException(status_code=403, detail="Hanya petugas jurnal yang ditetapkan yang dapat mengirim.")

    officer_period = db.query(ClassOfficerPeriod).filter(
        ClassOfficerPeriod.class_id == journal.class_id,
        ClassOfficerPeriod.user_id == data.officer_user_id,
        ClassOfficerPeriod.start_date <= journal.journal_date,
    ).filter(
        (ClassOfficerPeriod.end_date.is_(None))
        | (ClassOfficerPeriod.end_date >= journal.journal_date)
    ).first()
    if officer_period is None:
        raise HTTPException(status_code=403, detail="Petugas tidak terdaftar pada tanggal jurnal.")

    expected_slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.class_id == journal.class_id,
        ScheduleSlot.day_of_week == journal.journal_date.strftime("%A"),
        ScheduleSlot.slot_type == "LESSON",
        ScheduleSlot.jp_number.is_not(None),
    ).all()
    sessions = db.query(JournalSession).filter(JournalSession.journal_id == journal_id).all()
    session_slot_ids = set()
    for session in sessions:
        links = db.query(JournalSessionSlot).filter(
            JournalSessionSlot.session_id == session.id
        ).all()
        session_slot_ids.update(link.slot_id for link in links)

    expected_slot_ids = {slot.id for slot in expected_slots}
    missing_sessions = expected_slot_ids - session_slot_ids
    if missing_sessions:
        raise HTTPException(
            status_code=400,
            detail=f"Masih ada {len(missing_sessions)} JP pelajaran yang belum dicatat dalam sesi.",
        )

    active_students = db.query(Student).filter(
        Student.class_id == journal.class_id,
        Student.is_active.is_(True),
    ).all()
    for session in sessions:
        links = db.query(JournalSessionSlot).filter(
            JournalSessionSlot.session_id == session.id
        ).all()
        for link in links:
            attendance_ids = {
                row.student_id for row in db.query(AttendanceRecord).filter(
                    AttendanceRecord.session_id == session.id,
                    AttendanceRecord.slot_id == link.slot_id,
                ).all()
            }
            missing_count = sum(
                1 for student in active_students if student.id not in attendance_ids
            )
            if missing_count:
                slot = db.query(ScheduleSlot).filter(
                    ScheduleSlot.id == link.slot_id
                ).first()
                raise HTTPException(
                    status_code=400,
                    detail=f"Absensi JP {slot.jp_number} belum lengkap: {missing_count} siswa belum dicatat.",
                )

    previous_revision = db.query(JournalReview).filter(
        JournalReview.journal_id == journal_id,
        JournalReview.decision == "REQUEST_REVISION",
    ).first()
    journal.status = "RESUBMITTED" if previous_revision is not None else "SUBMITTED"
    db.commit()
    db.refresh(journal)
    return journal


@app.post("/duty-rosters", response_model=DutyRosterResponse, status_code=status.HTTP_201_CREATED, tags=["Duty Rosters"])
def create_duty_roster(data: DutyRosterCreate, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == data.assigned_by_user_id).first()
    if admin is None or admin.role != "admin" or not admin.is_active:
        raise HTTPException(status_code=403, detail="Penugasan hanya dapat dibuat oleh akun admin aktif.")
    teacher = db.query(User).filter(User.id == data.teacher_user_id).first()
    if teacher is None or teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Guru piket harus menggunakan akun guru aktif.")
    existing = db.query(DutyRoster).filter(
        DutyRoster.duty_date == data.duty_date,
        DutyRoster.teacher_user_id == data.teacher_user_id,
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Guru tersebut sudah ditugaskan pada tanggal itu.")
    roster = DutyRoster(
        duty_date=data.duty_date,
        teacher_user_id=data.teacher_user_id,
        assigned_by_user_id=data.assigned_by_user_id,
    )
    db.add(roster)
    db.commit()
    db.refresh(roster)
    return DutyRosterResponse(
        id=roster.id, duty_date=roster.duty_date,
        teacher_user_id=teacher.id, teacher_name=teacher.full_name,
        username=teacher.username, assigned_by_user_id=roster.assigned_by_user_id,
    )


@app.get("/duty-rosters", response_model=list[DutyRosterResponse], tags=["Duty Rosters"])
def get_duty_rosters(duty_date: date | None = None, db: Session = Depends(get_db)):
    query = db.query(DutyRoster)
    if duty_date is not None:
        query = query.filter(DutyRoster.duty_date == duty_date)
    rosters = query.order_by(DutyRoster.duty_date, DutyRoster.id).all()
    results = []
    for roster in rosters:
        teacher = db.query(User).filter(User.id == roster.teacher_user_id).first()
        results.append(DutyRosterResponse(
            id=roster.id, duty_date=roster.duty_date,
            teacher_user_id=roster.teacher_user_id, teacher_name=teacher.full_name,
            username=teacher.username, assigned_by_user_id=roster.assigned_by_user_id,
        ))
    return results


@app.delete("/duty-rosters/{roster_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Duty Rosters"])
def delete_duty_roster(roster_id: int, admin_user_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if admin is None or admin.role != "admin" or not admin.is_active:
        raise HTTPException(status_code=403, detail="Hanya admin aktif yang dapat menghapus penugasan.")
    roster = db.query(DutyRoster).filter(DutyRoster.id == roster_id).first()
    if roster is None:
        raise HTTPException(status_code=404, detail="Penugasan piket tidak ditemukan.")
    db.delete(roster)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/reviews/inbox", response_model=list[DailyJournalResponse], tags=["Journal Reviews"])
def get_review_inbox(db: Session = Depends(get_db)):
    return db.query(DailyJournal).filter(
        DailyJournal.status.in_(["SUBMITTED", "RESUBMITTED"])
    ).order_by(DailyJournal.journal_date, DailyJournal.id).all()


@app.post("/journals/{journal_id}/review", response_model=JournalReviewResponse, status_code=status.HTTP_201_CREATED, tags=["Journal Reviews"])
def review_daily_journal(journal_id: int, data: JournalReviewCreate, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status not in ("SUBMITTED", "RESUBMITTED"):
        raise HTTPException(status_code=400, detail="Jurnal belum dikirim atau sudah diperiksa.")
    reviewer = db.query(User).filter(User.id == data.reviewer_user_id).first()
    if reviewer is None or reviewer.role != "teacher" or not reviewer.is_active:
        raise HTTPException(status_code=403, detail="Pemeriksa harus akun guru yang aktif.")
    duty = db.query(DutyRoster).filter(
        DutyRoster.duty_date == journal.journal_date,
        DutyRoster.teacher_user_id == reviewer.id,
    ).first()
    if duty is None:
        raise HTTPException(status_code=403, detail="Guru tidak terdaftar sebagai petugas piket pada tanggal jurnal.")
    status_by_decision = {"APPROVE": "APPROVED", "REQUEST_REVISION": "REVISION_REQUIRED", "REJECT": "REJECTED"}
    journal.status = status_by_decision[data.decision]
    review = JournalReview(journal_id=journal_id, reviewer_user_id=reviewer.id, decision=data.decision, notes=data.notes.strip() if data.notes else None)
    db.add(review)
    db.commit()
    db.refresh(review)
    return JournalReviewResponse(id=review.id, journal_id=review.journal_id, reviewer_user_id=review.reviewer_user_id, reviewer_name=reviewer.full_name, decision=review.decision, notes=review.notes, reviewed_at=review.reviewed_at)


@app.get("/journals/{journal_id}/reviews", response_model=list[JournalReviewResponse], tags=["Journal Reviews"])
def get_journal_reviews(journal_id: int, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    reviews = db.query(JournalReview).filter(JournalReview.journal_id == journal_id).order_by(JournalReview.reviewed_at, JournalReview.id).all()
    results = []
    for review in reviews:
        reviewer = db.query(User).filter(User.id == review.reviewer_user_id).first()
        results.append(JournalReviewResponse(id=review.id, journal_id=review.journal_id, reviewer_user_id=review.reviewer_user_id, reviewer_name=reviewer.full_name, decision=review.decision, notes=review.notes, reviewed_at=review.reviewed_at))
    return results


@app.get(
    "/dashboard/classes/{class_id}",
    response_model=ClassDashboardResponse,
    tags=["Dashboard"],
)
def get_class_dashboard(
    class_id: int,
    report_date: date | None = None,
    db: Session = Depends(get_db),
):
    selected_date = report_date or date.today()
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    journal = db.query(DailyJournal).filter(
        DailyJournal.class_id == class_id,
        DailyJournal.journal_date == selected_date,
    ).first()
    attendance_statuses = ["PRESENT", "SICK", "PERMITTED", "ABSENT"]
    total_counts = {name: 0 for name in attendance_statuses}
    session_results = []
    reviews = []

    if journal is not None:
        sessions = db.query(JournalSession).filter(
            JournalSession.journal_id == journal.id
        ).order_by(JournalSession.actual_start_time).all()

        for session in sessions:
            subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
            teacher = db.query(User).filter(User.id == session.teacher_id).first()
            links = db.query(JournalSessionSlot).filter(
                JournalSessionSlot.session_id == session.id
            ).all()
            slots = [
                db.query(ScheduleSlot).filter(ScheduleSlot.id == link.slot_id).first()
                for link in links
            ]
            slots.sort(key=lambda slot: slot.slot_order)
            records = db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session.id
            ).all()
            counts = {name: 0 for name in attendance_statuses}
            for record in records:
                if record.attendance_status in counts:
                    counts[record.attendance_status] += 1
                    total_counts[record.attendance_status] += 1

            session_results.append(ClassDashboardSessionResponse(
                session_id=session.id,
                subject_name=subject.name,
                teacher_id=teacher.id,
                teacher_name=teacher.full_name,
                jp_numbers=[slot.jp_number for slot in slots],
                material=session.material,
                actual_start_time=session.actual_start_time,
                actual_end_time=session.actual_end_time,
                attendance_counts=counts,
            ))

        review_rows = db.query(JournalReview).filter(
            JournalReview.journal_id == journal.id
        ).order_by(JournalReview.reviewed_at, JournalReview.id).all()
        for review in review_rows:
            reviewer = db.query(User).filter(User.id == review.reviewer_user_id).first()
            reviews.append(ClassDashboardReviewResponse(
                decision=review.decision,
                reviewer_name=reviewer.full_name,
                notes=review.notes,
                reviewed_at=review.reviewed_at,
            ))

    return ClassDashboardResponse(
        report_date=selected_date,
        class_id=classroom.id,
        class_name=classroom.name,
        journal_id=journal.id if journal else None,
        journal_status=journal.status if journal else "MISSING",
        total_sessions=len(session_results),
        attendance_counts=total_counts,
        sessions=session_results,
        reviews=reviews,
    )
