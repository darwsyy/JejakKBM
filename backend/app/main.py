import csv
from datetime import date
from io import StringIO

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import (
    TOKEN_LIFETIME_SECONDS, create_access_token, get_current_user,
    hash_password, require_roles, verify_password,
)
from app.models import (
    AttendanceRecord, AuditLog, ClassOfficerAssignment, ClassOfficerPeriod, Classroom, DailyJournal, DutyRoster, JournalReview, JournalSession, JournalSessionSlot, Notification, ScheduleSlot, ScheduleTeacherAssignment, TeacherAbsenceReport,
    ScheduleSubjectAssignment, Student, Subject, Teacher, User,
)
from app.schemas import (
    ClassDashboardResponse,
    ClassDashboardSessionResponse,
    ClassDashboardReviewResponse,
    TeacherAbsenceReportCreate,
    TeacherAbsenceReportResponse,
    NotificationResponse,
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
    AdminBootstrap,
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    SetPasswordRequest,
    AuditLogResponse,
    DailyScheduleResponse,
    DailyScheduleSlotResponse,
    AttendanceReportResponse,
    StudentAttendanceSummary,
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


@app.post("/auth/bootstrap", response_model=UserResponse, status_code=201, tags=["Authentication"])
def bootstrap_admin(data: AdminBootstrap, db: Session = Depends(get_db)):
    """Membuat admin pertama saat database belum memiliki admin ber-password."""
    existing_admin = db.query(User).filter(
        User.role == "admin", User.password_hash.is_not(None)
    ).first()
    if existing_admin is not None:
        raise HTTPException(status_code=409, detail="Admin awal sudah dibuat.")

    user = db.query(User).filter(User.username == data.username).first()
    if user is not None:
        if user.role != "admin" or user.password_hash is not None:
            raise HTTPException(status_code=409, detail="Username sudah digunakan.")
        user.full_name = data.full_name.strip()
        user.password_hash = hash_password(data.password)
    else:
        user = User(
            username=data.username.strip(),
            full_name=data.full_name.strip(),
            role="admin",
            password_hash=hash_password(data.password),
        )
        db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admin awal gagal dibuat.")
    return user


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Username atau password salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.id, user.token_version),
        expires_in=TOKEN_LIFETIME_SECONDS,
        user=user,
    )


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/auth/change-password", tags=["Authentication"])
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Password lama tidak sesuai.")
    current_user.password_hash = hash_password(data.new_password)
    current_user.token_version += 1
    db.commit()
    return {"message": "Password berhasil diubah. Semua token lama sudah tidak berlaku."}


@app.post("/auth/logout", tags=["Authentication"])
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    return {"message": "Logout berhasil. Token ini sudah tidak berlaku."}


@app.put("/users/{user_id}/password", response_model=UserResponse, tags=["Users"], dependencies=[Depends(require_roles("admin"))])
def set_user_password(
    user_id: int,
    data: SetPasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan.")
    user.password_hash = hash_password(data.password)
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def add_notification(
    db: Session,
    recipient_user_id: int,
    journal_id: int,
    notification_type: str,
    title: str,
    message: str,
):
    notification = Notification(
        recipient_user_id=recipient_user_id,
        journal_id=journal_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )
    db.add(notification)
    return notification


def add_audit_log(
    db: Session,
    actor_user_id,
    action: str,
    target_type: str,
    target_id: int,
    details: str,
):
    try:
        actor_id = int(actor_user_id)
    except (TypeError, ValueError):
        actor_id = None
    if actor_id is not None and db.query(User.id).filter(User.id == actor_id).first() is None:
        actor_id = None
    db.add(AuditLog(
        actor_user_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details[:500],
    ))


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    dependencies=[Depends(require_roles("admin"))])
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


@app.get("/users", response_model=list[UserResponse], tags=["Users"], dependencies=[Depends(require_roles("admin"))])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@app.post(
    "/classes",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Classes"],
    dependencies=[Depends(require_roles("admin"))])
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


