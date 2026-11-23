# JejakKBM

Sistem jurnal Kegiatan Belajar Mengajar (KBM) digital.

## Status proyek

Tahap backend: API jurnal KBM, absensi, autentikasi, notifikasi, audit log, dan database lokal. GUI Android belum dibuat.

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

Perintah ini membuat akun demo (`demo_admin`, `demo_guru`, `demo_petugas`), kelas, satu siswa, mata pelajaran, jadwal dua JP pada hari Senin, dan penugasan piket untuk Senin terdekat. Hasil perintah menampilkan ID akun, ID kelas, ID siswa, dan tanggal piket. Aman dijalankan berulang kali karena data yang sudah ada tidak dibuat ulang. Akun demo belum memiliki password; gunakan `demo_admin` saat membuat admin pertama melalui `/auth/bootstrap`, lalu admin mengatur password guru dan petugas melalui endpoint admin. Gunakan hanya untuk database latihan, bukan data sekolah sungguhan.

## Menjalankan API

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

Dokumentasi API tersedia di http://127.0.0.1:8000/docs.

## Endpoint yang tersedia

| Method | Alamat | Fungsi |
|---|---|---|
| GET | /health | Memeriksa API |
| POST | /auth/bootstrap | Membuat admin pertama |
| POST | /auth/login | Login dan memperoleh token |
| GET | /auth/me | Melihat akun yang sedang login |
| POST | /auth/change-password | Mengubah password akun sendiri |
| POST | /auth/logout | Membatalkan token saat ini |
| PUT | /users/{user_id}/password | Admin menetapkan password akun |
| GET | /audit-logs | Admin melihat riwayat tindakan penting |
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
| GET | /notifications?user_id=1 | Melihat notifikasi milik pengguna |
| GET | /notifications?user_id=1&unread_only=true | Melihat notifikasi yang belum dibaca |
| PUT | /notifications/{notification_id}/read?user_id=1 | Menandai notifikasi sudah dibaca |

## Menjalankan tes

```powershell
python -m pytest -q
```

## Login pertama kali

1. Siapkan database dan jalankan API.
2. Sebelum menjalankan API, atur secret token di PowerShell:

```powershell
$env:JEJAKKBM_SECRET_KEY = "ganti-dengan-secret-random-yang-panjang"
```

3. Buka `/docs`, lalu gunakan `POST /auth/bootstrap` untuk membuat admin pertama. Contoh JSON:

```json
{
  "username": "admin_sekolah",
  "full_name": "Administrator Sekolah",
  "password": "password-kuat-minimal-8"
}
```

4. Login melalui `POST /auth/login`. Gunakan access token yang diterima pada tombol **Authorize** di dokumentasi API.
5. Admin dapat membuat akun melalui `POST /users`, lalu menetapkan password melalui `PUT /users/{user_id}/password` dengan JSON `{ "password": "password-kuat" }`.
6. Akun dapat melihat identitas sendiri melalui `/auth/me`, mengganti password melalui `/auth/change-password`, dan keluar melalui `/auth/logout`.

`/auth/bootstrap`, `/auth/login`, dan `/health` tidak membutuhkan token. Endpoint lainnya memerlukan Bearer token. Operasi pengelolaan data utama dibatasi untuk admin. Tindakan yang membawa ID pelaku juga memeriksa agar ID tersebut sama dengan akun yang sedang login.

## Catatan

- Secret default di kode hanya untuk pengembangan lokal. Untuk penggunaan sekolah, selalu atur `JEJAKKBM_SECRET_KEY` sendiri dan jangan membagikannya.
- Password disimpan menggunakan PBKDF2-HMAC-SHA256. Token berlaku 8 jam; logout dan penggantian password membatalkan token lama.
- `POST /auth/bootstrap` hanya dapat berhasil sebelum admin ber-password pertama dibuat.
- Audit log mencatat pembuatan jurnal, sesi, absensi, pengiriman, review, revisi, laporan guru tidak hadir, dan penugasan piket. Hanya admin yang dapat membaca audit log.
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
- Sesi pembelajaran hanya memakai slot `LESSON` yang berurutan pada hari jurnal dan memiliki mata pelajaran yang sama. Biasanya guru sesi harus sama dengan guru terjadwal. Jika guru terjadwal tidak hadir, guru aktif lain boleh mengisi sesi setelah petugas kelas membuat laporan ketidakhadiran untuk setiap JP yang diambil alih. Data sesi dan absensi mencatat akun guru yang benar-benar mengajar. Waktu aktual serta materi dicatat pada sesi.
- Absensi disimpan per siswa dan per JP. Hanya guru pengajar sesi yang dapat mengisi; siswa harus berasal dari kelas jurnal. Status sementara: `PRESENT`, `SICK`, `PERMITTED`, `ABSENT`.


