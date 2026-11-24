from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app


class TestActorId:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


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
    # Aktor admin default untuk pengujian alur bisnis lama.
    test_admin = SimpleNamespace(
        id=TestActorId(), username="test_admin", full_name="Test Admin",
        role="admin", is_active=True, password_hash=None, token_version=0,
    )
    app.dependency_overrides[get_current_user] = lambda: test_admin

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


def test_create_classroom_also_creates_one_officer_account(client):
    response = client.post(
        "/classes/create-with-officer",
        json={
            "name": "XI TITL 3",
            "academic_year": "2026/2027",
            "officer_full_name": "Petugas XI TITL 3",
            "officer_password": "password123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["classroom"]["name"] == "XI TITL 3"
    assert payload["officer"]["username"] == "petugas_xi_titl_3"
    assert payload["officer"]["role"] == "class_officer"

    users = client.get("/users").json()
    assert len(users) == 1
    assert users[0]["username"] == "petugas_xi_titl_3"

    officer = client.get(
        f"/classes/{payload['classroom']['id']}/officer"
    )
    assert officer.status_code == 200
    assert officer.json()["user_id"] == payload["officer"]["id"]


def test_create_classroom_with_officer_creates_configured_attendance_numbers(client):
    response = client.post(
        "/classes/create-with-officer",
        json={
            "name": "XI RPL 2",
            "academic_year": "2026/2027",
            "officer_full_name": "Petugas XI RPL 2",
            "officer_password": "password123",
            "roster_size": 36,
        },
    )
    assert response.status_code == 201
    class_id = response.json()["classroom"]["id"]
    roster = client.get(f"/classes/{class_id}/roster")
    assert roster.status_code == 200
    assert len(roster.json()) == 36
    assert roster.json()[0]["attendance_number"] == 1
    assert roster.json()[-1]["attendance_number"] == 36


def test_create_classroom_with_officer_rolls_back_on_duplicate_class(client):
    request_data = {
        "name": "XI TITL 3",
        "academic_year": "2026/2027",
        "officer_full_name": "Petugas XI TITL 3",
        "officer_password": "password123",
    }
    first = client.post("/classes/create-with-officer", json=request_data)
    second = client.post("/classes/create-with-officer", json=request_data)

    assert first.status_code == 201
    assert second.status_code == 409
    assert len(client.get("/classes").json()) == 1
    assert len(client.get("/users").json()) == 1


def test_create_teacher_account_and_code_together(client):
    response = client.post(
        "/teachers/create-with-account",
        json={
            "username": "guru_matematika",
            "full_name": "Guru Matematika",
            "password": "password123",
            "teacher_code": "G-014",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "guru_matematika"
    assert payload["full_name"] == "Guru Matematika"
    assert payload["nip"] == "G-014"
    assert payload["is_active"] is True
    assert len(client.get("/users").json()) == 1
    assert len(client.get("/teachers").json()) == 1


def test_create_teacher_account_rolls_back_when_username_or_code_is_duplicate(client):
    request_data = {
        "username": "guru_matematika",
        "full_name": "Guru Matematika",
        "password": "password123",
        "teacher_code": "G-014",
    }
    first = client.post("/teachers/create-with-account", json=request_data)
    second = client.post(
        "/teachers/create-with-account",
        json={
            **request_data,
            "username": "guru_fisika",
            "teacher_code": "G-014",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert len(client.get("/users").json()) == 1
    assert len(client.get("/teachers").json()) == 1


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


def test_update_subject_name_and_reject_duplicate(client):
    first = client.post("/subjects", json={"name": "Matematika"}).json()
    second = client.post("/subjects", json={"name": "Fisika"}).json()

    updated = client.put(f"/subjects/{first['id']}", json={"name": "Matematika Lanjut"})
    duplicate = client.put(f"/subjects/{first['id']}", json={"name": "Fisika"})
    missing = client.put("/subjects/999", json={"name": "Kimia"})

    assert updated.status_code == 200
    assert updated.json()["name"] == "Matematika Lanjut"
    assert duplicate.status_code == 409
    assert missing.status_code == 404
    assert client.get("/subjects").json()[0]["id"] == second["id"]


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


def test_class_officer_period_history_and_current_lookup(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    first_user = create_user(client, "petugas1", role="class_officer").json()
    second_user = create_user(client, "petugas2", role="class_officer").json()

    first = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": first_user["id"],
        "start_date": "2026-07-01",
        "end_date": "2026-12-31",
    })
    second = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": second_user["id"],
        "start_date": "2027-01-01",
        "end_date": None,
    })

    assert first.status_code == 201
    assert second.status_code == 201
    history = client.get(f"/classes/{classroom['id']}/officer-periods")
    assert len(history.json()) == 2
    assert history.json()[0]["username"] == "petugas1"
    current = client.get(
        f"/classes/{classroom['id']}/officer-current?on_date=2027-02-01"
    )
    assert current.status_code == 200
    assert current.json()["username"] == "petugas2"


def test_class_officer_period_rejects_overlapping_dates(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    first_user = create_user(client, "petugas1", role="class_officer").json()
    second_user = create_user(client, "petugas2", role="class_officer").json()
    first = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": first_user["id"], "start_date": "2026-07-01", "end_date": "2026-12-31"
    })
    overlap = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": second_user["id"], "start_date": "2026-12-01", "end_date": None
    })

    assert first.status_code == 201
    assert overlap.status_code == 409


def test_class_officer_period_requires_valid_user_and_class(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    teacher = create_user(client, "guru1", role="teacher").json()
    invalid_role = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": teacher["id"], "start_date": "2026-07-01"
    })
    missing_class = client.post("/classes/999/officer-periods", json={
        "user_id": teacher["id"], "start_date": "2026-07-01"
    })
    missing_user = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": 999, "start_date": "2026-07-01"
    })

    assert invalid_role.status_code == 400
    assert missing_class.status_code == 404
    assert missing_user.status_code == 404


def test_class_officer_period_rejects_end_date_before_start_date(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    user = create_user(client, "petugas1", role="class_officer").json()
    response = client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": user["id"], "start_date": "2026-12-31", "end_date": "2026-07-01"
    })
    assert response.status_code == 422


