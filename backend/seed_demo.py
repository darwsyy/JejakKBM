from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401 - mendaftarkan semua model
from app.models import (
    ClassOfficerPeriod, Classroom, DutyRoster, ScheduleSlot, ScheduleSubjectAssignment,
    ScheduleTeacherAssignment, Student, Subject, Teacher, User,
)

def get_or_create_user(db, username, full_name, role):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        user = User(username=username, full_name=full_name, role=role)
        db.add(user)
        db.flush()
    return user


def seed_demo(db):
    # Akun contoh untuk mencoba setiap peran dasar. Belum memakai password/login.
    admin = get_or_create_user(db, "demo_admin", "Admin Demo", "admin")
    teacher_user = get_or_create_user(db, "demo_guru", "Guru Demo", "teacher")
    officer_user = get_or_create_user(
        db, "demo_petugas", "Petugas Demo", "class_officer"
    )

    classroom = db.query(Classroom).filter(
        Classroom.name == "DEMO X TKJ 1"
    ).first()
    if classroom is None:
        classroom = Classroom(name="DEMO X TKJ 1", academic_year="2026/2027")
        db.add(classroom)
        db.flush()

    teacher = db.query(Teacher).filter(Teacher.user_id == teacher_user.id).first()
    if teacher is None:
        teacher = Teacher(user_id=teacher_user.id, nip="DEMO-GURU-001")
        db.add(teacher)

    subject = db.query(Subject).filter(Subject.name == "Matematika").first()
    if subject is None:
        subject = Subject(name="Matematika")
        db.add(subject)
        db.flush()

    student = db.query(Student).filter(Student.nis == "DEMO1001").first()
    if student is None:
        student = Student(
            nis="DEMO1001",
            full_name="Siswa Demo",
            class_id=classroom.id,
        )
        db.add(student)
        db.flush()

    # Jadwal contoh: dua JP pelajaran berurutan pada hari Senin.
    demo_slots = [
        (1, 2, "08:30", "09:15"),
        (2, 3, "09:15", "10:00"),
    ]
    for order, jp, start, end in demo_slots:
        slot = db.query(ScheduleSlot).filter(
            ScheduleSlot.class_id == classroom.id,
            ScheduleSlot.day_of_week == "Monday",
            ScheduleSlot.slot_order == order,
        ).first()
        if slot is None:
            slot = ScheduleSlot(
                class_id=classroom.id,
                day_of_week="Monday",
                slot_order=order,
                jp_number=jp,
                start_time=start,
                end_time=end,
                slot_type="LESSON",
            )
            db.add(slot)
            db.flush()

        subject_assignment = db.query(ScheduleSubjectAssignment).filter(
            ScheduleSubjectAssignment.slot_id == slot.id
        ).first()
        if subject_assignment is None:
            db.add(ScheduleSubjectAssignment(
                slot_id=slot.id, subject_id=subject.id
            ))

        teacher_assignment = db.query(ScheduleTeacherAssignment).filter(
            ScheduleTeacherAssignment.slot_id == slot.id
        ).first()
        if teacher_assignment is None:
            db.add(ScheduleTeacherAssignment(
                slot_id=slot.id, teacher_id=teacher_user.id
            ))

    officer_period = db.query(ClassOfficerPeriod).filter(
        ClassOfficerPeriod.class_id == classroom.id,
        ClassOfficerPeriod.user_id == officer_user.id,
    ).first()
    if officer_period is None:
        db.add(ClassOfficerPeriod(
            class_id=classroom.id,
            user_id=officer_user.id,
            start_date=date(2026, 7, 1),
            end_date=None,
        ))

    # Pilih Senin terdekat agar jadwal contoh dan jadwal piket cocok.
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    duty_date = today + timedelta(days=days_until_monday)

    duty_roster = db.query(DutyRoster).filter(
        DutyRoster.duty_date == duty_date,
        DutyRoster.teacher_user_id == teacher_user.id,
    ).first()
    if duty_roster is None:
        db.add(DutyRoster(
            duty_date=duty_date,
            teacher_user_id=teacher_user.id,
            assigned_by_user_id=admin.id,
        ))

    db.commit()
    return {
        "users": [admin.username, teacher_user.username, officer_user.username],
        "user_ids": [admin.id, teacher_user.id, officer_user.id],
        "class": classroom.name,
        "class_id": classroom.id,
        "subject": subject.name,
        "student": student.nis,
        "student_id": student.id,
        "duty_date": duty_date.isoformat(),
    }


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_demo(db)
        print("Data demo berhasil disiapkan:")
        for key, value in result.items():
            print(f"- {key}: {value}")
        print("Jalankan lagi dengan aman; data yang sudah ada tidak dibuat ulang.")
    finally:
        db.close()