### Absensi massal dan kelengkapan

- `POST /journal-sessions/{session_id}/attendance/batch` menerima satu `slot_id`, `teacher_id`, dan daftar `records` berisi `student_id` serta `attendance_status`. Semua siswa divalidasi sebelum disimpan; jika satu data tidak valid, tidak ada catatan yang disimpan.
- `GET /journal-sessions/{session_id}/attendance/completeness` menampilkan jumlah siswa aktif, jumlah yang sudah dicatat, dan daftar yang belum dicatat untuk setiap JP. Tambahkan query `slot_id` untuk memeriksa satu JP saja.


### Pengiriman jurnal harian

- `POST /journals/{journal_id}/submit` menerima `officer_user_id` untuk mengirim jurnal oleh petugas kelas yang ditetapkan.
- Pengiriman hanya berhasil jika jurnal masih `DRAFT`, seluruh slot jadwal bertipe `LESSON` pada hari tersebut sudah masuk ke sesi pembelajaran, dan semua siswa aktif memiliki catatan absensi pada setiap JP dalam sesi.
- Slot khusus seperti `BREAK`, `ASSEMBLY`, `COCURRICULAR`, dan `FREE` tidak memerlukan sesi pembelajaran.
- Jika pemeriksaan berhasil, status jurnal berubah menjadi `SUBMITTED`. Status ini berarti jurnal sudah dikirim dan tidak perlu menunggu pemeriksaan guru piket untuk dihitung sebagai terkirim.


### Pemeriksaan guru

- `GET /reviews/inbox` menampilkan jurnal berstatus `SUBMITTED` atau `RESUBMITTED`.
- `POST /journals/{journal_id}/review` menerima `reviewer_user_id`, `decision` (`APPROVE`, `REQUEST_REVISION`, atau `REJECT`), dan `notes`. Catatan wajib untuk revisi atau penolakan.
- `GET /journals/{journal_id}/reviews` menampilkan riwayat pemeriksaan.
- Keputusan mengubah status jurnal menjadi `APPROVED`, `REVISION_REQUIRED`, atau `REJECTED`. Saat ini pemeriksa divalidasi sebagai akun guru aktif; penugasan guru piket khusus dan alur edit/resubmit akan dibuat pada tahap berikutnya.


### Revisi dan pengiriman ulang jurnal

- `POST /journals/{journal_id}/revision/start` menerima `officer_user_id` dan mengubah jurnal `REVISION_REQUIRED` menjadi `DRAFT` agar petugas dapat memperbaiki data.
- `PUT /journal-sessions/{session_id}` memperbaiki materi dan waktu aktual sesi saat jurnal `DRAFT`.
- `PUT /attendance/{attendance_id}` memperbaiki status absensi saat jurnal `DRAFT`, hanya oleh guru pengajar sesi.
- Setelah diperbaiki, gunakan kembali `POST /journals/{journal_id}/submit`. Jika jurnal pernah diminta revisi, status berubah menjadi `RESUBMITTED` dan masuk kembali ke antrean pemeriksaan. Riwayat pemeriksaan sebelumnya tetap disimpan.


### Penugasan guru piket

- `POST /duty-rosters` membuat penugasan guru piket berdasarkan tanggal. Request berisi `duty_date`, `teacher_user_id`, dan `assigned_by_user_id`. Hanya admin aktif yang dapat membuat penugasan dan guru yang ditugaskan harus aktif.
- `GET /duty-rosters` menampilkan semua penugasan; gunakan `?duty_date=YYYY-MM-DD` untuk satu tanggal.
- `DELETE /duty-rosters/{roster_id}?admin_user_id=1` menghapus penugasan dengan persetujuan akun admin aktif.
- Seorang guru boleh mendapat beberapa tanggal piket, dan satu tanggal boleh memiliki beberapa guru piket. Guru yang memeriksa jurnal harus terdaftar pada tanggal jurnal tersebut.
- Request masih membawa ID pelaku untuk menghubungkan tindakan dengan data, tetapi backend memeriksa bahwa ID tersebut sama dengan identitas dari Bearer token.


### Dashboard ringkasan harian

- `GET /dashboard/daily` menampilkan ringkasan jurnal untuk tanggal hari ini.
- Gunakan `GET /dashboard/daily?report_date=YYYY-MM-DD` untuk melihat tanggal tertentu.
- Respons berisi jumlah seluruh kelas, jumlah jurnal yang dibuat, jumlah jurnal berdasarkan status (`DRAFT`, `SUBMITTED`, `RESUBMITTED`, `REVISION_REQUIRED`, `APPROVED`, `REJECTED`), serta nama kelas yang belum membuat jurnal pada tanggal tersebut.
- Dashboard menghitung berdasarkan tanggal jurnal, bukan tanggal saat data diperiksa. Kelas tanpa jadwal tetap muncul dalam daftar jika belum memiliki jurnal.


