from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "jejak-kbm-api",
    }




def test_gui_is_written_in_python_with_flet() -> None:
    gui_file = Path(__file__).resolve().parents[2] / "frontend" / "app.py"
    source = gui_file.read_text(encoding="utf-8")

    assert "import flet as ft" in source
    assert "ft.run(main" in source


def test_gui_is_not_served_as_html_by_backend() -> None:
    response = client.get("/app")

    assert response.status_code == 404