def test_class_officer_current_lookup_returns_not_found_when_unassigned(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    response = client.get(f"/classes/{classroom['id']}/officer-current?on_date=2026-07-01")
    assert response.status_code == 404


def test_seed_demo_creates_sample_data_and_is_repeatable():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    from app.models import ClassOfficerPeriod, Classroom, ScheduleSlot, Student, User
    from seed_demo import seed_demo

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    try:
        with TestingSession() as db:
            first_result = seed_demo(db)
            second_result = seed_demo(db)

            assert first_result == second_result
            assert db.query(User).count() == 3
            assert db.query(Classroom).count() == 1
            assert db.query(Student).count() == 1
            assert db.query(ScheduleSlot).count() == 2
            assert db.query(ClassOfficerPeriod).count() == 1
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def create_officer_period(client, class_id, user_id, start="2026-01-01", end=None):
    return client.post(f"/classes/{class_id}/officer-periods", json={
        "user_id": user_id, "start_date": start, "end_date": end
    })


def test_create_daily_journal_and_get_details(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas1").json()
    create_officer_period(client, classroom["id"], officer["id"])

    response = client.post("/journals", json={
        "class_id": classroom["id"],
        "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    })

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"
    detail = client.get(f"/journals/{response.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["class_id"] == classroom["id"]


def test_daily_journal_creation_is_idempotent(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas1").json()
    create_officer_period(client, classroom["id"], officer["id"])
    data = {
        "class_id": classroom["id"],
        "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    }

    first = client.post("/journals", json=data)
    second = client.post("/journals", json=data)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/journals").json()) == 1


def test_daily_journal_requires_current_class_officer(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas1").json()
    response = client.post("/journals", json={
        "class_id": classroom["id"],
        "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    })
    assert response.status_code == 403


def test_daily_journal_rejects_invalid_class_or_user(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    teacher = create_user(client, "guru1", role="teacher").json()
    invalid_role = client.post("/journals", json={
        "class_id": classroom["id"], "journal_date": "2026-11-23",
        "officer_user_id": teacher["id"],
    })
    missing_class = client.post("/journals", json={
        "class_id": 999, "journal_date": "2026-11-23",
        "officer_user_id": teacher["id"],
    })
    missing_user = client.post("/journals", json={
        "class_id": classroom["id"], "journal_date": "2026-11-23",
        "officer_user_id": 999,
    })

    assert invalid_role.status_code == 400
    assert missing_class.status_code == 404
    assert missing_user.status_code == 404


def test_list_daily_journals_can_filter_by_class_and_date(client):
    first_class = create_classroom(client, "X TKJ 1").json()
    second_class = create_classroom(client, "X TKJ 2").json()
    first_officer = create_user(client, "petugas1").json()
    second_officer = create_user(client, "petugas2").json()
    create_officer_period(client, first_class["id"], first_officer["id"])
    create_officer_period(client, second_class["id"], second_officer["id"])

    for classroom, officer, day in [
        (first_class, first_officer, "2026-11-23"),
        (second_class, second_officer, "2026-11-23"),
        (first_class, first_officer, "2026-11-24"),
    ]:
        client.post("/journals", json={
            "class_id": classroom["id"], "journal_date": day,
            "officer_user_id": officer["id"],
        })

    assert len(client.get(f"/journals?class_id={first_class['id']}").json()) == 2
    assert len(client.get("/journals?journal_date=2026-11-23").json()) == 2
    assert len(client.get("/journals").json()) == 3


def test_daily_journal_detail_returns_404_for_unknown_id(client):
    assert client.get("/journals/999").status_code == 404


def setup_journal_with_two_lesson_slots(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas1").json()
    teacher = create_user(client, "guru1", role="teacher").json()
    create_officer_period(client, classroom["id"], officer["id"])
    journal = client.post("/journals", json={
        "class_id": classroom["id"], "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    }).json()
    subject = client.post("/subjects", json={"name": "Matematika"}).json()
    slot_ids = []
    for order, jp, start, end in [(1, 2, "08:30", "09:15"), (2, 3, "09:15", "10:00")]:
        slot = client.post(f"/classes/{classroom['id']}/schedule-slots", json={
            "day_of_week": "Monday", "slot_order": order, "jp_number": jp,
            "start_time": start, "end_time": end, "slot_type": "LESSON",
        }).json()
        slot_ids.append(slot["id"])
        client.put(f"/schedule-slots/{slot['id']}/teacher/{teacher['id']}")
        client.put(f"/schedule-slots/{slot['id']}/subject/{subject['id']}")
    return journal, teacher, slot_ids


def test_create_journal_session_with_two_consecutive_jps(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    response = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": slot_ids, "teacher_id": teacher["id"],
        "material": "Pengenalan aljabar",
        "actual_start_time": "08:35", "actual_end_time": "09:55",
    })

    assert response.status_code == 201
    assert response.json()["jp_numbers"] == [2, 3]
    assert response.json()["subject_name"] == "Matematika"
    assert len(client.get(f"/journals/{journal['id']}/sessions").json()) == 1


def test_journal_session_rejects_non_consecutive_jps(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    # JP 2 dan JP 4 dipisahkan oleh slot istirahat / slot jadwal lain.
    third = client.post(f"/classes/1/schedule-slots", json={
        "day_of_week": "Monday", "slot_order": 4, "jp_number": 4,
        "start_time": "10:15", "end_time": "11:00", "slot_type": "LESSON",
    }).json()
    client.put(f"/schedule-slots/{third['id']}/teacher/{teacher['id']}")
    subject = client.get(f"/schedule-slots/{slot_ids[0]}/subject").json()
    client.put(f"/schedule-slots/{third['id']}/subject/{subject['subject_id']}")
    response = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": [slot_ids[0], third["id"]], "teacher_id": teacher["id"],
        "material": "Materi", "actual_start_time": "08:30", "actual_end_time": "11:00",
    })
    assert response.status_code == 400


def test_journal_session_rejects_wrong_teacher_or_missing_schedule_assignment(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    other_teacher = create_user(client, "guru2", role="teacher").json()
    response = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": slot_ids, "teacher_id": other_teacher["id"],
        "material": "Materi", "actual_start_time": "07:00", "actual_end_time": "08:30",
    })
    assert response.status_code == 400


def test_journal_session_cannot_reuse_a_slot(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    data = {
        "slot_ids": [slot_ids[0]], "teacher_id": teacher["id"],
        "material": "Materi", "actual_start_time": "08:30", "actual_end_time": "09:10",
    }
    first = client.post(f"/journals/{journal['id']}/sessions", json=data)
    second = client.post(f"/journals/{journal['id']}/sessions", json=data)
    assert first.status_code == 201
    assert second.status_code == 409


def test_journal_session_rejects_invalid_actual_time_and_empty_material(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    invalid_time = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": [slot_ids[0]], "teacher_id": teacher["id"],
        "material": "Materi", "actual_start_time": "08:00", "actual_end_time": "07:00",
    })
    empty_material = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": [slot_ids[0]], "teacher_id": teacher["id"],
        "material": "  ", "actual_start_time": "08:30", "actual_end_time": "09:10",
    })
    assert invalid_time.status_code == 422
    assert empty_material.status_code == 422


def test_journal_session_rejects_missing_journal_and_lists_empty_sessions(client):
    assert client.post("/journals/999/sessions", json={
        "slot_ids": [1], "teacher_id": 1, "material": "Materi",
        "actual_start_time": "08:30", "actual_end_time": "09:10",
    }).status_code == 404
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas1").json()
    create_officer_period(client, classroom["id"], officer["id"])
    journal = client.post("/journals", json={
        "class_id": classroom["id"], "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    }).json()
    assert client.get(f"/journals/{journal['id']}/sessions").json() == []


def setup_session_with_student(client):
    journal, teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    student = client.post("/students", json={
        "nis": "S001", "full_name": "Siswa Satu",
        "class_id": 1,
    }).json()
    session = client.post(f"/journals/{journal['id']}/sessions", json={
        "slot_ids": slot_ids, "teacher_id": teacher["id"],
        "material": "Materi pengantar",
        "actual_start_time": "08:35", "actual_end_time": "09:55",
    }).json()
    return session, teacher, student, slot_ids


def test_teacher_can_record_attendance_by_class_number(client):
    session, teacher, _student, slot_ids = setup_session_with_student(client)
    roster = client.put(
        "/classes/1/roster",
        json={"roster_size": 3},
    )
    assert roster.status_code == 200
    assert [item["attendance_number"] for item in roster.json()] == [1, 2, 3]

    response = client.post(
        f"/journal-sessions/{session['id']}/class-attendance",
        json={
            "slot_id": slot_ids[0],
            "teacher_id": teacher["id"],
            "records": [
                {"attendance_number": 1, "attendance_status": "PRESENT"},
                {"attendance_number": 2, "attendance_status": "SICK"},
                {"attendance_number": 3, "attendance_status": "PERMITTED"},
            ],
        },
    )
    assert response.status_code == 201
    assert [row["attendance_number"] for row in response.json()] == [1, 2, 3]
    assert {row["attendance_status"] for row in response.json()} == {
        "PRESENT", "SICK", "PERMITTED"
    }

    completeness = client.get(
        f"/journal-sessions/{session['id']}/attendance/completeness?slot_id={slot_ids[0]}"
    ).json()[0]
    assert completeness["total_students"] == 3
    assert completeness["recorded_count"] == 3
    assert completeness["missing_count"] == 0


def test_class_number_attendance_rejects_unregistered_number(client):
    session, teacher, _student, slot_ids = setup_session_with_student(client)
    client.put("/classes/1/roster", json={"roster_size": 2})
    response = client.post(
        f"/journal-sessions/{session['id']}/class-attendance",
        json={
            "slot_id": slot_ids[0],
            "teacher_id": teacher["id"],
            "records": [
                {"attendance_number": 1, "attendance_status": "PRESENT"},
                {"attendance_number": 3, "attendance_status": "ABSENT"},
            ],
        },
    )
    assert response.status_code == 400
    assert client.get(
        f"/journal-sessions/{session['id']}/class-attendance"
    ).json() == []


def test_teacher_can_record_attendance_per_student_and_jp(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": teacher["id"], "attendance_status": "PRESENT",
    })
    assert response.status_code == 201
    assert response.json()["jp_number"] == 2
    assert response.json()["attendance_status"] == "PRESENT"
    assert len(client.get(f"/journal-sessions/{session['id']}/attendance").json()) == 1


def test_teacher_can_record_same_student_for_each_jp(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id, "student_id": student["id"],
            "teacher_id": teacher["id"], "attendance_status": "PRESENT",
        })
        assert response.status_code == 201
    assert len(client.get(f"/journal-sessions/{session['id']}/attendance").json()) == 2


def test_attendance_rejects_non_teaching_user(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    officer = create_user(client, "petugas2", role="class_officer").json()
    response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": officer["id"], "attendance_status": "PRESENT",
    })
    assert response.status_code == 403


def test_attendance_rejects_student_from_another_class(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    other_class = create_classroom(client, "X TKJ 2").json()
    other_student = client.post("/students", json={
        "nis": "S002", "full_name": "Siswa Dua",
        "class_id": other_class["id"],
    }).json()
    response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0], "student_id": other_student["id"],
        "teacher_id": teacher["id"], "attendance_status": "PRESENT",
    })
    assert response.status_code == 400


def test_attendance_rejects_slot_outside_session_and_duplicate_record(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    data = {
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": teacher["id"], "attendance_status": "SICK",
    }
    first = client.post(f"/journal-sessions/{session['id']}/attendance", json=data)
    duplicate = client.post(f"/journal-sessions/{session['id']}/attendance", json=data)
    invalid_slot = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        **data, "slot_id": 999, "student_id": student["id"],
    })
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert invalid_slot.status_code == 400


def test_attendance_rejects_invalid_status_and_unknown_session(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    invalid = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": teacher["id"], "attendance_status": "UNKNOWN",
    })
    missing = client.post("/journal-sessions/999/attendance", json={
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": teacher["id"], "attendance_status": "PRESENT",
    })
    assert invalid.status_code == 422
    assert missing.status_code == 404



def test_batch_attendance_records_multiple_students(client):
    session, teacher, first_student, slot_ids = setup_session_with_student(client)
    second_student = client.post("/students", json={
        "nis": "S002", "full_name": "Siswa Dua", "class_id": 1,
    }).json()
    response = client.post(f"/journal-sessions/{session['id']}/attendance/batch", json={
        "slot_id": slot_ids[0], "teacher_id": teacher["id"],
        "records": [
            {"student_id": first_student["id"], "attendance_status": "PRESENT"},
            {"student_id": second_student["id"], "attendance_status": "SICK"},
        ],
    })
    assert response.status_code == 201
    assert len(response.json()) == 2
    assert {item["attendance_status"] for item in response.json()} == {"PRESENT", "SICK"}


def test_batch_attendance_rejects_duplicate_students_in_payload(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    response = client.post(f"/journal-sessions/{session['id']}/attendance/batch", json={
        "slot_id": slot_ids[0], "teacher_id": teacher["id"],
        "records": [
            {"student_id": student["id"], "attendance_status": "PRESENT"},
            {"student_id": student["id"], "attendance_status": "ABSENT"},
        ],
    })
    assert response.status_code == 422


def test_batch_attendance_rejects_wrong_class_without_partial_save(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    other_class = create_classroom(client, "X TKJ 2").json()
    other_student = client.post("/students", json={
        "nis": "S099", "full_name": "Siswa Lain", "class_id": other_class["id"],
    }).json()
    response = client.post(f"/journal-sessions/{session['id']}/attendance/batch", json={
        "slot_id": slot_ids[0], "teacher_id": teacher["id"],
        "records": [
            {"student_id": student["id"], "attendance_status": "PRESENT"},
            {"student_id": other_student["id"], "attendance_status": "ABSENT"},
        ],
    })
    assert response.status_code == 400
    assert client.get(f"/journal-sessions/{session['id']}/attendance").json() == []


def test_batch_attendance_rejects_existing_records(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    data = {
        "slot_id": slot_ids[0], "teacher_id": teacher["id"],
        "records": [{"student_id": student["id"], "attendance_status": "PRESENT"}],
    }
    first = client.post(f"/journal-sessions/{session['id']}/attendance/batch", json=data)
    second = client.post(f"/journal-sessions/{session['id']}/attendance/batch", json=data)
    assert first.status_code == 201
    assert second.status_code == 409


def test_attendance_completeness_lists_missing_students(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    second_student = client.post("/students", json={
        "nis": "S002", "full_name": "Siswa Dua", "class_id": 1,
    }).json()
    client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0], "student_id": student["id"],
        "teacher_id": teacher["id"], "attendance_status": "PRESENT",
    })
    response = client.get(f"/journal-sessions/{session['id']}/attendance/completeness")
    assert response.status_code == 200
    assert response.json()[0]["recorded_count"] == 1
    assert response.json()[0]["missing_count"] == 1
    assert response.json()[0]["missing_students"][0]["student_id"] == second_student["id"]
    assert response.json()[1]["missing_count"] == 2


def test_attendance_completeness_can_filter_one_jp(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    response = client.get(
        f"/journal-sessions/{session['id']}/attendance/completeness?slot_id={slot_ids[1]}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["jp_number"] == 3


def test_attendance_completeness_rejects_unknown_session_or_jp(client):
    assert client.get("/journal-sessions/999/attendance/completeness").status_code == 404
    session, teacher, student, slot_ids = setup_session_with_student(client)
    response = client.get(
        f"/journal-sessions/{session['id']}/attendance/completeness?slot_id=999"
    )
    assert response.status_code == 400



def test_journal_submit_rejects_missing_lesson_sessions(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    officer = create_user(client, "petugas_submit").json()
    create_officer_period(client, classroom["id"], officer["id"])
    journal = client.post("/journals", json={
        "class_id": classroom["id"], "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    }).json()
    client.post(f"/classes/{classroom['id']}/schedule-slots", json={
        "day_of_week": "Monday", "slot_order": 1, "jp_number": 1,
        "start_time": "07:00", "end_time": "07:45", "slot_type": "LESSON",
    })
    response = client.post(f"/journals/{journal['id']}/submit", json={
        "officer_user_id": officer["id"],
    })
    assert response.status_code == 400
    assert "JP pelajaran" in response.json()["detail"]


def test_journal_submit_rejects_incomplete_attendance(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    response = client.post(f"/journals/{session['journal_id']}/submit", json={
        "officer_user_id": 1,
    })
    assert response.status_code == 400
    assert "absensi" in response.json()["detail"].lower()


def test_journal_submit_succeeds_when_all_lessons_and_attendance_complete(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id, "student_id": student["id"],
            "teacher_id": teacher["id"], "attendance_status": "PRESENT",
        })
    submitted = client.post(f"/journals/{session['journal_id']}/submit", json={
        "officer_user_id": 1,
    })
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED"
    assert client.get(f"/journals/{session['journal_id']}").json()["status"] == "SUBMITTED"
    repeated = client.post(f"/journals/{session['journal_id']}/submit", json={
        "officer_user_id": 1,
    })
    assert repeated.status_code == 400


def test_journal_submit_rejects_wrong_officer_and_repeat_submission(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    wrong = client.post(f"/journals/{session['journal_id']}/submit", json={
        "officer_user_id": 999,
    })
    assert wrong.status_code == 403



def submit_ready_journal(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id, "student_id": student["id"],
            "teacher_id": teacher["id"], "attendance_status": "PRESENT",
        })
        assert response.status_code == 201
    admin = create_user(client, "admin_piket", role="admin").json()
    roster = client.post("/duty-rosters", json={
        "duty_date": "2026-11-23",
        "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert roster.status_code == 201
    submitted = client.post(f"/journals/{session['journal_id']}/submit", json={"officer_user_id": 1})
    assert submitted.status_code == 200
    return session, teacher


def test_review_inbox_and_approve_journal(client):
    session, teacher = submit_ready_journal(client)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=teacher["id"], role="teacher", is_active=True,
    )
    inbox = client.get("/reviews/inbox")
    assert inbox.status_code == 200
    assert any(item["id"] == session["journal_id"] for item in inbox.json())

    reviewed = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "APPROVE",
    })
    assert reviewed.status_code == 201
    assert reviewed.json()["decision"] == "APPROVE"
    assert client.get(f"/journals/{session['journal_id']}").json()["status"] == "APPROVED"
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, role="class_officer", is_active=True,
    )
    officer_notifications = client.get("/notifications?user_id=1").json()
    assert officer_notifications[0]["notification_type"] == "JOURNAL_APPROVED"
    history = client.get(f"/journals/{session['journal_id']}/reviews")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_review_can_request_revision_and_requires_notes(client):
    session, teacher = submit_ready_journal(client)
    missing_notes = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "REQUEST_REVISION",
    })
    assert missing_notes.status_code == 422
    reviewed = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "REQUEST_REVISION",
        "notes": "Mohon lengkapi catatan materi.",
    })
    assert reviewed.status_code == 201
    assert client.get(f"/journals/{session['journal_id']}").json()["status"] == "REVISION_REQUIRED"


def test_review_rejects_non_teacher_and_invalid_journal_state(client):
    session, teacher = submit_ready_journal(client)
    non_teacher = create_user(client, "review_admin", role="admin").json()
    forbidden = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": non_teacher["id"], "decision": "APPROVE",
    })
    assert forbidden.status_code == 403
    approved = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "APPROVE",
    })
    assert approved.status_code == 201
    repeated = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "REJECT", "notes": "Tidak sesuai.",
    })
    assert repeated.status_code == 400



