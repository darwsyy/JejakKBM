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
    inbox = client.get("/reviews/inbox")
    assert inbox.status_code == 200
    assert any(item["id"] == session["journal_id"] for item in inbox.json())

    reviewed = client.post(f"/journals/{session['journal_id']}/review", json={
        "reviewer_user_id": teacher["id"], "decision": "APPROVE",
    })
    assert reviewed.status_code == 201
    assert reviewed.json()["decision"] == "APPROVE"
    assert client.get(f"/journals/{session['journal_id']}").json()["status"] == "APPROVED"
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