### Dashboard detail per kelas

- `GET /dashboard/classes/{class_id}` menampilkan rincian jurnal kelas untuk tanggal hari ini.
- Gunakan `?report_date=YYYY-MM-DD` untuk memilih tanggal.
- Respons berisi status jurnal (atau `MISSING` jika belum dibuat), daftar sesi, guru, mata pelajaran, JP, materi, waktu aktual, jumlah absensi per status, dan riwayat catatan pemeriksaan.
- Jika jurnal belum ada, endpoint tetap mengembalikan ringkasan kosong agar dashboard dapat menampilkan kelas yang belum mengirim jurnal.


### Laporan guru tidak hadir

- `POST /journals/{journal_id}/absence-reports` mencatat guru terjadwal yang tidak hadir pada satu JP. Request berisi `slot_id`, `officer_user_id`, dan catatan opsional.
- Hanya petugas kelas yang ditetapkan dan masih aktif pada tanggal jurnal yang dapat melapor.
- Laporan hanya berlaku untuk slot `LESSON` yang memiliki guru terjadwal dan belum memiliki sesi pembelajaran.
- Satu JP hanya dapat memiliki satu laporan ketidakhadiran pada jurnal yang sama.
- `GET /journals/{journal_id}/absence-reports` menampilkan semua laporan untuk jurnal tersebut.
- Identitas pelapor diambil dari Bearer token; ID petugas pada request harus cocok dengan akun yang sedang login.


### Notifikasi dalam aplikasi

- Saat jurnal dikirim, semua guru yang terdaftar sebagai guru piket pada tanggal jurnal menerima notifikasi.
- Saat jurnal diminta revisi, petugas kelas menerima notifikasi beserta catatan guru piket.
- Saat jurnal disetujui atau ditolak, petugas kelas menerima notifikasi hasil pemeriksaan.
- `GET /notifications?user_id=1` menampilkan notifikasi pengguna. Tambahkan `&unread_only=true` untuk hanya melihat yang belum dibaca.
- `PUT /notifications/{notification_id}/read?user_id=1` menandai notifikasi sebagai sudah dibaca. Hanya penerima yang boleh mengubah status baca.
- Notifikasi disimpan di database lokal. Push notification ke HP belum dibuat karena aplikasi mobile belum tersedia.
- `user_id` pada URL harus sama dengan ID dari Bearer token. Pengguna tidak dapat membaca atau mengubah notifikasi milik akun lain.


### Jadwal harian dan validasi jadwal

- `GET /classes/{class_id}/daily-schedule?on_date=YYYY-MM-DD` menampilkan slot jadwal kelas pada tanggal yang dipilih, guru terjadwal, guru yang benar-benar mengajar, dan status jurnal.
- Saat membuat atau mengubah slot, backend menolak waktu yang bertabrakan dengan slot lain pada kelas dan hari yang sama.
- Dua slot yang waktunya tepat bersebelahan tetap diperbolehkan, misalnya 08:30–09:15 dan 09:15–10:00.
- Jadwal khusus seperti Apel, Kokurikuler, Istirahat, dan kegiatan lain dimasukkan sebagai tipe slot yang sesuai. Jadwal rutin sekolah diatur melalui slot per hari.

### Laporan administrasi

- `GET /reports/attendance?class_id=1&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` menampilkan rekap status absensi siswa untuk satu kelas.
- `GET /reports/attendance.csv?class_id=1&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` mengunduh rekap yang sama dalam format CSV.
- Kedua laporan hanya dapat dibuka oleh akun admin.
- Rentang laporan maksimal 366 hari agar permintaan tetap ringan.


### Perlindungan riwayat jurnal

- Slot jadwal yang sudah digunakan oleh sesi jurnal atau laporan ketidakhadiran tidak dapat dihapus. Backend mengembalikan HTTP 409 agar data absensi dan riwayat jurnal lama tetap utuh.
- Siswa dan profil guru dinonaktifkan, bukan dihapus permanen, sehingga catatan historis tetap dapat ditelusuri.
- Jurnal yang sudah dikirim atau diperiksa tidak dapat diubah melalui endpoint sesi dan absensi. Perbaikan hanya dilakukan setelah jurnal berstatus `REVISION_REQUIRED` dan petugas memulai revisi.
- SQLite sekarang mengaktifkan pemeriksaan foreign key pada koneksi aplikasi. Relasi yang masih dipakai tidak bisa dihapus diam-diam; data harus tetap konsisten.