def test_journal_revision_cycle_and_resubmission(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id, "student_id": student["id"],
            "teacher_id": teacher["id"], "attendance_status": "PRESENT",
        })
        assert response.status_code == 201

    journal_id = session["journal_id"]
    admin = create_user(client, "admin_revisi", role="admin").json()
    roster = client.post("/duty-rosters", json={
        "duty_date": "2026-11-23",
        "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert roster.status_code == 201
    submitted = client.post(f"/journals/{journal_id}/submit", json={"officer_user_id": 1})
    assert submitted.status_code == 200
    revision = client.post(f"/journals/{journal_id}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "REQUEST_REVISION",
        "notes": "Perbaiki materi dan status kehadiran.",
    })
    assert revision.status_code == 201
    assert client.get(f"/journals/{journal_id}").json()["status"] == "REVISION_REQUIRED"

    started = client.post(f"/journals/{journal_id}/revision/start", json={"officer_user_id": 1})
    assert started.status_code == 200
    assert started.json()["status"] == "DRAFT"

    updated_session = client.put(f"/journal-sessions/{session['id']}", json={
        "material": "Materi yang sudah diperbaiki",
        "actual_start_time": "08:35", "actual_end_time": "09:50",
    })
    assert updated_session.status_code == 200
    attendance = client.get(f"/journal-sessions/{session['id']}/attendance").json()
    updated_attendance = client.put(f"/attendance/{attendance[0]['id']}", json={
        "teacher_id": teacher["id"], "attendance_status": "SICK",
    })
    assert updated_attendance.status_code == 200
    assert updated_attendance.json()["attendance_status"] == "SICK"

    resubmitted = client.post(f"/journals/{journal_id}/submit", json={"officer_user_id": 1})
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "RESUBMITTED"
    teacher_notifications = client.get(f"/notifications?user_id={teacher['id']}").json()
    assert any(item["notification_type"] == "JOURNAL_RESUBMITTED" for item in teacher_notifications)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=teacher["id"], role="teacher", is_active=True,
    )
    assert any(item["id"] == journal_id for item in client.get("/reviews/inbox").json())
    assert len(client.get(f"/journals/{journal_id}/reviews").json()) == 1



