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

Perintah tersebut membuat file `jejak_kbm.db` dan tabel yang diperlukan jika belum tersedia, termasuk data pengguna, kelas, petugas kelas, dan jadwal.

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
| PUT | /classes/{class_id}/officer/{user_id} | Menetapkan petugas jurnal utama |
| GET | /classes/{class_id}/officer | Melihat petugas jurnal utama kelas |
| POST | /classes/{class_id}/schedule-slots | Menambahkan slot jadwal kelas |
| GET | /classes/{class_id}/schedule-slots | Melihat slot jadwal kelas (opsional filter `?day=Monday`) |
| PUT | /schedule-slots/{slot_id} | Mengubah slot jadwal |
| PUT | /schedule-slots/{slot_id}/teacher/{teacher_id} | Menetapkan atau mengganti guru pengajar |
| GET | /schedule-slots/{slot_id}/teacher | Melihat guru pengajar slot |
| DELETE | /schedule-slots/{slot_id}/teacher | Menghapus penugasan guru |
| DELETE | /schedule-slots/{slot_id} | Menghapus slot jadwal |
| POST | /subjects | Menambahkan mata pelajaran |
| GET | /subjects | Melihat daftar mata pelajaran |
| POST | /students | Menambahkan siswa ke kelas |
| GET | /students | Melihat daftar siswa (opsional filter `?class_id=1`) |
| PUT | /students/{student_id} | Mengubah data atau kelas siswa |
| DELETE | /students/{student_id} | Menonaktifkan siswa tanpa menghapus data |
| PUT | /schedule-slots/{slot_id}/subject/{subject_id} | Menetapkan atau mengganti mata pelajaran |
| GET | /schedule-slots/{slot_id}/subject | Melihat mata pelajaran pada slot |
| DELETE | /schedule-slots/{slot_id}/subject | Menghapus penugasan mata pelajaran |

## Menjalankan tes

```powershell
python -m pytest -q
```

## Catatan

- Saat ini belum ada login atau pembatasan akses. Endpoint hanya untuk pengembangan lokal.
- File database lokal tidak dimasukkan ke Git.
- Jangan gunakan data pribadi siswa sungguhan untuk pengujian.
- Penugasan petugas utama belum menyediakan fitur pergantian petugas.
- Slot jadwal menyimpan hari, urutan, nomor JP (opsional), jam, dan jenis kegiatan.
- Slot dengan nomor JP harus berdurasi 45 menit. Slot istirahat/kegiatan khusus tidak perlu memiliki nomor JP.
- Penugasan guru hanya berlaku untuk slot bertipe LESSON dan akun guru aktif.
- Penugasan mata pelajaran hanya berlaku untuk slot bertipe LESSON. Satu slot memiliki maksimal satu mata pelajaran.
- Setiap siswa memiliki NIS unik dan ditempatkan pada satu kelas. Penghapusan siswa dilakukan dengan menonaktifkan data, bukan menghapus permanen.
