import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def create_user(client, username, role="class_officer"):
    return client.post(
        "/users",
        json={
            "username": username,
            "full_name": f"Nama {username}",
            "role": role,
        },
    )


def create_classroom(client, name):
    return client.post(
        "/classes",
        json={
            "name": name,
            "academic_year": "2026/2027",
        },
    )


def test_create_and_list_user(client):
    response = client.post(
        "/users",
        json={
            "username": "petugas1",
            "full_name": "Petugas Kelas",
            "role": "class_officer",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "petugas1"

    list_response = client.get("/users")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_duplicate_username_is_rejected(client):
    user_data = {
        "username": "guru1",
        "full_name": "Guru Satu",
        "role": "teacher",
    }

    first_response = client.post("/users", json=user_data)
    second_response = client.post("/users", json=user_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_and_list_classroom(client):
    response = create_classroom(client, "X TKJ 1")

    assert response.status_code == 201
    assert response.json()["name"] == "X TKJ 1"

    list_response = client.get("/classes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_assign_and_get_class_officer(client):
    user_response = create_user(client, "petugas1")
    class_response = create_classroom(client, "X TKJ 1")

    user_id = user_response.json()["id"]
    class_id = class_response.json()["id"]

    assign_response = client.put(f"/classes/{class_id}/officer/{user_id}")

    assert assign_response.status_code == 200
    assert assign_response.json()["username"] == "petugas1"
    assert assign_response.json()["class_name"] == "X TKJ 1"

    get_response = client.get(f"/classes/{class_id}/officer")
    assert get_response.status_code == 200
    assert get_response.json()["user_id"] == user_id


def test_teacher_cannot_be_assigned_as_class_officer(client):
    user_response = create_user(client, "guru1", role="teacher")
    class_response = create_classroom(client, "X TKJ 1")

    response = client.put(
        f"/classes/{class_response.json()['id']}/officer/{user_response.json()['id']}"
    )

    assert response.status_code == 400


def test_class_cannot_have_two_primary_officers(client):
    first_user = create_user(client, "petugas1")
    second_user = create_user(client, "petugas2")
    classroom = create_classroom(client, "X TKJ 1")
    class_id = classroom.json()["id"]

    first_response = client.put(
        f"/classes/{class_id}/officer/{first_user.json()['id']}"
    )
    second_response = client.put(
        f"/classes/{class_id}/officer/{second_user.json()['id']}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_officer_cannot_be_assigned_to_two_classes(client):
    user = create_user(client, "petugas1")
    first_class = create_classroom(client, "X TKJ 1")
    second_class = create_classroom(client, "X TKJ 2")
    user_id = user.json()["id"]

    first_response = client.put(
        f"/classes/{first_class.json()['id']}/officer/{user_id}"
    )
    second_response = client.put(
        f"/classes/{second_class.json()['id']}/officer/{user_id}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


@pytest.mark.parametrize(
    ("class_id", "user_id"),
    [(999, 1), (1, 999)],
)
def test_assignment_rejects_missing_class_or_user(client, class_id, user_id):
    response = client.put(f"/classes/{class_id}/officer/{user_id}")

    assert response.status_code == 404


def test_create_and_list_schedule_slots(client):
    classroom = create_classroom(client, "X TKJ 1")
    class_id = classroom.json()["id"]

    response = client.post(
        f"/classes/{class_id}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": 1,
            "start_time": "07:45",
            "end_time": "08:30",
            "slot_type": "LESSON",
        },
    )

    assert response.status_code == 201
    assert response.json()["slot_type"] == "LESSON"

    list_response = client.get(f"/classes/{class_id}/schedule-slots?day=Monday")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_schedule_slot_rejects_invalid_jp_duration(client):
    classroom = create_classroom(client, "X TKJ 1")

    response = client.post(
        f"/classes/{classroom.json()['id']}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": 1,
            "start_time": "07:45",
            "end_time": "08:20",
            "slot_type": "LESSON",
        },
    )

    assert response.status_code == 422


def test_schedule_slot_rejects_duplicate_order(client):
    classroom = create_classroom(client, "X TKJ 1")
    class_id = classroom.json()["id"]
    slot_data = {
        "day_of_week": "Monday",
        "slot_order": 1,
        "jp_number": 1,
        "start_time": "07:45",
        "end_time": "08:30",
        "slot_type": "LESSON",
    }

    first_response = client.post(
        f"/classes/{class_id}/schedule-slots", json=slot_data
    )
    second_response = client.post(
        f"/classes/{class_id}/schedule-slots",
        json={**slot_data, "jp_number": 2, "start_time": "08:30", "end_time": "09:15"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_schedule_slot_can_be_updated_and_deleted(client):
    classroom = create_classroom(client, "X TKJ 1")
    class_id = classroom.json()["id"]
    response = client.post(
        f"/classes/{class_id}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": None,
            "start_time": "10:00",
            "end_time": "10:15",
            "slot_type": "BREAK",
        },
    )
    slot_id = response.json()["id"]

    update_response = client.put(
        f"/schedule-slots/{slot_id}",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": None,
            "start_time": "10:00",
            "end_time": "10:15",
            "slot_type": "SPECIAL_EVENT",
        },
    )
    delete_response = client.delete(f"/schedule-slots/{slot_id}")

    assert update_response.status_code == 200
    assert update_response.json()["slot_type"] == "SPECIAL_EVENT"
    assert delete_response.status_code == 204
    assert client.get(f"/classes/{class_id}/schedule-slots").json() == []


def test_schedule_slot_requires_existing_class(client):
    response = client.post(
        "/classes/999/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": 1,
            "start_time": "07:45",
            "end_time": "08:30",
            "slot_type": "LESSON",
        },
    )

    assert response.status_code == 404


def test_create_and_list_subjects(client):
    first = client.post("/subjects", json={"name": "Matematika"})
    second = client.post("/subjects", json={"name": "Bahasa Indonesia"})

    assert first.status_code == 201
    assert first.json()["name"] == "Matematika"
    assert second.status_code == 201

    response = client.get("/subjects")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [
        "Bahasa Indonesia", "Matematika"
    ]


def test_duplicate_subject_name_is_rejected(client):
    first = client.post("/subjects", json={"name": "Matematika"})
    second = client.post("/subjects", json={"name": "Matematika"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_assign_get_change_and_remove_schedule_subject(client):
    classroom = create_classroom(client, "X TKJ 1")
    slot_response = client.post(
        f"/classes/{classroom.json()['id']}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": 1,
            "start_time": "07:45",
            "end_time": "08:30",
            "slot_type": "LESSON",
        },
    )
    slot_id = slot_response.json()["id"]
    first_subject = client.post("/subjects", json={"name": "Matematika"}).json()
    second_subject = client.post("/subjects", json={"name": "Fisika"}).json()

    assign = client.put(
        f"/schedule-slots/{slot_id}/subject/{first_subject['id']}"
    )
    get_response = client.get(f"/schedule-slots/{slot_id}/subject")
    change = client.put(
        f"/schedule-slots/{slot_id}/subject/{second_subject['id']}"
    )
    delete_response = client.delete(f"/schedule-slots/{slot_id}/subject")

    assert assign.status_code == 200
    assert assign.json()["subject_name"] == "Matematika"
    assert get_response.status_code == 200
    assert get_response.json()["subject_id"] == first_subject["id"]
    assert change.status_code == 200
    assert change.json()["subject_name"] == "Fisika"
    assert delete_response.status_code == 204
    assert client.get(f"/schedule-slots/{slot_id}/subject").status_code == 404


def test_subject_cannot_be_assigned_to_non_lesson_slot(client):
    classroom = create_classroom(client, "X TKJ 1")
    slot_response = client.post(
        f"/classes/{classroom.json()['id']}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": None,
            "start_time": "10:00",
            "end_time": "10:15",
            "slot_type": "BREAK",
        },
    )
    subject = client.post("/subjects", json={"name": "Matematika"}).json()

    response = client.put(
        f"/schedule-slots/{slot_response.json()['id']}/subject/{subject['id']}"
    )
    assert response.status_code == 400


def test_subject_assignment_rejects_missing_slot_or_subject(client):
    classroom = create_classroom(client, "X TKJ 1")
    slot_response = client.post(
        f"/classes/{classroom.json()['id']}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": 1,
            "start_time": "07:45",
            "end_time": "08:30",
            "slot_type": "LESSON",
        },
    )
    slot_id = slot_response.json()["id"]
    subject = client.post("/subjects", json={"name": "Matematika"}).json()

    missing_slot = client.put(f"/schedule-slots/999/subject/{subject['id']}")
    missing_subject = client.put(f"/schedule-slots/{slot_id}/subject/999")

    assert missing_slot.status_code == 404
    assert missing_subject.status_code == 404


def test_create_list_and_filter_students(client):
    first_class = create_classroom(client, "X TKJ 1").json()
    second_class = create_classroom(client, "X TKJ 2").json()

    first = client.post("/students", json={
        "nis": "10001", "full_name": "Andi Saputra", "class_id": first_class["id"]
    })
    second = client.post("/students", json={
        "nis": "10002", "full_name": "Budi Santoso", "class_id": second_class["id"]
    })

    assert first.status_code == 201
    assert first.json()["is_active"] is True
    assert second.status_code == 201
    assert len(client.get("/students").json()) == 2
    filtered = client.get(f"/students?class_id={first_class['id']}")
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["nis"] == "10001"


def test_student_nis_must_be_unique(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    data = {"nis": "10001", "full_name": "Andi Saputra", "class_id": classroom["id"]}

    first = client.post("/students", json=data)
    second = client.post("/students", json={**data, "full_name": "Budi Santoso"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_student_requires_existing_class(client):
    response = client.post("/students", json={
        "nis": "10001", "full_name": "Andi Saputra", "class_id": 999
    })
    assert response.status_code == 404


def test_student_can_be_updated_and_moved_to_another_class(client):
    first_class = create_classroom(client, "X TKJ 1").json()
    second_class = create_classroom(client, "X TKJ 2").json()
    student = client.post("/students", json={
        "nis": "10001", "full_name": "Andi Saputra", "class_id": first_class["id"]
    }).json()

    response = client.put(f"/students/{student['id']}", json={
        "nis": "10001", "full_name": "Andi Pratama", "class_id": second_class["id"]
    })

    assert response.status_code == 200
    assert response.json()["full_name"] == "Andi Pratama"
    assert response.json()["class_id"] == second_class["id"]


def test_student_can_be_deactivated_without_deleting_record(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    student = client.post("/students", json={
        "nis": "10001", "full_name": "Andi Saputra", "class_id": classroom["id"]
    }).json()

    response = client.delete(f"/students/{student['id']}")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert len(client.get("/students").json()) == 1


def test_student_endpoints_reject_unknown_ids(client):
    assert client.get("/students?class_id=999").status_code == 404
    assert client.put("/students/999", json={
        "nis": "10001", "full_name": "Andi Saputra", "class_id": 1
    }).status_code == 404
    assert client.delete("/students/999").status_code == 404


def test_create_and_list_teacher_profiles(client):
    user = create_user(client, "guru1", role="teacher").json()
    response = client.post("/teachers", json={"user_id": user["id"], "nip": "1987001"})

    assert response.status_code == 201
    assert response.json()["full_name"] == user["full_name"]
    assert response.json()["nip"] == "1987001"
    listed = client.get("/teachers")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_teacher_profile_requires_teacher_account(client):
    user = create_user(client, "petugas1", role="class_officer").json()
    response = client.post("/teachers", json={"user_id": user["id"]})
    assert response.status_code == 400


def test_teacher_profile_rejects_missing_or_duplicate_user(client):
    missing = client.post("/teachers", json={"user_id": 999})
    user = create_user(client, "guru1", role="teacher").json()
    first = client.post("/teachers", json={"user_id": user["id"]})
    second = client.post("/teachers", json={"user_id": user["id"]})

    assert missing.status_code == 404
    assert first.status_code == 201
    assert second.status_code == 409


def test_teacher_nip_must_be_unique(client):
    first_user = create_user(client, "guru1", role="teacher").json()
    second_user = create_user(client, "guru2", role="teacher").json()
    first = client.post("/teachers", json={"user_id": first_user["id"], "nip": "1987001"})
    second = client.post("/teachers", json={"user_id": second_user["id"], "nip": "1987001"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_teacher_profile_can_be_updated_and_deactivated(client):
    user = create_user(client, "guru1", role="teacher").json()
    teacher = client.post("/teachers", json={"user_id": user["id"], "nip": "1987001"}).json()

    updated = client.put(f"/teachers/{teacher['id']}", json={"nip": "1987002"})
    deactivated = client.delete(f"/teachers/{teacher['id']}")

    assert updated.status_code == 200
    assert updated.json()["nip"] == "1987002"
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False


def test_teacher_profile_endpoints_reject_unknown_id(client):
    assert client.put("/teachers/999", json={"nip": "123"}).status_code == 404
    assert client.delete("/teachers/999").status_code == 404