def test_admin_can_assign_and_filter_duty_roster(client):
    admin = create_user(client, "admin_roster", role="admin").json()
    teacher = create_user(client, "guru_roster", role="teacher").json()
    created = client.post("/duty-rosters", json={
        "duty_date": "2026-11-23",
        "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert created.status_code == 201
    assert created.json()["teacher_user_id"] == teacher["id"]
    filtered = client.get("/duty-rosters?duty_date=2026-11-23")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1


def test_duty_roster_rejects_duplicate_and_non_teacher(client):
    admin = create_user(client, "admin_roster2", role="admin").json()
    teacher = create_user(client, "guru_roster2", role="teacher").json()
    student_user = create_user(client, "petugas_roster", role="class_officer").json()
    payload = {
        "duty_date": "2026-11-24",
        "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    }
    assert client.post("/duty-rosters", json=payload).status_code == 201
    assert client.post("/duty-rosters", json=payload).status_code == 409
    invalid = client.post("/duty-rosters", json={
        **payload, "teacher_user_id": student_user["id"],
    })
    assert invalid.status_code == 400


def test_duty_roster_requires_admin_and_can_be_deleted(client):
    admin = create_user(client, "admin_roster3", role="admin").json()
    teacher = create_user(client, "guru_roster3", role="teacher").json()
    not_admin = client.post("/duty-rosters", json={
        "duty_date": "2026-11-25", "teacher_user_id": teacher["id"],
        "assigned_by_user_id": teacher["id"],
    })
    assert not_admin.status_code == 403
    created = client.post("/duty-rosters", json={
        "duty_date": "2026-11-25", "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert created.status_code == 201
    deleted = client.delete(f"/duty-rosters/{created.json()['id']}?admin_user_id={admin['id']}")
    assert deleted.status_code == 204
    assert client.get("/duty-rosters?duty_date=2026-11-25").json() == []


def test_teacher_without_duty_roster_cannot_review(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id, "student_id": student["id"],
            "teacher_id": teacher["id"], "attendance_status": "PRESENT",
        })
    submitted = client.post(f"/journals/{session['journal_id']}/submit", json={"officer_user_id": 1})
    assert submitted.status_code == 200
    response = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "APPROVE",
    })
    assert response.status_code == 403



def test_daily_dashboard_counts_journals_and_missing_classes(client):
    first_class = create_classroom(client, "X TKJ 1").json()
    second_class = create_classroom(client, "X TKJ 2").json()
    third_class = create_classroom(client, "X TKJ 3").json()
    first_officer = create_user(client, "dashboard_officer1").json()
    second_officer = create_user(client, "dashboard_officer2").json()
    create_officer_period(client, first_class["id"], first_officer["id"])
    create_officer_period(client, second_class["id"], second_officer["id"])

    draft = client.post("/journals", json={
        "class_id": first_class["id"], "journal_date": "2026-11-23",
        "officer_user_id": first_officer["id"],
    })
    submitted = client.post("/journals", json={
        "class_id": second_class["id"], "journal_date": "2026-11-23",
        "officer_user_id": second_officer["id"],
    })
    assert draft.status_code == 201
    assert submitted.status_code == 201
    sent = client.post(f"/journals/{submitted.json()['id']}/submit", json={
        "officer_user_id": second_officer["id"],
    })
    assert sent.status_code == 200

    admin = create_user(client, "dashboard_admin", role="admin").json()
    teacher = create_user(client, "dashboard_teacher", role="teacher").json()
    roster = client.post("/duty-rosters", json={
        "duty_date": "2026-11-23", "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert roster.status_code == 201
    approved = client.post(f"/journals/{submitted.json()['id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "APPROVE",
    })
    assert approved.status_code == 201

    response = client.get("/dashboard/daily?report_date=2026-11-23")
    assert response.status_code == 200
    result = response.json()
    assert result["total_classes"] == 3
    assert result["total_journals"] == 2
    assert result["status_counts"]["DRAFT"] == 1
    assert result["status_counts"]["APPROVED"] == 1
    assert result["status_counts"]["SUBMITTED"] == 0
    assert result["missing_classes"] == ["X TKJ 3"]


def test_daily_dashboard_uses_today_by_default_and_handles_empty_date(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    response = client.get("/dashboard/daily")
    assert response.status_code == 200
    assert response.json()["report_date"]
    assert response.json()["total_classes"] == 1
    assert response.json()["total_journals"] == 0
    assert response.json()["missing_classes"] == [classroom["name"]]

    empty_day = client.get("/dashboard/daily?report_date=2026-12-31")
    assert empty_day.status_code == 200
    assert empty_day.json()["total_journals"] == 0
    assert empty_day.json()["status_counts"]["DRAFT"] == 0



def test_class_dashboard_shows_sessions_attendance_and_review_history(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    for slot_id in slot_ids:
        response = client.post(f"/journal-sessions/{session['id']}/attendance", json={
            "slot_id": slot_id,
            "student_id": student["id"],
            "teacher_id": teacher["id"],
            "attendance_status": "PRESENT",
        })
        assert response.status_code == 201

    journal_id = session["journal_id"]
    admin = create_user(client, "class_dash_admin", role="admin").json()
    roster = client.post("/duty-rosters", json={
        "duty_date": "2026-11-23",
        "teacher_user_id": teacher["id"],
        "assigned_by_user_id": admin["id"],
    })
    assert roster.status_code == 201
    submitted = client.post(f"/journals/{journal_id}/submit", json={"officer_user_id": 1})
    assert submitted.status_code == 200
    reviewed = client.post(f"/journals/{journal_id}/review", json={
        "reviewer_user_id": teacher["id"],
        "decision": "REQUEST_REVISION",
        "notes": "Lengkapi catatan pembelajaran.",
    })
    assert reviewed.status_code == 201

    class_id = client.get(f"/journals/{journal_id}").json()["class_id"]
    response = client.get(f"/dashboard/classes/{class_id}?report_date=2026-11-23")
    assert response.status_code == 200
    result = response.json()
    assert result["journal_id"] == journal_id
    assert result["journal_status"] == "REVISION_REQUIRED"
    assert result["total_sessions"] == 1
    assert result["sessions"][0]["teacher_name"] == teacher["full_name"]
    assert result["sessions"][0]["material"]
    assert result["attendance_counts"]["PRESENT"] == len(slot_ids)
    assert result["reviews"][0]["notes"] == "Lengkapi catatan pembelajaran."


def test_class_dashboard_handles_missing_journal_and_unknown_class(client):
    classroom = create_classroom(client, "X TKJ Dashboard").json()
    response = client.get(
        f"/dashboard/classes/{classroom['id']}?report_date=2026-11-23"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["journal_id"] is None
    assert result["journal_status"] == "MISSING"
    assert result["sessions"] == []
    assert result["attendance_counts"]["PRESENT"] == 0

    missing = client.get("/dashboard/classes/999?report_date=2026-11-23")
    assert missing.status_code == 404



def test_journal_submission_notifies_duty_teacher(client):
    session, teacher = submit_ready_journal(client)

    response = client.get(f"/notifications?user_id={teacher['id']}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    notification = response.json()[0]
    assert notification["journal_id"] == session["journal_id"]
    assert notification["notification_type"] == "JOURNAL_SUBMITTED"
    assert notification["is_read"] is False


def test_journal_review_notifies_class_officer(client):
    session, teacher = submit_ready_journal(client)
    reviewed = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"],
        "decision": "REQUEST_REVISION",
        "notes": "Mohon lengkapi materi.",
    })
    assert reviewed.status_code == 201

    response = client.get("/notifications?user_id=1&unread_only=true")

    assert response.status_code == 200
    assert len(response.json()) == 1
    notification = response.json()[0]
    assert notification["notification_type"] == "REVISION_REQUESTED"
    assert "Mohon lengkapi materi." in notification["message"]


def test_notification_can_be_marked_read_only_by_recipient(client):
    session, teacher = submit_ready_journal(client)
    notification = client.get(f"/notifications?user_id={teacher['id']}").json()[0]
    other_user = create_user(client, "guru_lain", role="teacher").json()

    forbidden = client.put(
        f"/notifications/{notification['id']}/read?user_id={other_user['id']}"
    )
    marked = client.put(
        f"/notifications/{notification['id']}/read?user_id={teacher['id']}"
    )
    unread = client.get(f"/notifications?user_id={teacher['id']}&unread_only=true")
    all_notifications = client.get(f"/notifications?user_id={teacher['id']}")

    assert forbidden.status_code == 403
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert unread.json() == []
    assert all_notifications.json()[0]["is_read"] is True


def test_notification_list_rejects_unknown_user(client):
    response = client.get("/notifications?user_id=999")
    assert response.status_code == 404



def test_rejecting_journal_notifies_class_officer(client):
    session, teacher = submit_ready_journal(client)
    reviewed = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"],
        "decision": "REJECT",
        "notes": "Data jurnal tidak sesuai.",
    })

    notifications = client.get("/notifications?user_id=1").json()

    assert reviewed.status_code == 201
    assert notifications[0]["notification_type"] == "JOURNAL_REJECTED"
    assert "Data jurnal tidak sesuai." in notifications[0]["message"]



def test_admin_bootstrap_login_and_current_user(client):
    bootstrap = client.post("/auth/bootstrap", json={
        "username": "admin_utama",
        "full_name": "Administrator Utama",
        "password": "password-kuat-123",
    })
    second_bootstrap = client.post("/auth/bootstrap", json={
        "username": "admin_kedua",
        "full_name": "Admin Kedua",
        "password": "password-kuat-123",
    })
    wrong_login = client.post("/auth/login", json={
        "username": "admin_utama",
        "password": "password-salah",
    })
    login = client.post("/auth/login", json={
        "username": "admin_utama",
        "password": "password-kuat-123",
    })

    assert bootstrap.status_code == 201
    assert second_bootstrap.status_code == 409
    assert wrong_login.status_code == 401
    assert login.status_code == 200
    assert "password_hash" not in bootstrap.json()

    app.dependency_overrides.pop(get_current_user, None)
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "admin_utama"


def test_password_change_invalidates_old_token(client):
    client.post("/auth/bootstrap", json={
        "username": "admin_ganti",
        "full_name": "Admin Ganti",
        "password": "password-lama-123",
    })
    login = client.post("/auth/login", json={
        "username": "admin_ganti",
        "password": "password-lama-123",
    })
    old_token = login.json()["access_token"]
    app.dependency_overrides.pop(get_current_user, None)

    changed = client.post(
        "/auth/change-password",
        json={
            "old_password": "password-lama-123",
            "new_password": "password-baru-123",
        },
        headers={"Authorization": f"Bearer {old_token}"},
    )
    old_token_check = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    new_login = client.post("/auth/login", json={
        "username": "admin_ganti",
        "password": "password-baru-123",
    })

    assert changed.status_code == 200
    assert old_token_check.status_code == 401
    assert new_login.status_code == 200


def test_logout_invalidates_current_token(client):
    client.post("/auth/bootstrap", json={
        "username": "admin_logout",
        "full_name": "Admin Logout",
        "password": "password-kuat-123",
    })
    login = client.post("/auth/login", json={
        "username": "admin_logout",
        "password": "password-kuat-123",
    })
    token = login.json()["access_token"]
    app.dependency_overrides.pop(get_current_user, None)

    logout_response = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert logout_response.status_code == 200
    assert me.status_code == 401


def test_admin_can_set_password_for_new_user(client):
    admin = client.post("/auth/bootstrap", json={
        "username": "admin_password",
        "full_name": "Admin Password",
        "password": "password-admin-123",
    })
    user = create_user(client, "guru_baru", role="teacher")

    response = client.put(
        f"/users/{user.json()['id']}/password",
        json={"password": "password-guru-123"},
    )
    login = client.post("/auth/login", json={
        "username": "guru_baru",
        "password": "password-guru-123",
    })

    assert admin.status_code == 201
    assert response.status_code == 200
    assert login.status_code == 200


def test_protected_api_requires_login_and_admin_role(client):
    app.dependency_overrides.pop(get_current_user, None)
    unauthenticated = client.get("/users")
    test_admin = SimpleNamespace(
        id=TestActorId(), username="test_admin", full_name="Test Admin",
        role="admin", is_active=True, password_hash=None, token_version=0,
    )
    app.dependency_overrides[get_current_user] = lambda: test_admin
    client.post("/auth/bootstrap", json={
        "username": "admin_access",
        "full_name": "Admin Access",
        "password": "password-admin-123",
    })
    user = create_user(client, "guru_access", role="teacher")
    client.put(
        f"/users/{user.json()['id']}/password",
        json={"password": "password-guru-123"},
    )
    teacher_login = client.post("/auth/login", json={
        "username": "guru_access",
        "password": "password-guru-123",
    })
    app.dependency_overrides.pop(get_current_user, None)
    headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    forbidden = client.post(
        "/classes",
        json={"name": "X TKJ 1", "academic_year": "2026/2027"},
        headers=headers,
    )
    allowed_read = client.get("/classes", headers=headers)

    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert allowed_read.status_code == 200



def test_journal_actions_are_saved_in_audit_log(client):
    session, teacher = submit_ready_journal(client)
    journal_id = session["journal_id"]

    response = client.get(f"/audit-logs?journal_id={journal_id}&limit=200")
    actions = {item["action"] for item in response.json()}

    assert response.status_code == 200
    assert "JOURNAL_CREATED" in actions
    assert "SESSION_CREATED" in actions
    assert "ATTENDANCE_RECORDED" in actions
    assert "JOURNAL_SUBMITTED" in actions


def test_audit_log_limit_is_validated(client):
    response = client.get("/audit-logs?limit=201")
    assert response.status_code == 422


def test_logged_in_user_cannot_act_as_another_user(client):
    client.post("/auth/bootstrap", json={
        "username": "admin_identity",
        "full_name": "Admin Identity",
        "password": "password-admin-123",
    })
    classroom = create_classroom(client, "X TKJ Identity").json()
    officer = create_user(client, "petugas_identity", role="class_officer").json()
    client.put(
        f"/users/{officer['id']}/password",
        json={"password": "password-petugas-123"},
    )
    client.post(f"/classes/{classroom['id']}/officer-periods", json={
        "user_id": officer["id"],
        "start_date": "2026-11-23",
        "end_date": None,
    })
    admin_login = client.post("/auth/login", json={
        "username": "admin_identity",
        "password": "password-admin-123",
    })
    officer_login = client.post("/auth/login", json={
        "username": "petugas_identity",
        "password": "password-petugas-123",
    })
    app.dependency_overrides.pop(get_current_user, None)

    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    officer_headers = {"Authorization": f"Bearer {officer_login.json()['access_token']}"}
    payload = {
        "class_id": classroom["id"],
        "journal_date": "2026-11-23",
        "officer_user_id": officer["id"],
    }
    impersonation = client.post("/journals", json=payload, headers=admin_headers)
    created = client.post("/journals", json=payload, headers=officer_headers)

    assert impersonation.status_code == 403
    assert created.status_code == 201



def test_current_session_endpoint_rejects_non_teacher(client):
    admin = create_user(client, "admin_current_session", role="admin").json()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=admin["id"], username=admin["username"],
        full_name=admin["full_name"], role="admin",
        is_active=True, password_hash=None, token_version=0,
    )
    response = client.post(
        "/teachers/me/current-session",
        json={"slot_id": 1, "material": "Materi pengujian"},
    )
    assert response.status_code == 403


def test_teacher_current_schedule_uses_wib_and_returns_today_slots(client):
    teacher = create_user(client, "teacher_current_schedule", role="teacher").json()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=teacher["id"], username=teacher["username"],
        full_name=teacher["full_name"], role="teacher",
        is_active=True, password_hash=None, token_version=0,
    )
    response = client.get("/teachers/me/current-schedule")
    assert response.status_code == 200
    result = response.json()
    assert result["timezone"] == "Asia/Jakarta (WIB)"
    assert result["teacher_id"] == teacher["id"]
    assert "current_time" in result
    assert "today_slots" in result


def test_daily_schedule_shows_slots_and_actual_teacher(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)

    response = client.get(
        f"/classes/1/daily-schedule?on_date=2026-11-23"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["class_name"] == "X TKJ 1"
    assert result["journal_id"] == session["journal_id"]
    assert len(result["slots"]) == 2
    first_slot = next(item for item in result["slots"] if item["slot_id"] == slot_ids[0])
    assert first_slot["session_id"] == session["id"]
    assert first_slot["actual_teacher_id"] == teacher["id"]


def test_class_attendance_matrix_returns_number_by_date(client):
    session, teacher, _student, slot_ids = setup_session_with_student(client)
    client.put("/classes/1/roster", json={"roster_size": 2})
    recorded = client.post(
        f"/journal-sessions/{session['id']}/class-attendance",
        json={
            "slot_id": slot_ids[0],
            "teacher_id": teacher["id"],
            "records": [
                {"attendance_number": 1, "attendance_status": "PRESENT"},
                {"attendance_number": 2, "attendance_status": "SICK"},
            ],
        },
    )
    assert recorded.status_code == 201

    response = client.get(
        "/reports/class-attendance-matrix"
        "?class_id=1&start_date=2026-11-23&end_date=2026-11-24"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["class_name"] == "X TKJ 1"
    assert result["attendance_numbers"][0]["days"]["2026-11-23"] == "H"
    assert result["attendance_numbers"][1]["days"]["2026-11-23"] == "S"
    assert result["attendance_numbers"][0]["days"]["2026-11-24"] == "-"


def test_attendance_report_and_csv_export(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)
    first = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[0],
        "student_id": student["id"],
        "teacher_id": teacher["id"],
        "attendance_status": "PRESENT",
    })
    second = client.post(f"/journal-sessions/{session['id']}/attendance", json={
        "slot_id": slot_ids[1],
        "student_id": student["id"],
        "teacher_id": teacher["id"],
        "attendance_status": "SICK",
    })

    report = client.get(
        "/reports/attendance?class_id=1&start_date=2026-11-23&end_date=2026-11-23"
    )
    csv_report = client.get(
        "/reports/attendance.csv?class_id=1&start_date=2026-11-23&end_date=2026-11-23"
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert report.status_code == 200
    assert report.json()["total_records"] == 2
    assert report.json()["status_counts"]["PRESENT"] == 1
    assert report.json()["status_counts"]["SICK"] == 1
    assert report.json()["students"][0]["total"] == 2
    assert csv_report.status_code == 200
    assert "NIS,Nama Siswa,Hadir,Sakit,Izin,Alpa,Total" in csv_report.text
    assert student["full_name"] in csv_report.text


def test_attendance_report_rejects_invalid_date_range(client):
    response = client.get(
        "/reports/attendance?class_id=1&start_date=2026-11-24&end_date=2026-11-23"
    )
    assert response.status_code == 422



def test_schedule_slot_rejects_overlapping_time(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    url = f"/classes/{classroom['id']}/schedule-slots"
    first = {
        "day_of_week": "Monday",
        "slot_order": 1,
        "jp_number": 1,
        "start_time": "07:45",
        "end_time": "08:30",
        "slot_type": "LESSON",
    }
    overlap = {
        **first,
        "slot_order": 2,
        "jp_number": 2,
        "start_time": "08:15",
        "end_time": "09:00",
    }
    adjacent = {
        **first,
        "slot_order": 2,
        "jp_number": 2,
        "start_time": "08:30",
        "end_time": "09:15",
    }

    assert client.post(url, json=first).status_code == 201
    assert client.post(url, json=overlap).status_code == 409
    assert client.post(url, json=adjacent).status_code == 201


def test_schedule_slot_update_rejects_overlap_but_allows_same_slot(client):
    classroom = create_classroom(client, "X TKJ 1").json()
    url = f"/classes/{classroom['id']}/schedule-slots"
    first = client.post(url, json={
        "day_of_week": "Monday", "slot_order": 1, "jp_number": 1,
        "start_time": "07:45", "end_time": "08:30", "slot_type": "LESSON",
    }).json()
    second = client.post(url, json={
        "day_of_week": "Monday", "slot_order": 2, "jp_number": 2,
        "start_time": "08:30", "end_time": "09:15", "slot_type": "LESSON",
    }).json()

    same_slot = client.put(f"/schedule-slots/{first['id']}", json={
        "day_of_week": "Monday", "slot_order": 1, "jp_number": 1,
        "start_time": "07:45", "end_time": "08:30", "slot_type": "LESSON",
    })
    overlap = client.put(f"/schedule-slots/{second['id']}", json={
        "day_of_week": "Monday", "slot_order": 2, "jp_number": 2,
        "start_time": "08:00", "end_time": "08:45", "slot_type": "LESSON",
    })

    assert same_slot.status_code == 200
    assert overlap.status_code == 409



def test_review_inbox_only_shows_journals_for_assigned_duty_dates(client):
    session, assigned_teacher = submit_ready_journal(client)
    other_teacher = create_user(client, "guru_tidak_piket", role="teacher").json()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=assigned_teacher["id"], role="teacher", is_active=True,
    )
    assigned_inbox = client.get("/reviews/inbox")
    assert assigned_inbox.status_code == 200
    assert [item["id"] for item in assigned_inbox.json()] == [session["journal_id"]]

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=other_teacher["id"], role="teacher", is_active=True,
    )
    unassigned_inbox = client.get("/reviews/inbox")
    assert unassigned_inbox.status_code == 200
    assert unassigned_inbox.json() == []



def test_lesson_schedule_slot_requires_jp_number(client):
    classroom = create_classroom(client, "X TKJ No JP").json()
    response = client.post(
        f"/classes/{classroom['id']}/schedule-slots",
        json={
            "day_of_week": "Monday",
            "slot_order": 1,
            "jp_number": None,
            "start_time": "07:45",
            "end_time": "08:30",
            "slot_type": "LESSON",
        },
    )
    assert response.status_code == 422


def test_schedule_slot_used_by_journal_cannot_be_deleted(client):
    session, teacher, student, slot_ids = setup_session_with_student(client)

    response = client.delete(f"/schedule-slots/{slot_ids[0]}")

    assert response.status_code == 409
    assert "riwayat jurnal" in response.json()["detail"].lower()
    schedule = client.get("/classes/1/schedule-slots?day=Monday")
    assert any(slot["id"] == slot_ids[0] for slot in schedule.json())


def test_approved_journal_cannot_be_changed_again(client):
    session, teacher = submit_ready_journal(client)
    approved = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"],
        "decision": "APPROVE",
    })
    assert approved.status_code == 201

    session_update = client.put(f"/journal-sessions/{session['id']}", json={
        "material": "Perubahan setelah disetujui",
        "actual_start_time": "08:35",
        "actual_end_time": "09:55",
    })
    attendance = client.get(f"/journal-sessions/{session['id']}/attendance").json()
    attendance_update = client.put(f"/attendance/{attendance[0]['id']}", json={
        "teacher_id": teacher["id"],
        "attendance_status": "ABSENT",
    })
    resubmit = client.post(f"/journals/{session['journal_id']}/submit", json={
        "officer_user_id": 1,
    })

    assert session_update.status_code == 400
    assert attendance_update.status_code == 400
    assert resubmit.status_code == 400