@app.get("/classes", response_model=list[ClassroomResponse], tags=["Classes"], dependencies=[Depends(get_current_user)])
def get_classrooms(db: Session = Depends(get_db)):
    return db.query(Classroom).order_by(Classroom.id).all()


@app.put(
    "/classes/{class_id}/officer/{user_id}",
    response_model=ClassOfficerResponse,
    tags=["Class Officer"],
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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


@app.get("/subjects", response_model=list[SubjectResponse], tags=["Subjects"], dependencies=[Depends(get_current_user)])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.name).all()


@app.put(
    "/schedule-slots/{slot_id}/subject/{subject_id}",
    response_model=ScheduleSubjectResponse,
    tags=["Schedule"],
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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


@app.get("/students", response_model=list[StudentResponse], tags=["Students"], dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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


@app.get("/teachers", response_model=list[TeacherResponse], tags=["Teachers"], dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(require_roles("admin"))])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(get_current_user)])
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


@app.get(
    "/classes/{class_id}/daily-schedule",
    response_model=DailyScheduleResponse,
    tags=["Schedule"],
    dependencies=[Depends(get_current_user)],
)
def get_daily_schedule(
    class_id: int,
    on_date: date | None = None,
    db: Session = Depends(get_db),
):
    selected_date = on_date or date.today()
    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    day_name = selected_date.strftime("%A")
    schedule_slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.class_id == class_id,
        ScheduleSlot.day_of_week == day_name,
    ).order_by(ScheduleSlot.slot_order).all()
    journal = db.query(DailyJournal).filter(
        DailyJournal.class_id == class_id,
        DailyJournal.journal_date == selected_date,
    ).first()

    results = []
    for slot in schedule_slots:
        subject_assignment = db.query(ScheduleSubjectAssignment).filter(
            ScheduleSubjectAssignment.slot_id == slot.id
        ).first()
        subject = (
            db.query(Subject).filter(Subject.id == subject_assignment.subject_id).first()
            if subject_assignment else None
        )

        teacher_assignment = db.query(ScheduleTeacherAssignment).filter(
            ScheduleTeacherAssignment.slot_id == slot.id
        ).first()
        scheduled_teacher = (
            db.query(User).filter(User.id == teacher_assignment.teacher_id).first()
            if teacher_assignment else None
        )

        session = None
        actual_teacher = None
        if journal is not None:
            session_link = db.query(JournalSessionSlot).join(
                JournalSession, JournalSession.id == JournalSessionSlot.session_id
            ).filter(
                JournalSession.journal_id == journal.id,
                JournalSessionSlot.slot_id == slot.id,
            ).first()
            if session_link is not None:
                session = db.query(JournalSession).filter(
                    JournalSession.id == session_link.session_id
                ).first()
                actual_teacher = db.query(User).filter(
                    User.id == session.teacher_id
                ).first()

        results.append(DailyScheduleSlotResponse(
            slot_id=slot.id,
            slot_order=slot.slot_order,
            jp_number=slot.jp_number,
            start_time=slot.start_time,
            end_time=slot.end_time,
            slot_type=slot.slot_type,
            subject_name=subject.name if subject else None,
            scheduled_teacher_id=scheduled_teacher.id if scheduled_teacher else None,
            scheduled_teacher_name=scheduled_teacher.full_name if scheduled_teacher else None,
            session_id=session.id if session else None,
            actual_teacher_id=actual_teacher.id if actual_teacher else None,
            actual_teacher_name=actual_teacher.full_name if actual_teacher else None,
        ))

    return DailyScheduleResponse(
        class_id=classroom.id,
        class_name=classroom.name,
        schedule_date=selected_date,
        day_of_week=day_name,
        journal_id=journal.id if journal else None,
        journal_status=journal.status if journal else "MISSING",
        slots=results,
    )


@app.post(
    "/journals",
    response_model=DailyJournalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Daily Journals"],
    dependencies=[Depends(get_current_user)])
