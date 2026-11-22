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
    response = client.post(
        "/classes",
        json={
            "name": "X TKJ 1",
            "academic_year": "2026/2027",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "X TKJ 1"

    list_response = client.get("/classes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
