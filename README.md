# JejakKBM

Sistem jurnal Kegiatan Belajar Mengajar (KBM) digital.

## Status proyek

Tahap awal: fondasi backend API. Fitur database, autentikasi, aplikasi Android, dan dashboard admin belum diimplementasikan.

## Teknologi backend

- Python 3.14
- FastAPI
- Uvicorn
- pytest dan HTTPX untuk pengujian

## Persiapan Windows (PowerShell)

Dari direktori root proyek:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Jika PowerShell menolak aktivasi environment, jalankan executable secara langsung:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Menjalankan API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Dokumentasi API tersedia di `http://127.0.0.1:8000/docs` saat server berjalan.

## Menjalankan tes

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## Endpoint awal

- `GET /health` — pemeriksaan ketersediaan API.

## Catatan

Database belum dikonfigurasi. Jangan menyimpan kredensial atau file `.env` ke Git.
