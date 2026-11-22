from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import User


def test_user_can_be_saved_to_database(tmp_path) -> None:
    database_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{database_file}")

    Base.metadata.create_all(bind=test_engine)

    with Session(test_engine) as session:
        user = User(
            username="petugas1",
            full_name="Petugas Jurnal",
            role="class_officer",
        )
        session.add(user)
        session.commit()

        saved_user = session.query(User).filter_by(username="petugas1").first()

    assert saved_user is not None
    assert saved_user.full_name == "Petugas Jurnal"
    assert saved_user.role == "class_officer"

    test_engine.dispose()