def create_daily_journal(
    data: DailyJournalCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.officer_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik petugas kelas yang membuat jurnal.")
    # Satu kelas hanya memiliki satu jurnal untuk satu tanggal.
    existing = db.query(DailyJournal).filter(
        DailyJournal.class_id == data.class_id,
        DailyJournal.journal_date == data.journal_date,
    ).first()
    if existing is not None:
        if existing.officer_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Jurnal ini bukan milik petugas yang sedang login.")
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
        db.flush()
        add_audit_log(db, current_user.id, "JOURNAL_CREATED", "DailyJournal", journal.id, "Jurnal harian dibuat.")
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


@app.get("/journals", response_model=list[DailyJournalResponse], tags=["Daily Journals"], dependencies=[Depends(get_current_user)])
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


@app.get("/dashboard/daily", response_model=DailyDashboardResponse, tags=["Dashboard"], dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(get_current_user)])
def create_journal_session(
    journal_id: int,
    data: JournalSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.teacher_id:
        raise HTTPException(status_code=403, detail="Token login harus milik guru yang mengisi sesi.")
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
            absence_report = db.query(TeacherAbsenceReport).filter(
                TeacherAbsenceReport.journal_id == journal_id,
                TeacherAbsenceReport.slot_id == slot.id,
                TeacherAbsenceReport.scheduled_teacher_id == teacher_assignment.teacher_id,
            ).first()
            if absence_report is None:
                raise HTTPException(
                    status_code=400,
                    detail="Guru sesi harus sesuai jadwal. Jika guru terjadwal tidak hadir, petugas kelas harus membuat laporan ketidakhadiran terlebih dahulu.",
                )

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
    add_audit_log(db, current_user.id, "SESSION_CREATED", "DailyJournal", journal.id, f"Sesi dibuat untuk {len(slots)} JP.")
    db.commit()
    db.refresh(session)
    return build_journal_session_response(db, session)


@app.get(
    "/journals/{journal_id}/sessions",
    response_model=list[JournalSessionResponse],
    tags=["Journal Sessions"],
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(get_current_user)])
def create_attendance(
    session_id: int,
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.teacher_id:
        raise HTTPException(status_code=403, detail="Token login harus milik guru pengajar sesi ini.")
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
    db.flush()
    add_audit_log(db, current_user.id, "ATTENDANCE_RECORDED", "DailyJournal", journal.id, f"Absensi siswa {student.full_name} dicatat.")
    db.commit()
    db.refresh(record)
    return build_attendance_response(db, record)


@app.get(
    "/journal-sessions/{session_id}/attendance",
    response_model=list[AttendanceResponse],
    tags=["Attendance"],
    dependencies=[Depends(get_current_user)])
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
    dependencies=[Depends(get_current_user)])
