"""Utilitas backup dan restore database SQLite JejakKBM.

Jalankan dari folder proyek:
    python backend/manage_database.py backup
    python backend/manage_database.py list
    python backend/manage_database.py restore NAMA_FILE.db --confirm
"""

import argparse
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "jejak_kbm.db"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"


def check_database_integrity(database_path: Path) -> None:
    """Tolak database yang tidak lolos pemeriksaan integritas SQLite."""
    if not database_path.is_file():
        raise FileNotFoundError(f"File database tidak ditemukan: {database_path}")

    with closing(sqlite3.connect(str(database_path))) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        detail = result[0] if result else "hasil pemeriksaan kosong"
        raise ValueError(f"Database tidak lolos integrity_check: {detail}")


def _copy_database(source_path: Path, destination_path: Path) -> None:
    """Salin snapshot database dengan SQLite backup API, termasuk transaksi aktif."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(source_path))) as source:
        with closing(sqlite3.connect(str(destination_path))) as destination:
            source.backup(destination)
            destination.commit()


def backup_database(
    database_path: Path = DEFAULT_DATABASE,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    label: str = "backup",
) -> Path:
    """Buat snapshot database dan verifikasi hasilnya."""
    database_path = Path(database_path)
    backup_dir = Path(backup_dir)
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database belum ditemukan: {database_path}. Jalankan setup database terlebih dahulu."
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"jejak_kbm_{label}_{timestamp}.db"
    try:
        _copy_database(database_path, backup_path)
        check_database_integrity(backup_path)
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def list_backups(backup_dir: Path = DEFAULT_BACKUP_DIR) -> list[Path]:
    """Daftar backup JejakKBM terbaru terlebih dahulu."""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    return sorted(
        backup_dir.glob("jejak_kbm_*.db"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def restore_database(
    backup_name: str,
    database_path: Path = DEFAULT_DATABASE,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> tuple[Path, Path | None]:
    """Pulihkan backup setelah membuat backup pengaman database saat ini."""
    database_path = Path(database_path)
    backup_dir = Path(backup_dir)

    # Hanya izinkan nama file di dalam folder backups, bukan path arbitrer.
    if Path(backup_name).name != backup_name or not backup_name.endswith(".db"):
        raise ValueError("Masukkan hanya nama file backup dari folder backups.")
    source_path = backup_dir / backup_name
    if not source_path.is_file():
        raise FileNotFoundError(f"File backup tidak ditemukan: {source_path}")
    if source_path.resolve() == database_path.resolve():
        raise ValueError("File backup tidak boleh sama dengan database aktif.")

    check_database_integrity(source_path)

    safety_backup = None
    if database_path.is_file():
        safety_backup = backup_database(
            database_path, backup_dir, label="before_restore"
        )

    # Siapkan file sementara di folder database agar os.replace tetap satu volume.
    temporary_path = database_path.with_name(
        f"{database_path.stem}_restore_tmp{database_path.suffix}"
    )
    try:
        temporary_path.unlink(missing_ok=True)
        _copy_database(source_path, temporary_path)
        check_database_integrity(temporary_path)
        os.replace(temporary_path, database_path)
    except PermissionError as error:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Database tidak dapat diganti. Matikan server JejakKBM terlebih dahulu, lalu ulangi restore."
        ) from error
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return database_path, safety_backup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backup dan restore database SQLite JejakKBM."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("backup", help="Buat backup database saat ini.")
    subparsers.add_parser("list", help="Tampilkan daftar file backup.")
    restore_parser = subparsers.add_parser("restore", help="Pulihkan database dari backup.")
    restore_parser.add_argument("backup_name", help="Nama file di folder backups.")
    restore_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Konfirmasi bahwa database aktif akan diganti.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "backup":
            path = backup_database()
            print(f"Backup berhasil dibuat: {path}")
        elif args.command == "list":
            backups = list_backups()
            if not backups:
                print("Belum ada backup.")
            else:
                for item in backups:
                    print(f"{item.name} ({item.stat().st_size:,} bytes)")
        elif args.command == "restore":
            if not args.confirm:
                print("Restore membatalkan isi database aktif. Tambahkan --confirm setelah memeriksa nama backup.")
                return 2
            database, safety_backup = restore_database(args.backup_name)
            print(f"Database berhasil dipulihkan: {database}")
            if safety_backup:
                print(f"Backup pengaman database sebelumnya: {safety_backup}")
            print("Jika server sedang berjalan, restart server agar koneksi memakai database hasil restore.")
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"Operasi database gagal: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
