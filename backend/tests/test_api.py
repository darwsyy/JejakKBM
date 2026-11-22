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
