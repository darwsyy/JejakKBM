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

## Mengisi data contoh (opsional)

Setelah database disiapkan, jalankan:

```powershell
python backend/seed_demo.py
```

Perintah ini membuat akun demo (`demo_admin`, `demo_guru`, `demo_petugas`), kelas, satu siswa, mata pelajaran, dan jadwal contoh. Aman dijalankan berulang kali karena data yang sudah ada tidak dibuat ulang. Belum ada password karena fitur login belum dibuat. Gunakan hanya untuk database latihan, bukan data sekolah sungguhan.

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
| POST | /journals | Membuat jurnal harian kelas (idempotent) |
| POST | /journals/{journal_id}/sessions | Mencatat sesi pembelajaran dan JP yang digabung |
| GET | /journals/{journal_id}/sessions | Melihat sesi pembelajaran dalam jurnal |
| POST | /journal-sessions/{session_id}/attendance | Mengisi absensi seorang siswa untuk satu JP |
| GET | /journal-sessions/{session_id}/attendance | Melihat absensi dalam satu sesi |
| GET | /journals | Melihat jurnal (filter `class_id` atau `journal_date`) |
| GET | /journals/{journal_id} | Melihat detail jurnal |
| POST | /students | Menambahkan siswa ke kelas |
| GET | /students | Melihat daftar siswa (opsional filter `?class_id=1`) |
| POST | /teachers | Membuat profil guru dari akun role teacher |
| GET | /teachers | Melihat daftar profil guru |
| POST | /classes/{class_id}/officer-periods | Menambahkan periode petugas jurnal |
| GET | /classes/{class_id}/officer-periods | Melihat riwayat petugas kelas |
| GET | /classes/{class_id}/officer-current | Melihat petugas pada tanggal tertentu (`?on_date=YYYY-MM-DD`) |
| PUT | /teachers/{teacher_id} | Mengubah NIP guru |
| DELETE | /teachers/{teacher_id} | Menonaktifkan profil guru |
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
- Data demo dapat dibuat dengan `python backend/seed_demo.py`; gunakan hanya pada database latihan.
- File database lokal tidak dimasukkan ke Git.
- Jangan gunakan data pribadi siswa sungguhan untuk pengujian.
- Penugasan petugas utama belum menyediakan fitur pergantian petugas.
- Slot jadwal menyimpan hari, urutan, nomor JP (opsional), jam, dan jenis kegiatan.
- Slot dengan nomor JP harus berdurasi 45 menit. Slot istirahat/kegiatan khusus tidak perlu memiliki nomor JP.
- Penugasan guru hanya berlaku untuk slot bertipe LESSON dan akun guru aktif.
- Penugasan mata pelajaran hanya berlaku untuk slot bertipe LESSON. Satu slot memiliki maksimal satu mata pelajaran.
- Setiap siswa memiliki NIS unik dan ditempatkan pada satu kelas. Penghapusan siswa dilakukan dengan menonaktifkan data, bukan menghapus permanen.
- Profil guru terhubung ke satu akun dengan role teacher. NIP bersifat opsional dan unik jika diisi.
- Riwayat petugas jurnal disimpan per periode tanggal. Periode untuk kelas yang sama tidak boleh bertumpang tindih; `end_date` boleh kosong untuk penugasan yang masih berjalan.
- Satu kelas hanya memiliki satu jurnal per tanggal. Pembuatan jurnal memeriksa periode petugas dan aman diulang tanpa membuat jurnal duplikat. Jurnal baru berstatus `DRAFT`.
- Sesi pembelajaran hanya memakai slot `LESSON` yang berurutan pada hari jurnal, dengan mata pelajaran dan guru jadwal yang sama. Waktu aktual serta materi dicatat pada sesi.
- Absensi disimpan per siswa dan per JP. Hanya guru pengajar sesi yang dapat mengisi; siswa harus berasal dari kelas jurnal. Status sementara: `PRESENT`, `SICK`, `PERMITTED`, `ABSENT`.


### Absensi massal dan kelengkapan

- `POST /journal-sessions/{session_id}/attendance/batch` menerima satu `slot_id`, `teacher_id`, dan daftar `records` berisi `student_id` serta `attendance_status`. Semua siswa divalidasi sebelum disimpan; jika satu data tidak valid, tidak ada catatan yang disimpan.
- `GET /journal-sessions/{session_id}/attendance/completeness` menampilkan jumlah siswa aktif, jumlah yang sudah dicatat, dan daftar yang belum dicatat untuk setiap JP. Tambahkan query `slot_id` untuk memeriksa satu JP saja.


### Pengiriman jurnal harian

- `POST /journals/{journal_id}/submit` menerima `officer_user_id` untuk mengirim jurnal oleh petugas kelas yang ditetapkan.
- Pengiriman hanya berhasil jika jurnal masih `DRAFT`, seluruh slot jadwal bertipe `LESSON` pada hari tersebut sudah masuk ke sesi pembelajaran, dan semua siswa aktif memiliki catatan absensi pada setiap JP dalam sesi.
- Slot khusus seperti `BREAK`, `ASSEMBLY`, `COCURRICULAR`, dan `FREE` tidak memerlukan sesi pembelajaran.
- Jika pemeriksaan berhasil, status jurnal berubah menjadi `SUBMITTED`. Status ini berarti jurnal sudah dikirim dan tidak perlu menunggu pemeriksaan guru piket untuk dihitung sebagai terkirim.
