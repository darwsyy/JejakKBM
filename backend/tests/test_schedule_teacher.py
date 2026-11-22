from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


def test_schedule_teacher_assignment():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            classroom = client.post(
                "/classes",
                json={"name": "X TKJ 1", "academic_year": "2026/2027"},
            ).json()
            teacher = client.post(
                "/users",
                json={"username": "guru1", "full_name": "Guru Satu", "role": "teacher"},
            ).json()
            other_teacher = client.post(
                "/users",
                json={"username": "guru2", "full_name": "Guru Dua", "role": "teacher"},
            ).json()
            student = client.post(
                "/users",
                json={"username": "siswa1", "full_name": "Siswa Satu", "role": "class_officer"},
            ).json()

            lesson = client.post(
                f"/classes/{classroom['id']}/schedule-slots",
                json={
                    "day_of_week": "Monday",
                    "slot_order": 1,
                    "jp_number": 1,
                    "start_time": "07:45",
                    "end_time": "08:30",
                    "slot_type": "LESSON",
                },
            ).json()
            lesson_id = lesson["id"]

            assign = client.put(f"/schedule-slots/{lesson_id}/teacher/{teacher['id']}")
            assert assign.status_code == 200
            assert assign.json()["teacher_id"] == teacher["id"]

            get_assignment = client.get(f"/schedule-slots/{lesson_id}/teacher")
            assert get_assignment.status_code == 200
            assert get_assignment.json()["username"] == "guru1"

            replace = client.put(
                f"/schedule-slots/{lesson_id}/teacher/{other_teacher['id']}"
            )
            assert replace.status_code == 200
            assert replace.json()["username"] == "guru2"

            reject_student = client.put(
                f"/schedule-slots/{lesson_id}/teacher/{student['id']}"
            )
            assert reject_student.status_code == 400

            break_slot = client.post(
                f"/classes/{classroom['id']}/schedule-slots",
                json={
                    "day_of_week": "Monday",
                    "slot_order": 2,
                    "jp_number": None,
                    "start_time": "10:00",
                    "end_time": "10:15",
                    "slot_type": "BREAK",
                },
            ).json()
            reject_break = client.put(
                f"/schedule-slots/{break_slot['id']}/teacher/{teacher['id']}"
            )
            assert reject_break.status_code == 400

            remove = client.delete(f"/schedule-slots/{lesson_id}/teacher")
            assert remove.status_code == 204
            assert client.get(f"/schedule-slots/{lesson_id}/teacher").status_code == 404
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
