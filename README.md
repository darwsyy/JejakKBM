# JejakKBM

Sistem jurnal Kegiatan Belajar Mengajar (KBM) digital.

## Status proyek

Tahap awal: fondasi backend dan database lokal. Fitur login, jurnal KBM, absensi, aplikasi Android, dan dashboard admin akan dibuat bertahap.

## Teknologi

- Python 3.14
- FastAPI dan Uvicorn untuk backend API
- SQLite untuk database lokal
- SQLAlchemy untuk menghubungkan Python dengan database
- pytest untuk pengujian

## Persiapan Windows (PowerShell)

Jalankan dari folder utama proyek:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Jika environment sudah pernah dibuat, tidak perlu membuatnya lagi. Cukup aktifkan:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Menyiapkan database

```powershell
python backend/create_db.py
```

Perintah tersebut membuat file `jejak_kbm.db` dan tabel awal `users` jika belum tersedia.

## Menjalankan API

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

Dokumentasi API tersedia di http://127.0.0.1:8000/docs.

## Menjalankan tes

```powershell
python -m pytest -q
```

## Endpoint awal

- `GET /health` — memeriksa apakah API berjalan.

## Catatan

File database lokal tidak dimasukkan ke Git. Database saat ini hanya untuk pengembangan; data sekolah sungguhan belum digunakan.