def create_attendance_batch(
    session_id: int,
    data: AttendanceBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.teacher_id:
        raise HTTPException(status_code=403, detail="Token login harus milik guru pengajar sesi ini.")
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
    add_audit_log(db, current_user.id, "ATTENDANCE_BATCH_RECORDED", "DailyJournal", journal.id, f"Absensi {len(records)} siswa dicatat sekaligus.")
    db.commit()
    for record in records:
        db.refresh(record)
    return [build_attendance_response(db, record) for record in records]


@app.get(
    "/journal-sessions/{session_id}/attendance/completeness",
    response_model=list[AttendanceCompletenessResponse],
    tags=["Attendance"],
    dependencies=[Depends(get_current_user)])
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


@app.post("/journals/{journal_id}/revision/start", response_model=DailyJournalResponse, tags=["Daily Journals"], dependencies=[Depends(get_current_user)])
def start_journal_revision(
    journal_id: int, data: JournalRevisionStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.officer_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik petugas kelas.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status != "REVISION_REQUIRED":
        raise HTTPException(status_code=400, detail="Jurnal tidak sedang menunggu revisi.")
    if data.officer_user_id != journal.officer_user_id:
        raise HTTPException(status_code=403, detail="Hanya petugas jurnal yang ditetapkan yang dapat memperbaiki.")
    journal.status = "DRAFT"
    add_audit_log(db, current_user.id, "JOURNAL_REVISION_STARTED", "DailyJournal", journal.id, "Petugas mulai memperbaiki jurnal.")
    db.commit()
    db.refresh(journal)
    return journal


@app.put("/journal-sessions/{session_id}", response_model=JournalSessionResponse, tags=["Journal Sessions"], dependencies=[Depends(get_current_user)])
def update_journal_session(
    session_id: int, data: JournalSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(JournalSession).filter(JournalSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    if current_user.id != session.teacher_id:
        raise HTTPException(status_code=403, detail="Hanya guru pengajar sesi ini yang dapat memperbaiki.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == session.journal_id).first()
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Sesi hanya dapat diperbaiki saat jurnal DRAFT.")
    session.material = data.material.strip()
    session.actual_start_time = data.actual_start_time
    session.actual_end_time = data.actual_end_time
    add_audit_log(db, current_user.id, "SESSION_UPDATED", "DailyJournal", journal.id, "Materi atau waktu aktual sesi diperbarui.")
    db.commit()
    db.refresh(session)
    return build_journal_session_response(db, session)


@app.put("/attendance/{attendance_id}", response_model=AttendanceResponse, tags=["Attendance"], dependencies=[Depends(get_current_user)])
def update_attendance(
    attendance_id: int, data: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.teacher_id:
        raise HTTPException(status_code=403, detail="Token login harus milik guru pengajar sesi ini.")
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
    add_audit_log(db, current_user.id, "ATTENDANCE_UPDATED", "DailyJournal", journal.id, f"Status absensi siswa {record.student_id} diperbarui.")
    db.commit()
    db.refresh(record)
    return build_attendance_response(db, record)


@app.post(
    "/journals/{journal_id}/submit",
    response_model=DailyJournalResponse,
    tags=["Daily Journals"],
    dependencies=[Depends(get_current_user)])
def submit_daily_journal(
    journal_id: int,
    data: JournalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.officer_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik petugas kelas yang mengirim jurnal.")
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
    is_resubmission = previous_revision is not None
    journal.status = "RESUBMITTED" if is_resubmission else "SUBMITTED"

    classroom = db.query(Classroom).filter(Classroom.id == journal.class_id).first()
    duty_teachers = db.query(DutyRoster).filter(
        DutyRoster.duty_date == journal.journal_date
    ).all()
    notification_type = "JOURNAL_RESUBMITTED" if is_resubmission else "JOURNAL_SUBMITTED"
    notification_title = "Jurnal dikirim ulang" if is_resubmission else "Jurnal baru menunggu pemeriksaan"
    notification_message = (
        f"Jurnal kelas {classroom.name} tanggal {journal.journal_date} "
        f"{'dikirim ulang' if is_resubmission else 'telah dikirim'} dan menunggu pemeriksaan."
    )
    for duty_teacher in duty_teachers:
        add_notification(
            db, duty_teacher.teacher_user_id, journal.id, notification_type,
            notification_title, notification_message,
        )
    add_audit_log(
        db, current_user.id, notification_type, "DailyJournal", journal.id,
        f"Jurnal kelas {classroom.name} dikirim dengan status {journal.status}.",
    )

    db.commit()
    db.refresh(journal)
    return journal


@app.post("/duty-rosters", response_model=DutyRosterResponse, status_code=status.HTTP_201_CREATED, tags=["Duty Rosters"], dependencies=[Depends(require_roles("admin"))])
def create_duty_roster(
    data: DutyRosterCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.assigned_by_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik admin yang membuat penugasan.")
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
    db.flush()
    add_audit_log(db, current_user.id, "DUTY_ROSTER_CREATED", "DutyRoster", roster.id, f"Guru {teacher.full_name} ditugaskan sebagai piket pada {data.duty_date}.")
    db.commit()
    db.refresh(roster)
    return DutyRosterResponse(
        id=roster.id, duty_date=roster.duty_date,
        teacher_user_id=teacher.id, teacher_name=teacher.full_name,
        username=teacher.username, assigned_by_user_id=roster.assigned_by_user_id,
    )


@app.get("/duty-rosters", response_model=list[DutyRosterResponse], tags=["Duty Rosters"], dependencies=[Depends(get_current_user)])
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


@app.delete("/duty-rosters/{roster_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Duty Rosters"], dependencies=[Depends(require_roles("admin"))])
def delete_duty_roster(
    roster_id: int, admin_user_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != admin_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik admin.")
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if admin is None or admin.role != "admin" or not admin.is_active:
        raise HTTPException(status_code=403, detail="Hanya admin aktif yang dapat menghapus penugasan.")
    roster = db.query(DutyRoster).filter(DutyRoster.id == roster_id).first()
    if roster is None:
        raise HTTPException(status_code=404, detail="Penugasan piket tidak ditemukan.")
    db.delete(roster)
    add_audit_log(db, current_user.id, "DUTY_ROSTER_DELETED", "DutyRoster", roster_id, "Penugasan guru piket dihapus.")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/reviews/inbox", response_model=list[DailyJournalResponse], tags=["Journal Reviews"], dependencies=[Depends(require_roles("teacher"))])
def get_review_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Antrean pemeriksaan hanya untuk akun guru.")
    return db.query(DailyJournal).filter(
        DailyJournal.status.in_(["SUBMITTED", "RESUBMITTED"])
    ).order_by(DailyJournal.journal_date, DailyJournal.id).all()


@app.post("/journals/{journal_id}/review", response_model=JournalReviewResponse, status_code=status.HTTP_201_CREATED, tags=["Journal Reviews"], dependencies=[Depends(get_current_user)])
def review_daily_journal(
    journal_id: int, data: JournalReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.reviewer_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik guru piket yang memeriksa.")
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

    notification_details = {
        "APPROVE": ("JOURNAL_APPROVED", "Jurnal disetujui", "Jurnal kelas ini telah disetujui oleh guru piket."),
        "REQUEST_REVISION": ("REVISION_REQUESTED", "Jurnal perlu diperbaiki", "Guru piket meminta perbaikan pada jurnal ini."),
        "REJECT": ("JOURNAL_REJECTED", "Jurnal ditolak", "Jurnal kelas ini ditolak oleh guru piket."),
    }
    notification_type, notification_title, notification_message = notification_details[data.decision]
    if data.notes:
        notification_message += f" Catatan: {data.notes.strip()}"
    add_notification(
        db, journal.officer_user_id, journal.id, notification_type,
        notification_title, notification_message,
    )
    add_audit_log(
        db, current_user.id, f"JOURNAL_{data.decision}", "DailyJournal", journal.id,
        f"Guru piket memberi keputusan {data.decision} pada jurnal."
        + (f" Catatan: {data.notes.strip()}" if data.notes else ""),
    )

    db.commit()
    db.refresh(review)
    return JournalReviewResponse(id=review.id, journal_id=review.journal_id, reviewer_user_id=review.reviewer_user_id, reviewer_name=reviewer.full_name, decision=review.decision, notes=review.notes, reviewed_at=review.reviewed_at)


@app.get("/journals/{journal_id}/reviews", response_model=list[JournalReviewResponse], tags=["Journal Reviews"], dependencies=[Depends(get_current_user)])
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


def build_attendance_report(
    db: Session, class_id: int, start_date: date, end_date: date
) -> AttendanceReportResponse:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="Tanggal akhir tidak boleh sebelum tanggal awal.")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="Rentang laporan maksimal 366 hari.")

    classroom = db.query(Classroom).filter(Classroom.id == class_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan.")

    rows = db.query(AttendanceRecord, Student).join(
        Student, Student.id == AttendanceRecord.student_id
    ).join(
        JournalSession, JournalSession.id == AttendanceRecord.session_id
    ).join(
        DailyJournal, DailyJournal.id == JournalSession.journal_id
    ).filter(
        DailyJournal.class_id == class_id,
        DailyJournal.journal_date >= start_date,
        DailyJournal.journal_date <= end_date,
    ).order_by(Student.full_name, DailyJournal.journal_date).all()

    status_counts = {"PRESENT": 0, "SICK": 0, "PERMITTED": 0, "ABSENT": 0}
    student_totals = {}
    for record, student in rows:
        if student.id not in student_totals:
            student_totals[student.id] = {
                "student_id": student.id,
                "nis": student.nis,
                "full_name": student.full_name,
                "present": 0,
                "sick": 0,
                "permitted": 0,
                "absent": 0,
                "total": 0,
            }
        summary = student_totals[student.id]
        field = record.attendance_status.lower()
        if field in summary:
            summary[field] += 1
        if record.attendance_status in status_counts:
            status_counts[record.attendance_status] += 1
        summary["total"] += 1

    return AttendanceReportResponse(
        class_id=classroom.id,
        class_name=classroom.name,
        start_date=start_date,
        end_date=end_date,
        total_records=len(rows),
        status_counts=status_counts,
        students=[
            StudentAttendanceSummary(**item)
            for item in sorted(student_totals.values(), key=lambda row: row["full_name"])
        ],
    )


@app.get(
    "/reports/attendance",
    response_model=AttendanceReportResponse,
    tags=["Reports"],
    dependencies=[Depends(require_roles("admin"))],
)
def get_attendance_report(
    class_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
):
    return build_attendance_report(db, class_id, start_date, end_date)


@app.get(
    "/reports/attendance.csv",
    tags=["Reports"],
    dependencies=[Depends(require_roles("admin"))],
)
def export_attendance_report(
    class_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
):
    report = build_attendance_report(db, class_id, start_date, end_date)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["NIS", "Nama Siswa", "Hadir", "Sakit", "Izin", "Alpa", "Total"])
    for student in report.students:
        writer.writerow([
            student.nis, student.full_name, student.present,
            student.sick, student.permitted, student.absent, student.total,
        ])
    filename = f"absensi_kelas_{class_id}_{start_date}_{end_date}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    tags=["Audit Logs"],
    dependencies=[Depends(require_roles("admin"))],
)
def get_audit_logs(
    journal_id: int | None = None,
    actor_user_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="Limit harus antara 1 sampai 200.")
    query = db.query(AuditLog, User).outerjoin(
        User, AuditLog.actor_user_id == User.id
    )
    if journal_id is not None:
        query = query.filter(
            AuditLog.target_type == "DailyJournal",
            AuditLog.target_id == journal_id,
        )
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).all()
    return [
        AuditLogResponse(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_name=user.full_name if user else None,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log, user in rows
    ]


@app.get(
    "/notifications",
    response_model=list[NotificationResponse],
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)])
def get_notifications(
    user_id: int,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Notifikasi hanya dapat dilihat oleh pemilik akun.")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan atau tidak aktif.")

    query = db.query(Notification).filter(Notification.recipient_user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc(), Notification.id.desc()).all()


@app.put(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)])
def mark_notification_as_read(
    notification_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik penerima notifikasi.")
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan.")
    if notification.recipient_user_id != user_id:
        raise HTTPException(status_code=403, detail="Notifikasi ini bukan milik pengguna tersebut.")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification



@app.get(
    "/dashboard/classes/{class_id}",
    response_model=ClassDashboardResponse,
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)])
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



def build_absence_report_response(db: Session, report: TeacherAbsenceReport):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == report.slot_id).first()
    teacher = db.query(User).filter(User.id == report.scheduled_teacher_id).first()
    officer = db.query(User).filter(User.id == report.reported_by_user_id).first()
    return TeacherAbsenceReportResponse(
        id=report.id,
        journal_id=report.journal_id,
        slot_id=slot.id,
        jp_number=slot.jp_number,
        scheduled_teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        reported_by_user_id=officer.id,
        officer_name=officer.full_name,
        notes=report.notes,
        reported_at=report.reported_at,
    )