def test_update_user_full_name(client):
    created = create_user(client, "akun_edit")
    user_id = created.json()["id"]

    response = client.put(
        f"/users/{user_id}",
        json={"full_name": "Nama Baru"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Nama Baru"
    assert response.json()["username"] == "akun_edit"


def test_deactivate_user(client):
    created = create_user(client, "akun_nonaktif")
    user_id = created.json()["id"]

    response = client.delete(f"/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    users = client.get("/users").json()
    saved_user = next(item for item in users if item["id"] == user_id)
    assert saved_user["is_active"] is False


def test_cannot_deactivate_last_active_admin(client):
    created = create_user(client, "admin_kedua", role="admin")
    user_id = created.json()["id"]

    response = client.delete(f"/users/{user_id}")

    assert response.status_code == 400
    assert "admin aktif terakhir" in response.json()["detail"]


def test_teacher_cannot_read_another_teachers_journal_or_attendance(client):
    journal, assigned_teacher, slot_ids = setup_journal_with_two_lesson_slots(client)
    outsider = create_user(client, "guru_tidak_terkait", role="teacher").json()
    client.put(
        f"/users/{outsider['id']}/password",
        json={"password": "password-guru-123"},
    )
    login = client.post("/auth/login", json={
        "username": "guru_tidak_terkait",
        "password": "password-guru-123",
    })
    assert login.status_code == 200

    app.dependency_overrides.pop(get_current_user, None)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    journal_detail = client.get(f"/journals/{journal['id']}", headers=headers)
    sessions = client.get(f"/journals/{journal['id']}/sessions", headers=headers)
    session = client.post(
        f"/journals/{journal['id']}/sessions",
        json={
            "slot_ids": slot_ids,
            "teacher_id": assigned_teacher["id"],
            "material": "Materi pengujian",
            "actual_start_time": "08:30",
            "actual_end_time": "10:00",
        },
        headers=headers,
    )
    assert session.status_code == 403

    # Buat sesi sebagai guru yang memang ditugaskan, lalu uji akses guru lain.
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=assigned_teacher["id"],
        username=assigned_teacher["username"],
        full_name=assigned_teacher["full_name"],
        role="teacher",
        is_active=True,
        password_hash=None,
        token_version=0,
    )
    created_session = client.post(
        f"/journals/{journal['id']}/sessions",
        json={
            "slot_ids": slot_ids,
            "teacher_id": assigned_teacher["id"],
            "material": "Materi pengujian",
            "actual_start_time": "08:30",
            "actual_end_time": "10:00",
        },
    )
    assert created_session.status_code == 201
    app.dependency_overrides.pop(get_current_user, None)

    session_id = created_session.json()["id"]
    class_attendance = client.get(
        f"/journal-sessions/{session_id}/class-attendance", headers=headers
    )
    completeness = client.get(
        f"/journal-sessions/{session_id}/attendance/completeness",
        headers=headers,
    )
    class_roster = client.get(
        f"/classes/{journal['class_id']}/roster", headers=headers
    )

    assert journal_detail.status_code == 403
    assert sessions.status_code == 403
    assert class_attendance.status_code == 403
    assert completeness.status_code == 403
    assert class_roster.status_code == 403


def test_teacher_read_permissions_limit_personal_and_admin_data(client):
    admin = create_user(client, "admin_read_scope", role="admin").json()
    classroom = create_classroom(client, "X TKJ Read Scope").json()
    officer = create_user(client, "petugas_read_scope").json()
    create_officer_period(client, classroom["id"], officer["id"])
    client.post("/students", json={
        "nis": "SCOPE001", "full_name": "Siswa Privat",
        "class_id": classroom["id"],
    })

    first_teacher = create_user(client, "guru_scope_1", role="teacher").json()
    second_teacher = create_user(client, "guru_scope_2", role="teacher").json()
    for teacher in (first_teacher, second_teacher):
        client.put(
            f"/users/{teacher['id']}/password",
            json={"password": "password-guru-123"},
        )
    for teacher in (first_teacher, second_teacher):
        created = client.post("/duty-rosters", json={
            "duty_date": "2026-11-25",
            "teacher_user_id": teacher["id"],
            "assigned_by_user_id": admin["id"],
        })
        assert created.status_code == 201

    login = client.post("/auth/login", json={
        "username": "guru_scope_1",
        "password": "password-guru-123",
    })
    assert login.status_code == 200
    app.dependency_overrides.pop(get_current_user, None)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    students = client.get("/students", headers=headers)
    teachers = client.get("/teachers", headers=headers)
    officer_periods = client.get(
        f"/classes/{classroom['id']}/officer-periods", headers=headers
    )
    duty_rosters = client.get("/duty-rosters", headers=headers)

    assert students.status_code == 403
    assert teachers.status_code == 403
    assert officer_periods.status_code == 403
    assert duty_rosters.status_code == 200
    assert [item["teacher_user_id"] for item in duty_rosters.json()] == [
        first_teacher["id"]
    ]


def test_class_officer_cannot_access_another_classes_journal(client):
    first_class = create_classroom(client, "X TKJ Officer A").json()
    second_class = create_classroom(client, "X TKJ Officer B").json()
    first_officer = create_user(client, "petugas_scope_a").json()
    second_officer = create_user(client, "petugas_scope_b").json()
    create_officer_period(client, first_class["id"], first_officer["id"])
    create_officer_period(client, second_class["id"], second_officer["id"])
    journal = client.post("/journals", json={
        "class_id": first_class["id"],
        "journal_date": "2026-11-25",
        "officer_user_id": first_officer["id"],
    }).json()

    client.put(
        f"/users/{second_officer['id']}/password",
        json={"password": "password-petugas-123"},
    )
    login = client.post("/auth/login", json={
        "username": "petugas_scope_b",
        "password": "password-petugas-123",
    })
    assert login.status_code == 200
    app.dependency_overrides.pop(get_current_user, None)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    detail = client.get(f"/journals/{journal['id']}", headers=headers)
    journal_list = client.get("/journals", headers=headers)
    dashboard = client.get(
        f"/dashboard/classes/{first_class['id']}?report_date=2026-11-25",
        headers=headers,
    )
    roster = client.get(f"/classes/{first_class['id']}/roster", headers=headers)

    assert detail.status_code == 403
    assert journal_list.status_code == 200
    assert journal_list.json() == []
    assert dashboard.status_code == 403
    assert roster.status_code == 403
