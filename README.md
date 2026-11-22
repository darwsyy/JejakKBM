# JejakKBM

Sistem jurnal Kegiatan Belajar Mengajar (KBM) digital.

## Status proyek

Tahap awal: backend API dan database lokal. Fitur login, jurnal KBM, absensi, aplikasi Android, dan dashboard admin akan dibuat bertahap.

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

Perintah tersebut membuat file `jejak_kbm.db` dan tabel `users` serta `classes` jika belum tersedia.

## Menjalankan API

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

Dokumentasi API tersedia di http://127.0.0.1:8000/docs.

## Endpoint yang tersedia

| Method | Alamat | Fungsi |
|---|---|---|
| GET | /health | Memeriksa API |
| POST | /users | Menambah pengguna |
| GET | /users | Melihat pengguna |
| POST | /classes | Menambah kelas |
| GET | /classes | Melihat kelas |

## Menjalankan tes

```powershell
python -m pytest -q
```

## Catatan

- Saat ini belum ada login atau pembatasan akses. Endpoint hanya untuk pengembangan lokal.
- File database lokal tidak dimasukkan ke Git.
- Jangan gunakan data pribadi siswa sungguhan untuk pengujian.