@app.post(
    "/journals/{journal_id}/absence-reports",
    response_model=TeacherAbsenceReportResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Teacher Absence"],
    dependencies=[Depends(get_current_user)])
def create_teacher_absence_report(
    journal_id: int,
    data: TeacherAbsenceReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != data.officer_user_id:
        raise HTTPException(status_code=403, detail="Token login harus milik petugas kelas yang melapor.")
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    if journal.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Laporan hanya dapat ditambahkan saat jurnal DRAFT.")
    if data.officer_user_id != journal.officer_user_id:
        raise HTTPException(status_code=403, detail="Hanya petugas jurnal kelas yang ditetapkan yang dapat melapor.")

    officer = db.query(User).filter(User.id == data.officer_user_id).first()
    if officer is None or officer.role != "class_officer" or not officer.is_active:
        raise HTTPException(status_code=403, detail="Pelapor harus petugas kelas yang aktif.")
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

    slot = db.query(ScheduleSlot).filter(
        ScheduleSlot.id == data.slot_id,
        ScheduleSlot.class_id == journal.class_id,
        ScheduleSlot.day_of_week == journal.journal_date.strftime("%A"),
    ).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot jadwal tidak ditemukan untuk kelas dan tanggal jurnal ini.")
    if slot.slot_type != "LESSON" or slot.jp_number is None:
        raise HTTPException(status_code=400, detail="Laporan hanya berlaku untuk slot pelajaran (LESSON).")

    teacher_assignment = db.query(ScheduleTeacherAssignment).filter(
        ScheduleTeacherAssignment.slot_id == slot.id
    ).first()
    if teacher_assignment is None:
        raise HTTPException(status_code=400, detail="Slot belum memiliki guru pengajar terjadwal.")
    teacher = db.query(User).filter(User.id == teacher_assignment.teacher_id).first()
    if teacher is None or teacher.role != "teacher" or not teacher.is_active:
        raise HTTPException(status_code=400, detail="Guru terjadwal tidak aktif atau bukan akun guru.")

    existing_session = db.query(JournalSessionSlot).join(
        JournalSession, JournalSession.id == JournalSessionSlot.session_id
    ).filter(
        JournalSession.journal_id == journal_id,
        JournalSessionSlot.slot_id == slot.id,
    ).first()
    if existing_session is not None:
        raise HTTPException(status_code=400, detail="JP ini sudah memiliki sesi pembelajaran; tidak dapat dilaporkan sebagai guru tidak hadir.")

    existing_report = db.query(TeacherAbsenceReport).filter(
        TeacherAbsenceReport.journal_id == journal_id,
        TeacherAbsenceReport.slot_id == slot.id,
    ).first()
    if existing_report is not None:
        raise HTTPException(status_code=409, detail="Laporan ketidakhadiran untuk JP ini sudah dibuat.")

    report = TeacherAbsenceReport(
        journal_id=journal_id,
        slot_id=slot.id,
        scheduled_teacher_id=teacher.id,
        reported_by_user_id=officer.id,
        notes=data.notes.strip() if data.notes and data.notes.strip() else None,
    )
    db.add(report)
    try:
        db.flush()
        add_audit_log(db, current_user.id, "TEACHER_ABSENCE_REPORTED", "DailyJournal", journal.id, f"Guru {teacher.full_name} dilaporkan tidak hadir pada JP {slot.jp_number}.")
        db.commit()
        db.refresh(report)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Laporan ketidakhadiran untuk JP ini sudah dibuat.")
    return build_absence_report_response(db, report)


@app.get(
    "/journals/{journal_id}/absence-reports",
    response_model=list[TeacherAbsenceReportResponse],
    tags=["Teacher Absence"],
    dependencies=[Depends(get_current_user)])
def get_teacher_absence_reports(journal_id: int, db: Session = Depends(get_db)):
    journal = db.query(DailyJournal).filter(DailyJournal.id == journal_id).first()
    if journal is None:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    reports = db.query(TeacherAbsenceReport).filter(
        TeacherAbsenceReport.journal_id == journal_id
    ).order_by(TeacherAbsenceReport.slot_id).all()
    return [build_absence_report_response(db, report) for report in reports]
