import sqlite3
from contextlib import closing

import pytest

from backend.manage_database import (
    backup_database,
    check_database_integrity,
    list_backups,
    restore_database,
)


def create_database(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS sample (value TEXT)")
        connection.execute("DELETE FROM sample")
        connection.execute("INSERT INTO sample (value) VALUES (?)", (value,))
        connection.commit()


def read_database_value(path):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute("SELECT value FROM sample").fetchone()[0]


def test_backup_creates_valid_snapshot_and_lists_it(tmp_path):
    database = tmp_path / "jejak_kbm.db"
    backup_dir = tmp_path / "backups"
    create_database(database, "sebelum")

    backup = backup_database(database, backup_dir)

    assert backup.is_file()
    check_database_integrity(backup)
    assert read_database_value(backup) == "sebelum"
    assert backup in list_backups(backup_dir)


def test_backup_requires_existing_database(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "missing.db", tmp_path / "backups")


def test_restore_creates_safety_backup_and_restores_data(tmp_path):
    database = tmp_path / "jejak_kbm.db"
    backup_dir = tmp_path / "backups"
    create_database(database, "versi-lama")
    backup = backup_database(database, backup_dir)

    create_database(database, "versi-baru")
    restored_path, safety_backup = restore_database(
        backup.name, database, backup_dir
    )

    assert restored_path == database
    assert read_database_value(database) == "versi-lama"
    assert safety_backup is not None and safety_backup.is_file()
    assert read_database_value(safety_backup) == "versi-baru"


def test_restore_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="nama file"):
        restore_database("../jejak_kbm.db", tmp_path / "db.db", tmp_path / "backups")


def test_restore_rejects_corrupt_backup(tmp_path):
    database = tmp_path / "jejak_kbm.db"
    backup_dir = tmp_path / "backups"
    create_database(database, "aman")
    backup_dir.mkdir()
    corrupt = backup_dir / "jejak_kbm_corrupt.db"
    corrupt.write_bytes(b"bukan database sqlite")

    with pytest.raises(sqlite3.DatabaseError):
        restore_database(corrupt.name, database, backup_dir)

    assert read_database_value(database) == "aman"
