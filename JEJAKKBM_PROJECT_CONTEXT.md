# JejakKBM --- Project Context & Development Blueprint

**Dokumen handoff untuk AI coding assistant**\
Versi: 1.0 \| Status: Pra-implementasi\
Nama: **JejakKBM --- Sistem Jurnal Kegiatan Belajar Mengajar Digital**

------------------------------------------------------------------------

## 0. Instruksi untuk AI Pengembang

Baca dokumen ini sebelum mengubah atau membuat kode. Dokumen ini adalah
sumber konteks utama proyek.

Aturan kerja: 1. Jangan mengubah tujuan atau aturan bisnis tanpa
persetujuan pengguna. 2. Jangan mengarang jawaban untuk keputusan yang
belum ditetapkan. Tandai sebagai **OPEN DECISION** dan tanyakan jika
memengaruhi implementasi. 3. Kerjakan satu fitur sampai implementasi dan
pengujiannya selesai sebelum berpindah fitur. 4. Sebelum mengubah kode,
jelaskan tujuan, file yang akan diubah, alur logika, dampak
database/API/UI, dan rencana pengujian. 5. Setelah perubahan, laporkan
file yang berubah, implementasi, hasil tes, langkah uji manual, dan
pekerjaan tersisa. 6. Jangan melakukan git commit/push; pengguna
mengerjakannya sendiri. 7. Jangan menghapus database atau data pengguna
saat migrasi. 8. Jangan menambah dependency tanpa alasan yang jelas. 9.
Backend adalah sumber kebenaran untuk authentication, authorization,
validasi, waktu, dan status jurnal. 10. Jangan menyatakan fitur selesai
hanya karena UI dibuat. Acceptance criteria harus terpenuhi. 11. Jangan
melakukan perubahan besar lintas modul tanpa membagi pekerjaan dan
meminta persetujuan. 12. Jika implementasi yang ada berbeda dari
dokumen, periksa kondisi aktual dan jelaskan konflik sebelum
mengubahnya.

------------------------------------------------------------------------

# 1. Ringkasan Proyek

## 1.1 Latar belakang

Di sekolah terdapat administrasi **jurnal kelas**, yaitu buku fisik
untuk merekam keberlangsungan Kegiatan Belajar Mengajar (KBM). Isinya
mencakup kehadiran guru, kehadiran siswa, materi pembelajaran, dan
pelaksanaan berdasarkan jam pelajaran. **1 JP = 45 menit.**

Masalah proses fisik: - Siswa harus mengambil jurnal sebelum JP 1; kelas
yang jauh membutuhkan waktu dan tenaga. - Siswa harus mengembalikan
jurnal setelah KBM dan mencari tanda tangan guru. - Guru mungkin sudah
tidak berada di sekolah ketika siswa selesai, sehingga proses
pengembalian tertunda. - Guru harus mencatat waktu aktual berakhirnya
pelajaran secara manual. - Tumpukan jurnal menyulitkan pencarian dan
pengambilan untuk hari berikutnya. - Pencatatan fisik menimbulkan
redundansi, pencarian lambat, dan rekapitulasi sulit.

## 1.2 Solusi

JejakKBM adalah sistem digital untuk mencatat, mengelola, mengirim,
memverifikasi, dan mengarsipkan jurnal KBM berdasarkan kelas, tanggal,
jadwal, dan JP.

Guru mengisi materi, kehadiran siswa, dan waktu aktual pembelajaran.
Petugas kelas melaporkan kondisi yang menjadi kewenangannya, memeriksa
kelengkapan, lalu mengirim jurnal harian. Guru piket memverifikasi
melalui antrean digital.

**Jurnal yang sudah dikirim dianggap sudah dikumpulkan walaupun belum
diverifikasi. Siswa tidak perlu menunggu persetujuan guru piket untuk
pulang.**

## 1.3 Tujuan

-   Menghilangkan kebutuhan mengambil dan mengembalikan buku fisik.
-   Mengurangi ketergantungan pada tanda tangan langsung.
-   Mencatat KBM secara terstruktur.
-   Memperjelas tanggung jawab guru, petugas kelas, dan guru piket.
-   Memudahkan verifikasi, pencarian, rekapitulasi, dan audit.

## 1.4 Bukan tujuan MVP

JejakKBM bukan LMS penuh. MVP tidak mencakup pengelolaan tugas akademik,
materi belajar lengkap, chat internal, pengganti seluruh sistem
akademik, analitik AI, atau integrasi WhatsApp otomatis.

------------------------------------------------------------------------

# 2. Platform dan Arsitektur

## 2.1 Target

-   Utama: Android / mobile-first.
-   Tambahan: dashboard web untuk administrator (cakupan MVP masih perlu
    dikonfirmasi).
-   Backend: Python.
-   API: REST melalui HTTPS.
-   Database: PostgreSQL.

## 2.2 Rekomendasi teknologi

  -----------------------------------------------------------------------
  Lapisan                             Rekomendasi
  ----------------------------------- -----------------------------------
  Backend                             Python + FastAPI

  Validasi                            Pydantic

  ORM                                 SQLAlchemy

  Migrasi database                    Alembic

  Database                            PostgreSQL

  Auth                                JWT dengan strategi refresh yang
                                      aman

  Password hashing                    Argon2id atau bcrypt

  Android                             Flutter (rekomendasi)

  Alternatif Android                  Kivy, jika Python pada client
                                      menjadi persyaratan kuat

  Admin web                           Frontend web terpisah; framework
                                      diputuskan kemudian

  Push notification                   Firebase Cloud Messaging, tahap
                                      lanjutan

  Testing                             pytest + HTTPX/TestClient

  Development environment             Docker Compose opsional
  -----------------------------------------------------------------------

**Belum final:** framework Android dan apakah dashboard web masuk MVP.
Rekomendasi awal Flutter untuk client, FastAPI untuk backend. Jangan
membuat dua frontend sebelum kontrak API dan alur inti stabil.

## 2.3 Prinsip arsitektur

1.  Backend menjadi sumber kebenaran.
2.  Semua permission diperiksa di backend, bukan hanya menyembunyikan
    tombol UI.
3.  Gunakan Role-Based Access Control (RBAC).
4.  Pisahkan master data, jadwal, jurnal, sesi, kehadiran, review, dan
    audit.
5.  Simpan timestamp secara konsisten dan tampilkan dalam zona waktu
    sekolah.
6.  Simpan snapshot jadwal pada jurnal agar perubahan jadwal baru tidak
    mengubah rekam historis.
7.  Gunakan database migration.
8.  Audit semua tindakan penting.
9.  Tangani request gagal dan koneksi tidak stabil.
10. Jangan mengimplementasikan offline sync penuh sebelum aturan konflik
    data dirancang.

------------------------------------------------------------------------

# 3. Role dan Hak Akses

Gunakan satu sistem login. Role menentukan izin dan menu. Satu akun
dapat memiliki lebih dari satu role, misalnya guru yang juga bertugas
sebagai guru piket.

## 3.1 Administrator

-   Mengelola akun, siswa, guru, kelas, dan mata pelajaran.
-   Mengelola anggota kelas.
-   Menetapkan satu petugas jurnal utama per kelas.
-   Mengelola jadwal mingguan, slot JP, dan perubahan jadwal per
    tanggal.
-   Menetapkan jadwal guru piket.
-   Melihat laporan sesuai kewenangan.

## 3.2 Petugas kelas (siswa yang ditunjuk)

-   Melihat jadwal dan jurnal kelas hari ini.
-   Melaporkan guru tidak hadir.
-   Mencatat informasi guru pengganti untuk dikonfirmasi.
-   Melengkapi bagian jurnal yang menjadi tanggung jawabnya.
-   Memeriksa kelengkapan dan mengirim jurnal harian.
-   Menerima notifikasi revisi dan mengajukan perbaikan.

**Batasan:** petugas kelas tidak boleh mengisi atau mengubah kehadiran
siswa atas nama guru. Setiap kelas memiliki satu petugas utama aktif
pada satu periode. Penunjukan pengganti sementara bila petugas utama
absen masih perlu disahkan.

## 3.3 Guru pengajar

-   Melihat jadwal mengajar.
-   Mengisi materi pembelajaran.
-   Mengisi kehadiran siswa.
-   Mencatat waktu aktual mulai dan selesai KBM.
-   Mengonfirmasi pertanggungjawaban atas data.
-   Mengonfirmasi sesi jika menjadi guru pengganti.

**Aturan:** hanya guru pengajar yang berwenang mengisi kehadiran siswa.
Guru hanya dapat mengubah sesi yang menjadi kewenangannya, kecuali ada
penugasan resmi.

## 3.4 Guru piket

Guru piket adalah guru yang ditugaskan pada tanggal tertentu, bukan
harus akun permanen terpisah. 1. Guru login dengan akun biasa. 2.
Backend memeriksa penugasan piket pada tanggal itu. 3. Jika ditugaskan,
menu/izin verifikasi aktif. 4. Guru piket melihat antrean, memeriksa
jurnal, lalu menyetujui, meminta revisi, atau menolak dengan alasan.

Jangan meminta login kedua. Identitas akun dan penugasan piket dari
database menjadi dasar izin.

------------------------------------------------------------------------

# 4. Aturan Bisnis yang Sudah Diputuskan

  -----------------------------------------------------------------------
  ID                                  Aturan
  ----------------------------------- -----------------------------------
  BR-001                              Satu JP berdurasi 45 menit.

  BR-002                              Kehadiran siswa per JP/sesi hanya
                                      diisi oleh guru pengajar.

  BR-003                              Beberapa JP berurutan boleh
                                      digabung jika pembelajaran
                                      berkelanjutan.

  BR-004                              Jurnal yang sudah dikirim tetap
                                      dianggap sudah dikirim walaupun
                                      belum diverifikasi.

  BR-005                              Siswa tidak harus menunggu
                                      verifikasi untuk pulang.

  BR-006                              Setiap kelas memiliki satu petugas
                                      jurnal utama.

  BR-007                              Petugas kelas memeriksa kelengkapan
                                      dan mengirim jurnal harian.

  BR-008                              Guru piket dapat menyetujui,
                                      meminta revisi, atau menolak dengan
                                      alasan.

  BR-009                              Jam kosong yang memang dijadwalkan
                                      tidak perlu memiliki catatan sesi
                                      KBM.

  BR-010                              Sistem membedakan waktu jadwal dan
                                      waktu aktual KBM.

  BR-011                              Riwayat perubahan dan verifikasi
                                      harus dapat ditelusuri.

  BR-012                              Petugas kelas tidak boleh mengisi
                                      kehadiran siswa.
  -----------------------------------------------------------------------

Jangan menyamakan status: - belum dikirim; - sudah dikirim; - sedang
diperiksa; - diminta revisi; - dikirim ulang; - disetujui.

`SUBMITTED` atau `UNDER_REVIEW` bukan "belum mengumpulkan".

------------------------------------------------------------------------

# 5. Aturan Jadwal Sekolah

## 5.1 Ketentuan yang sudah diberikan

  -----------------------------------------------------------------------
  Kondisi                             Ketentuan
  ----------------------------------- -----------------------------------
  Durasi JP                           45 menit

  Senin JP 1                          07.00--07.45 adalah apel; tidak
                                      perlu jurnal KBM, tampilkan sebagai
                                      Apel

  Istirahat 1                         10.00--10.15

  Istirahat 2                         12.00--12.30

  Jumat                               Dua JP pertama adalah kokurikuler

  Jam kosong                          Tidak perlu dipertanggungjawabkan
                                      sebagai sesi KBM

  Jadwal                              Dikelola administrator per kelas
  -----------------------------------------------------------------------

Istirahat disebut sebagai aturan harian dalam rancangan awal; penerapan
pada Jumat dan hari khusus perlu dikonfirmasi.

## 5.2 Tipe slot

-   `LESSON`: pelajaran reguler.
-   `ASSEMBLY`: apel.
-   `COCURRICULAR`: kokurikuler.
-   `BREAK`: istirahat.
-   `FREE`: jam kosong.
-   `SPECIAL_EVENT`: kegiatan khusus.

Slot non-KBM tidak boleh memaksa guru mengisi jurnal pelajaran.

## 5.3 Jadwal tetap dan pengecualian

Sistem harus mendukung: - jadwal mingguan berdasarkan kelas dan hari; -
slot JP, waktu, guru, dan mata pelajaran; - perubahan jadwal untuk
tanggal tertentu; - perubahan guru/kegiatan sementara; - penugasan guru
piket per tanggal.

Perubahan tanggal tertentu tidak boleh menimpa jadwal permanen. Jurnal
historis harus mempertahankan snapshot jadwal saat jurnal dibuat.

------------------------------------------------------------------------

# 6. Alur Operasional

## 6.1 Persiapan hari sekolah

1.  Sistem menentukan tanggal/hari sekolah.
2.  Mengambil jadwal kelas yang berlaku.
3.  Menerapkan pengecualian tanggal tertentu.
4.  Menyediakan jurnal harian untuk kelas.
5.  Petugas kelas dan guru melihat informasi sesuai role.

Pembuatan jurnal harus idempotent: proses berulang tidak menghasilkan
jurnal ganda untuk kelas dan tanggal yang sama.

## 6.2 Pengisian guru

1.  Guru login dan melihat jadwal.
2.  Membuka sesi/slot yang menjadi tanggung jawabnya.
3.  Mengisi materi.
4.  Mengisi kehadiran siswa.
5.  Mencatat waktu aktual mulai dan selesai.
6.  Menyatakan data benar/bertanggung jawab.
7.  Backend menyimpan aktor dan timestamp.

Waktu aktual idealnya berasal dari server ketika guru menekan tombol
mulai/selesai. Sediakan koreksi manual dengan alasan jika terjadi
kesalahan teknis/lupa menekan tombol. Koreksi harus diaudit.

## 6.3 Penggabungan JP

Satu sesi dapat mencakup satu atau beberapa JP berurutan jika
pembelajaran berkelanjutan.

Validasi: - JP berurutan; - kelas dan tanggal sama; - tidak melewati
istirahat atau kegiatan khusus; - tidak bertabrakan dengan sesi lain; -
guru sesuai jadwal atau penugasan pengganti; - sesi menyimpan daftar JP
yang dicakup.

Contoh: JP 2 dan JP 3 dapat menjadi satu sesi. JP 4 yang berbeda mata
pelajaran menjadi sesi lain.

## 6.4 Guru tidak hadir

1.  Petugas kelas memilih slot bermasalah.
2.  Sistem menampilkan guru dari jadwal.
3.  Petugas melaporkan ketidakhadiran.
4.  Jika ada guru pengganti, identitasnya dicatat.
5.  Guru pengganti mengonfirmasi jika memungkinkan.
6.  Laporan yang belum dikonfirmasi tetap terlihat bagi guru piket.
7.  Guru piket memeriksa laporan sebagai bagian jurnal.

Petugas tidak boleh mengisi materi/kehadiran seolah-olah sebagai guru.

## 6.5 Jam kosong

Slot bertipe `FREE` tidak memerlukan sesi. Jika pelajaran menjadi kosong
karena guru tidak hadir, catat kejadian ketidakhadiran; jangan diam-diam
menyamakannya dengan jam kosong terjadwal.

## 6.6 Pengiriman jurnal

1.  Petugas memeriksa kelengkapan.
2.  Backend memeriksa seluruh slot yang wajib memiliki catatan.
3.  Slot non-KBM dan jam kosong terjadwal dikecualikan.
4.  Data belum terkonfirmasi ditampilkan dengan jelas.
5.  Jika syarat terpenuhi, petugas menekan Kirim Jurnal.
6.  Backend mengunci versi kiriman dan mencatat waktu.
7.  Jurnal masuk antrean guru piket.
8.  Petugas boleh pulang tanpa menunggu verifikasi.

## 6.7 Verifikasi guru piket

Guru piket melihat kelas/tanggal, petugas, sesi/JP, guru, materi,
kehadiran, waktu aktual, laporan guru tidak hadir/pengganti, data belum
terkonfirmasi, dan riwayat revisi.

Tindakan: - `APPROVE`: menyetujui. - `REQUEST_REVISION`: meminta
perbaikan dengan catatan. - `REJECT`: menolak dengan alasan wajib.

------------------------------------------------------------------------

# 7. State Machine Jurnal

Status: 1. `DRAFT`: jurnal tersedia dan masih dilengkapi. 2.
`READY_TO_SUBMIT`: semua bagian wajib lengkap. 3. `SUBMITTED`: petugas
mengirim jurnal. 4. `UNDER_REVIEW`: guru piket sedang memeriksa. 5.
`REVISION_REQUIRED`: perbaikan diminta. 6. `RESUBMITTED`: jurnal
perbaikan dikirim ulang. 7. `APPROVED`: jurnal disetujui.

Alur:

``` text
DRAFT
  |
  v
READY_TO_SUBMIT
  |
  v
SUBMITTED
  |
  v
UNDER_REVIEW
  |             \
  v              v
APPROVED     REVISION_REQUIRED
                    |
                    v
                RESUBMITTED
                    |
                    v
                UNDER_REVIEW
```

Aturan: - `SUBMITTED` berarti kewajiban pengiriman telah dilakukan. -
`UNDER_REVIEW` tidak berarti siswa harus menunggu. - Setelah dikirim,
jurnal tidak boleh diedit langsung. - Revisi membuat versi/riwayat
baru. - `APPROVED` tidak boleh diedit langsung; koreksi setelah
disetujui harus melalui prosedur khusus dan audit. - Setiap transisi
menyimpan aktor, waktu, dan catatan. - Status kesiapan boleh dihitung
atau disimpan, tetapi backend harus menjadi pemeriksa.

------------------------------------------------------------------------

# 8. Waktu Aktual KBM

Sistem membedakan waktu jadwal, aktual mulai, dan aktual selesai.

Contoh: - Jadwal: 07.45--09.15. - Aktual: 07.51--09.22. - Selisih mulai:
+6 menit. - Selisih selesai: +7 menit.

Rumus: `selisih = waktu_aktual - waktu_jadwal`.

Positif berarti lebih lambat; negatif berarti lebih awal.

Catatan: - Waktu sesi bukan otomatis waktu kepulangan siswa. - Definisi
waktu aktual harus disepakati sekolah. - Gunakan waktu server. - Koreksi
manual harus menyimpan nilai awal, nilai koreksi, alasan, pelaku, dan
waktu. - Jangan menyimpulkan keterlambatan hanya dari waktu aplikasi
dibuka.

------------------------------------------------------------------------

# 9. Rancangan Database Konseptual

Ini daftar entitas awal, bukan skema SQL final. Buat ERD, constraint,
index, dan migration sebelum implementasi final.

  Tabel                       Fungsi
  --------------------------- -----------------------------------------------
  `users`                     Akun dan password hash
  `roles`                     Daftar role
  `user_roles`                Relasi akun-role
  `students`                  Profil siswa
  `teachers`                  Profil guru
  `classes`                   Data kelas
  `class_members`             Anggota kelas
  `class_officers`            Penugasan petugas utama per periode
  `subjects`                  Mata pelajaran
  `schedules`                 Jadwal mingguan
  `schedule_slots`            JP, waktu, jenis kegiatan, guru, mapel
  `schedule_exceptions`       Perubahan jadwal tanggal tertentu
  `duty_assignments`          Penugasan guru piket
  `daily_journals`            Jurnal harian kelas
  `learning_sessions`         Sesi pembelajaran, dapat mencakup beberapa JP
  `session_periods`           JP yang dicakup sesi
  `attendance_records`        Kehadiran siswa per sesi
  `teacher_absence_reports`   Laporan guru tidak hadir
  `substitute_assignments`    Guru pengganti dan konfirmasi
  `journal_reviews`           Pemeriksaan guru piket
  `journal_revisions`         Riwayat revisi
  `notifications`             Notifikasi
  `audit_logs`                Riwayat tindakan penting

Constraint penting: - satu jurnal per kelas per tanggal; - satu petugas
utama aktif per kelas dalam rentang tanggal sama; - JP tidak boleh
dipakai dua sesi yang bertabrakan; - sesi hanya mencakup JP valid dan
berurutan; - kehadiran harus memiliki guru pengisi berwenang; - review
menyimpan guru piket, keputusan, waktu, catatan; - perubahan status
memiliki aktor dan timestamp; - jadwal historis tetap konsisten ketika
master jadwal berubah.

------------------------------------------------------------------------

# 10. Struktur Folder Rekomendasi

``` text
JejakKBM/
├── README.md
├── JEJAKKBM_PROJECT_CONTEXT.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── requirements/
│   │   ├── SRS.md
│   │   ├── BUSINESS_RULES.md
│   │   └── USER_STORIES.md
│   ├── architecture/
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── ERD.md
│   │   ├── API_CONTRACT.md
│   │   └── JOURNAL_STATE_MACHINE.md
│   ├── operations/
│   │   ├── SCHOOL_SCHEDULE_RULES.md
│   │   └── DEPLOYMENT.md
│   └── decisions/
│       └── ADR-0001-initial-architecture.md
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── permissions.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── seed.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── role.py
│   │   │   ├── student.py
│   │   │   ├── teacher.py
│   │   │   ├── classroom.py
│   │   │   ├── subject.py
│   │   │   ├── schedule.py
│   │   │   ├── journal.py
│   │   │   ├── learning_session.py
│   │   │   ├── attendance.py
│   │   │   ├── review.py
│   │   │   ├── notification.py
│   │   │   └── audit_log.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── schedule.py
│   │   │   ├── journal.py
│   │   │   ├── learning_session.py
│   │   │   ├── attendance.py
│   │   │   └── review.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── auth.py
│   │   │           ├── users.py
│   │   │           ├── classes.py
│   │   │           ├── teachers.py
│   │   │           ├── schedules.py
│   │   │           ├── journals.py
│   │   │           ├── sessions.py
│   │   │           ├── attendance.py
│   │   │           ├── reviews.py
│   │   │           ├── notifications.py
│   │   │           └── reports.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── schedule_service.py
│   │   │   ├── journal_service.py
│   │   │   ├── session_service.py
│   │   │   ├── attendance_service.py
│   │   │   ├── submission_service.py
│   │   │   ├── review_service.py
│   │   │   ├── notification_service.py
│   │   │   └── audit_service.py
│   │   └── utils/
│   │       ├── datetime.py
│   │       └── pagination.py
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       └── api/
│
├── mobile/
│   └── README.md
│   # Project Flutter/Kivy dibuat setelah framework diputuskan.
├── admin_web/
│   └── README.md
│   # Dashboard dibuat setelah cakupan dan framework diputuskan.
├── scripts/
│   ├── seed_demo_data.*
│   └── backup_db.*
└── deployment/
    ├── Dockerfile.backend
    └── README.md
```

Tanggung jawab folder: - `models/`: tabel dan relasi ORM. - `schemas/`:
validasi dan bentuk request/response. - `api/`: endpoint HTTP; hindari
business logic kompleks di endpoint. - `services/`: aturan bisnis. -
`core/`: konfigurasi, keamanan, permission, logging, exception. -
`tests/`: unit, integration, API tests. - `docs/`: kontrak
implementasi. - `mobile/` dan `admin_web/`: frontend terpisah dari
backend.

Struktur boleh disesuaikan dengan alasan teknis, tetapi pemisahan
tanggung jawab harus dijaga.

------------------------------------------------------------------------

# 11. Rancangan API Awal

Endpoint berikut konseptual; kontrak final dibuat di
`docs/architecture/API_CONTRACT.md`.

**Auth** - `POST /api/v1/auth/login` - `POST /api/v1/auth/refresh` -
`POST /api/v1/auth/logout` - `GET /api/v1/auth/me`

**Master data** - `GET/POST /api/v1/classes` -
`GET/POST /api/v1/students` - `GET/POST /api/v1/teachers` -
`GET/POST /api/v1/subjects` - `GET/POST /api/v1/users` -
`GET/POST /api/v1/class-officers`

**Schedule** - `GET /api/v1/classes/{class_id}/schedule` -
`POST /api/v1/schedules` - `PATCH /api/v1/schedules/{schedule_id}` -
`POST /api/v1/schedule-exceptions` -
`GET /api/v1/duty-assignments/today`

**Journal/session** - `GET /api/v1/journals/today` -
`GET /api/v1/journals/{journal_id}` - `GET /api/v1/journals/history` -
`POST /api/v1/journals/{journal_id}/submit` -
`POST /api/v1/journals/{journal_id}/sessions` -
`PATCH /api/v1/sessions/{session_id}` -
`POST /api/v1/sessions/{session_id}/start` -
`POST /api/v1/sessions/{session_id}/finish` -
`POST /api/v1/sessions/{session_id}/confirm`

**Attendance** - `GET /api/v1/sessions/{session_id}/attendance` -
`PUT /api/v1/sessions/{session_id}/attendance`

Backend wajib memverifikasi guru pengisi sebagai guru pengajar yang
berwenang.

**Absence/substitute** -
`POST /api/v1/journals/{journal_id}/absence-reports` -
`POST /api/v1/absence-reports/{report_id}/substitute` -
`POST /api/v1/substitutes/{assignment_id}/confirm`

**Review** - `GET /api/v1/reviews/inbox` -
`POST /api/v1/journals/{journal_id}/review` -
`POST /api/v1/journals/{journal_id}/revisions` -
`POST /api/v1/journals/{journal_id}/resubmit`

**Reports** - `GET /api/v1/reports/journals` -
`GET /api/v1/reports/attendance` - `GET /api/v1/reports/teaching-time`

------------------------------------------------------------------------

# 12. Non-Functional Requirements

## Security

-   Password disimpan sebagai hash kuat, bukan plaintext.
-   Permission dan ownership diperiksa backend.
-   Endpoint sensitif membutuhkan autentikasi.
-   Batasi akses data siswa berdasarkan kewenangan.
-   Jangan mengekspos data pribadi dalam log.
-   Gunakan HTTPS pada deployment.
-   Pertimbangkan rate limiting untuk autentikasi.

## Data integrity

-   Gunakan foreign key dan constraint.
-   Gunakan transaksi untuk submit/review.
-   Cegah jurnal ganda dan JP bertabrakan.
-   Gunakan audit log.
-   Migrasi tidak boleh menghapus data.

## Reliability

-   Tangani koneksi gagal dan request berulang.
-   Draft tidak boleh hilang karena request gagal.
-   Operasi penting harus aman terhadap retry.
-   Sediakan backup dan prosedur restore.
-   Catat error yang dapat ditelusuri.

## Usability

-   Mobile-first.
-   Form sesuai role dan sesingkat mungkin.
-   Status jurnal mudah dibedakan.
-   Bahasa UI Indonesia yang jelas.
-   Konfirmasi sebelum tindakan final.
-   Error menjelaskan cara memperbaiki.

## Auditability

Minimal simpan aktor, jenis tindakan, entitas, waktu, nilai
sebelum/sesudah untuk perubahan penting, dan alasan koreksi/revisi.

------------------------------------------------------------------------

# 13. Task List / Development Objectives

Semua task dimulai dengan status `TODO`. Jangan tandai selesai sebelum
acceptance criteria terpenuhi.

## Phase 0 --- Product Definition & Decisions

-   [ ] P0-01 Konfirmasi nama dan deskripsi final.
-   [ ] P0-02 Putuskan framework Android (Flutter/Kivy).
-   [ ] P0-03 Putuskan apakah admin web masuk MVP.
-   [ ] P0-04 Konfirmasi aturan istirahat pada Jumat/hari khusus.
-   [ ] P0-05 Putuskan prosedur pengganti petugas kelas utama.
-   [ ] P0-06 Tetapkan kode kehadiran resmi (H/I/S/D) dan definisinya.
-   [ ] P0-07 Tetapkan siapa yang boleh mengoreksi kehadiran.
-   [ ] P0-08 Tetapkan batas waktu submit/verifikasi jika ada.
-   [ ] P0-09 Putuskan apakah laporan guru pengganti belum terkonfirmasi
    menghalangi submit.
-   [ ] P0-10 Definisikan waktu aktual secara resmi.
-   [ ] P0-11 Finalisasi SRS dan business rules.

**Acceptance:** keputusan yang memengaruhi skema, permission, dan
workflow terdokumentasi; tidak ada asumsi kritis.

## Phase 1 --- Repository & Backend Foundation

-   [ ] P1-01 Buat struktur repository.
-   [ ] P1-02 Buat Python environment dan dependency management.
-   [ ] P1-03 Konfigurasi FastAPI.
-   [ ] P1-04 Buat `.env.example` dan konfigurasi aplikasi.
-   [ ] P1-05 Siapkan PostgreSQL development.
-   [ ] P1-06 Integrasikan SQLAlchemy.
-   [ ] P1-07 Integrasikan Alembic.
-   [ ] P1-08 Buat health-check endpoint.
-   [ ] P1-09 Tambahkan logging dan exception handling.
-   [ ] P1-10 Siapkan pytest dan smoke tests.

**Acceptance:** backend berjalan sesuai README, koneksi DB berhasil,
migration awal berjalan, tes dasar lulus.

## Phase 2 --- Authentication & Authorization

-   [ ] P2-01 Model user.
-   [ ] P2-02 Model role dan user-role.
-   [ ] P2-03 Password hashing.
-   [ ] P2-04 Login.
-   [ ] P2-05 Refresh/logout sesuai strategi.
-   [ ] P2-06 Endpoint current user.
-   [ ] P2-07 Permission dependencies.
-   [ ] P2-08 Test akses berdasarkan role.
-   [ ] P2-09 Test akses lintas kelas/ownership.

**Acceptance:** password tidak plaintext; user tanpa izin mendapat 403;
user tidak dapat membaca/mengubah data kelas lain dengan mengganti ID.

## Phase 3 --- Master Data

-   [ ] P3-01 Model/migration kelas.
-   [ ] P3-02 Model/migration siswa.
-   [ ] P3-03 Model/migration guru.
-   [ ] P3-04 Model/migration mata pelajaran.
-   [ ] P3-05 Relasi siswa-kelas.
-   [ ] P3-06 Penugasan satu petugas utama per kelas/periode.
-   [ ] P3-07 CRUD master data administrator.
-   [ ] P3-08 Validasi data unik dan relasi.
-   [ ] P3-09 Seed data demo.

**Acceptance:** admin mengelola data; relasi akun benar; tidak ada dua
petugas utama aktif bersamaan untuk kelas/periode yang sama.

## Phase 4 --- Schedule Engine

-   [ ] P4-01 Model jadwal mingguan.
-   [ ] P4-02 Model slot JP dan tipe kegiatan.
-   [ ] P4-03 Durasi JP 45 menit.
-   [ ] P4-04 Aturan apel Senin JP 1.
-   [ ] P4-05 Kokurikuler Jumat dua JP pertama.
-   [ ] P4-06 Slot istirahat.
-   [ ] P4-07 Slot jam kosong.
-   [ ] P4-08 Pengecualian jadwal per tanggal.
-   [ ] P4-09 Penugasan guru piket.
-   [ ] P4-10 Generator jadwal harian.
-   [ ] P4-11 Snapshot jadwal pada jurnal.
-   [ ] P4-12 Test konflik dan perubahan jadwal.

**Acceptance:** jadwal sesuai aturan yang dikonfirmasi; slot non-KBM
benar; perubahan tanggal tidak mengubah jadwal permanen atau jurnal
historis.

## Phase 5 --- Daily Journal & Learning Sessions

-   [ ] P5-01 Model jurnal harian.
-   [ ] P5-02 Satu jurnal per kelas/tanggal.
-   [ ] P5-03 Pembuatan jurnal idempotent.
-   [ ] P5-04 Model sesi pembelajaran.
-   [ ] P5-05 Relasi sesi ke satu/beberapa JP.
-   [ ] P5-06 Validasi JP berurutan dan tidak overlap.
-   [ ] P5-07 Validasi guru sesuai jadwal/penugasan.
-   [ ] P5-08 Endpoint jurnal hari ini.
-   [ ] P5-09 Endpoint draft sesi.
-   [ ] P5-10 Pengisian materi.
-   [ ] P5-11 Konfirmasi tanggung jawab guru.
-   [ ] P5-12 Test sesi tunggal, gabungan, dan slot non-KBM.

**Acceptance:** jurnal muncul tepat; sesi gabungan valid; JP tidak
dipakai dua kali; sesi tidak melewati istirahat/kegiatan khusus;
snapshot historis tetap.

## Phase 6 --- Attendance

-   [ ] P6-01 Model kehadiran.
-   [ ] P6-02 Definisikan kode kehadiran setelah konfirmasi.
-   [ ] P6-03 Endpoint daftar siswa per sesi.
-   [ ] P6-04 Endpoint isi/perbarui kehadiran.
-   [ ] P6-05 Hanya guru pengajar berwenang dapat mengisi.
-   [ ] P6-06 Simpan aktor dan timestamp.
-   [ ] P6-07 Koreksi dengan audit log.
-   [ ] P6-08 Test akses petugas kelas/guru piket terhadap endpoint.

**Acceptance:** petugas kelas tidak dapat mengubah kehadiran melalui
API; setiap catatan punya pengisi; koreksi tidak menghapus riwayat.

## Phase 7 --- Teacher Absence & Substitute

-   [ ] P7-01 Model laporan guru tidak hadir.
-   [ ] P7-02 Endpoint laporan petugas kelas.
-   [ ] P7-03 Ambil guru terjadwal dari snapshot.
-   [ ] P7-04 Model guru pengganti.
-   [ ] P7-05 Konfirmasi guru pengganti.
-   [ ] P7-06 Status belum terkonfirmasi.
-   [ ] P7-07 Integrasi laporan ke jurnal.
-   [ ] P7-08 Test tanpa pengganti/dengan pengganti.

**Acceptance:** petugas hanya melaporkan; guru pengganti dapat
mengonfirmasi; laporan belum terkonfirmasi terlihat oleh piket;
ketidakhadiran tidak disamakan dengan jam kosong terjadwal.

## Phase 8 --- Submission, Review & Revision

-   [ ] P8-01 Aturan kelengkapan jurnal.
-   [ ] P8-02 Validasi kesiapan submit di backend.
-   [ ] P8-03 Endpoint submit.
-   [ ] P8-04 Kunci versi kiriman.
-   [ ] P8-05 Antrean review.
-   [ ] P8-06 Batasi antrean ke guru piket yang ditugaskan.
-   [ ] P8-07 Approve.
-   [ ] P8-08 Request revision.
-   [ ] P8-09 Reject dengan alasan wajib.
-   [ ] P8-10 Riwayat review/revisi.
-   [ ] P8-11 Resubmit.
-   [ ] P8-12 Pastikan siswa tidak harus menunggu approval.
-   [ ] P8-13 Test semua transisi state machine.

**Acceptance:** submit hanya jika syarat terpenuhi; versi terkunci;
hanya piket yang ditugaskan dapat review; revisi memiliki riwayat;
SUBMITTED berbeda dari belum dikirim; siswa boleh pulang setelah submit.

## Phase 9 --- Notifications & Audit

-   [ ] P9-01 Model notifikasi.
-   [ ] P9-02 Notifikasi jurnal masuk ke guru piket.
-   [ ] P9-03 Notifikasi revisi ke petugas.
-   [ ] P9-04 Notifikasi approval/rejection.
-   [ ] P9-05 Pengingat sesi guru yang belum diisi.
-   [ ] P9-06 Audit log tindakan penting.
-   [ ] P9-07 Tampilan riwayat aktivitas.
-   [ ] P9-08 Test notifikasi/audit.

**Acceptance:** notifikasi tidak menjadi sumber status; kegagalan
notifikasi tidak membatalkan submit; tindakan penting dapat ditelusuri.

## Phase 10 --- Mobile UI

-   [ ] P10-01 Fondasi app dan navigasi.
-   [ ] P10-02 Login.
-   [ ] P10-03 Dashboard per role.
-   [ ] P10-04 Jadwal harian.
-   [ ] P10-05 Jurnal harian.
-   [ ] P10-06 Form sesi guru.
-   [ ] P10-07 Form kehadiran.
-   [ ] P10-08 Laporan guru tidak hadir.
-   [ ] P10-09 Kelengkapan dan submit petugas.
-   [ ] P10-10 Antrean review guru piket.
-   [ ] P10-11 Revisi dan riwayat.
-   [ ] P10-12 Loading/error/empty/offline states.
-   [ ] P10-13 Test beberapa ukuran layar Android.

**Acceptance:** alur utama berjalan dari HP; UI sesuai role; semua
tindakan divalidasi backend; form memiliki feedback dan tidak kehilangan
draft tanpa sengaja.

## Phase 11 --- Admin Dashboard

-   [ ] P11-01 Konfirmasi cakupan admin web.
-   [ ] P11-02 Login dan permission admin.
-   [ ] P11-03 CRUD kelas/siswa/guru/mapel.
-   [ ] P11-04 Editor jadwal mingguan.
-   [ ] P11-05 Editor pengecualian jadwal.
-   [ ] P11-06 Penugasan petugas kelas.
-   [ ] P11-07 Penugasan guru piket.
-   [ ] P11-08 Rekap jurnal.

**Acceptance:** admin dapat mengelola data/jadwal tanpa mengubah
database secara manual.

## Phase 12 --- Reports, QA & Deployment

-   [ ] P12-01 Rekap jurnal per tanggal/kelas.
-   [ ] P12-02 Rekap kehadiran.
-   [ ] P12-03 Rekap waktu aktual KBM.
-   [ ] P12-04 Ekspor CSV/Excel/PDF sesuai kebutuhan.
-   [ ] P12-05 Integration test satu hari sekolah.
-   [ ] P12-06 Test role dan akses tidak sah.
-   [ ] P12-07 Test aturan Senin/Jumat/istirahat.
-   [ ] P12-08 Test revisi dan audit trail.
-   [ ] P12-09 Backup dan restore.
-   [ ] P12-10 Dokumentasi instalasi/deployment.
-   [ ] P12-11 Uji data simulasi.
-   [ ] P12-12 Uji coba terbatas di sekolah setelah izin.

**Acceptance:** alur inti lulus integration test; backup dapat
dipulihkan; deployment terdokumentasi; tidak ada akses lintas role yang
tidak sah.

## Fitur setelah MVP

-   [ ] Push notification FCM.
-   [ ] Tautan WhatsApp dengan pesan otomatis yang disiapkan, tetapi
    dikirim atas tindakan pengguna.
-   [ ] Offline draft dan sinkronisasi.
-   [ ] Analitik lanjutan.
-   [ ] Integrasi sistem akademik lain.

------------------------------------------------------------------------

# 14. Definition of Done

Fitur selesai hanya jika: 1. Business rule diterapkan. 2. Backend
validation dan authorization tersedia. 3. Migration tersedia jika skema
berubah. 4. API request/response terdokumentasi. 5. Unit test relevan
lulus. 6. Integration test relevan lulus. 7. Error handling tersedia. 8.
Audit tersedia untuk perubahan penting. 9. UI memiliki
loading/success/error/empty states jika relevan. 10. Langkah manual test
ditulis. 11. Dokumentasi diperbarui. 12. Tidak ada regresi pada fitur
yang sudah selesai.

------------------------------------------------------------------------

# 15. Open Decisions --- Jangan Diasumsikan

  -----------------------------------------------------------------------
  ID                      Pertanyaan              Dampak
  ----------------------- ----------------------- -----------------------
  OD-01                   Android memakai Flutter Frontend
                          atau Kivy?              

  OD-02                   Admin web masuk MVP?    Scope frontend

  OD-03                   Istirahat berlaku sama  Schedule engine
                          pada Jumat/hari khusus? 

  OD-04                   Bagaimana petugas       Permission/assignment
                          pengganti saat petugas  
                          utama absen?            

  OD-05                   Apa arti resmi kode     Validasi/laporan
                          kehadiran H/I/S/D?      

  OD-06                   Siapa yang boleh        Workflow
                          mengoreksi kehadiran    
                          setelah sesi selesai?   

  OD-07                   Apakah guru pengganti   Validasi submit
                          belum terkonfirmasi     
                          menghalangi submit?     

  OD-08                   Ada batas waktu         Reminder/escalation
                          submit/verifikasi?      

  OD-09                   Bagaimana koreksi       Audit/workflow
                          jurnal yang sudah       
                          disetujui?              

  OD-10                   Apa definisi resmi      Pencatatan waktu
                          waktu aktual?           

  OD-11                   Apakah ada kalender     Kalender
                          akademik/hari libur     
                          untuk diimpor?          

  OD-12                   Apakah petugas kelas    Privasi
                          boleh melihat detail    
                          kehadiran atau hanya    
                          status kelengkapan?     
  -----------------------------------------------------------------------

Jangan menjawab open decisions dengan dugaan. Catat keputusan baru di
`docs/requirements/BUSINESS_RULES.md` atau ADR.

------------------------------------------------------------------------

# 16. Skenario Uji Penerimaan

**A. Hari normal** - Jadwal sudah tersedia. - Guru mengisi materi,
kehadiran, dan waktu aktual. - Petugas mengirim jurnal. - Guru piket
menyetujui. - Aktor dan timestamp tercatat.

**B. Dua JP berurutan** - Guru membuat satu sesi dua JP. - Sistem
memvalidasi urutan. - JP tidak dipakai sesi lain. - Jurnal menampilkan
cakupan kedua JP.

**C. Guru tidak hadir** - Petugas melaporkan ketidakhadiran. - Petugas
tidak dapat mengisi kehadiran sebagai guru. - Guru pengganti dapat
mengonfirmasi. - Piket melihat laporan.

**D. Belum diverifikasi saat siswa pulang** - Petugas mengirim jurnal. -
Status menjadi `SUBMITTED`. - Piket belum memeriksa. - Sistem
menampilkan "sudah dikirim, menunggu verifikasi". - Tidak ada aturan
yang menahan siswa pulang.

**E. Revisi** - Piket meminta revisi dengan catatan. - Petugas menerima
notifikasi. - Perbaikan menjadi versi baru. - Riwayat lama tersimpan. -
Jurnal masuk antrean review kembali.

**F. Jadwal khusus** - Senin JP 1 tampil sebagai Apel. - Jumat dua JP
pertama tampil sebagai Kokurikuler. - Istirahat bukan sesi pelajaran. -
`FREE` tidak mewajibkan jurnal guru. - Perubahan tanggal tidak mengubah
jurnal historis.

**G. Akses tidak sah** - Petugas mencoba mengubah kehadiran melalui API:
ditolak. - Guru non-pengajar mencoba mengubah sesi: ditolak. - Guru
non-piket membuka antrean verifikasi: ditolak.

------------------------------------------------------------------------

# 17. Cara Memulai Sesi Coding

1.  Baca dokumen ini.
2.  Tanyakan apakah repository sudah ada atau perlu dibuat.
3.  Periksa struktur dan file aktual sebelum mengubah apa pun.
4.  Jangan mengasumsikan dependency/framework sudah terpasang.
5.  Selesaikan Phase 0 untuk keputusan yang memengaruhi arsitektur.
6.  Buat SRS, business rules, ERD, API contract, dan state machine.
7.  Mulai Phase 1 setelah spesifikasi disetujui.
8.  Selesaikan satu fitur sampai dapat diuji.
9.  Jalankan tes otomatis dan berikan langkah tes manual.
10. Berhenti pada batas task besar dan minta konfirmasi sebelum
    melanjutkan.

**Target pertama bukan membuat banyak halaman. Target pertama adalah
membangun alur jurnal yang benar, aman, dapat diaudit, dan sesuai proses
nyata sekolah.**

## Ringkasan untuk AI coding assistant

JejakKBM adalah aplikasi jurnal KBM digital mobile-first dengan backend
Python FastAPI dan PostgreSQL. Administrator mengelola kelas, akun,
jadwal JP, pengecualian jadwal, dan penugasan guru piket. Guru pengajar
mengisi materi, kehadiran siswa, dan waktu aktual; hanya guru pengajar
yang boleh mengisi kehadiran. JP berurutan dapat digabung menjadi satu
sesi jika pembelajaran berkelanjutan. Setiap kelas memiliki satu petugas
jurnal utama yang melengkapi bagian kewenangannya dan mengirim jurnal
harian. Guru piket memverifikasi melalui antrean. Jurnal yang sudah
dikirim dianggap terkumpul walaupun belum diverifikasi, sehingga siswa
tidak harus menunggu persetujuan untuk pulang. Jadwal harus mendukung
apel Senin JP 1, kokurikuler Jumat dua JP pertama, istirahat, dan jam
kosong sebagai slot khusus. Semua tindakan penting harus memiliki audit
trail. Implementasikan bertahap berdasarkan task list; jangan mengarang
kebijakan yang belum diputuskan; jangan menandai fitur selesai sebelum
diuji.


---

# 16. Keputusan dan Implementasi Terbaru (2026-11-23)

Bagian ini memperbarui ketentuan lama yang masih menyebut proses penugasan dan konfirmasi guru pengganti.

## Guru mengambil alih sesi

- Tidak dibuat tabel `substitute_assignments`, endpoint penugasan guru pengganti, atau proses konfirmasi khusus.
- Petugas kelas cukup membuat laporan ketidakhadiran guru terjadwal pada JP terkait.
- Jika guru lain mengambil alih pembelajaran, guru tersebut menggunakan akun sendiri untuk membuat sesi.
- Backend mengizinkan guru aktif yang berbeda dari guru terjadwal hanya jika laporan ketidakhadiran tersedia untuk setiap JP yang dipilih dalam sesi.
- `teacher_id` pada sesi dan catatan absensi harus menunjukkan guru yang benar-benar mengajar.
- Hanya guru pengajar yang tercatat pada sesi yang dapat mengisi atau memperbaiki absensi sesi tersebut.

## Notifikasi dalam aplikasi

- Jurnal dikirim atau dikirim ulang: notifikasi diberikan kepada guru piket yang terdaftar pada tanggal jurnal.
- Jurnal diminta revisi, disetujui, atau ditolak: notifikasi diberikan kepada petugas kelas pemilik jurnal.
- Notifikasi memiliki status sudah/belum dibaca dan disimpan di database.
- Push notification HP belum termasuk implementasi backend ini.
- Selama login belum dibuat, endpoint notifikasi menggunakan `user_id` sebagai identitas sementara untuk pengembangan lokal.

## Update 2026-11-23 ? GUI Python Flet

- GUI tidak menggunakan file HTML/CSS/JavaScript buatan project. Implementasi GUI berada di `frontend/app.py` menggunakan Python + Flet.
- Flet menampilkan aplikasi melalui browser (Flutter Web yang dikelola Flet); kode antarmuka yang ditulis dalam project tetap Python.
- FastAPI tetap backend API di port 8000 dan SQLite tetap database. Flet berjalan terpisah di port 8550 dan memanggil API dengan HTTPX.
- FastAPI dipatok `>=0.115,<0.120` karena Flet Web 0.86.5 masih menggunakan argumen `openapi_prefix` yang tidak tersedia pada FastAPI versi terbaru.
- Menjalankan backend dari root project: `python -m uvicorn app.main:app --app-dir backend --reload`.
- Menjalankan GUI dari root project di terminal kedua: `python -m frontend.app`.
- GUI dibuka di `http://127.0.0.1:8550/JejakKBM`; dokumentasi API di `http://127.0.0.1:8000/docs`.
- GUI awal menyediakan login/bootstrap admin, pengelolaan akun dan kelas, pembuatan siswa, penetapan petugas kelas dan periodenya, pembuatan mata pelajaran serta slot jadwal, penugasan guru ke slot, jadwal guru piket, pembuatan dan pengiriman jurnal, laporan guru tidak hadir, inbox pemeriksaan guru piket, pembuatan sesi pembelajaran, input absensi per siswa, dan notifikasi.
- Pengujian backend setelah migrasi GUI: 112 passed, 1 warning. Endpoint Flet Web mengembalikan HTTP 200; endpoint `/health` backend juga HTTP 200.
- GUI masih perlu uji manual melalui browser, terutama rangkaian setup admin -> jurnal petugas kelas -> sesi dan absensi guru -> review guru piket. Beberapa input memakai ID hasil pembuatan data agar alur tetap sederhana. Jangan menganggap seluruh alur GUI sudah selesai hanya karena backend tests lulus.

## Redesign Update — Class Roster Attendance (2026-11-23)

- New class creation through `POST /classes/create-with-officer` now creates the class, one class-officer account, its assignment/period, and an anonymous class roster in one transaction.
- `roster_size` is configurable from 1–60 and defaults to 40. The admin GUI asks for the number of attendance numbers when creating the class.
- Username for the officer is generated from the class name using the `petugas_<class_slug>` convention.
- New `ClassRosterNumber` records contain only `class_id`, `attendance_number`, and `is_active`. No student name or NIS is required for attendance.
- New `ClassAttendanceRecord` records store attendance by session, JP, class, attendance number, teacher, and status. Legacy `Student` and `AttendanceRecord` tables remain for backward compatibility and historical records; do not drop them until a deliberate migration is designed.
- New endpoints:
  - `GET /classes/{class_id}/roster`
  - `PUT /classes/{class_id}/roster` with `roster_size`
  - `GET /journal-sessions/{session_id}/class-attendance`
  - `POST /journal-sessions/{session_id}/class-attendance`
- Attendance completeness and journal submission use the anonymous class roster when configured; otherwise they fall back to legacy student records.
- Teacher GUI attendance input now displays attendance numbers instead of student names and submits to the new class-attendance endpoint.
- Existing DB startup uses SQLAlchemy `create_all`, which creates the new tables without dropping old tables. Existing classes without a roster get a default 40-number roster when the roster endpoint is first requested.

## Update 2026-11-23 — Rekap Matriks dan Deteksi JP Guru

- Endpoint `GET /reports/class-attendance-matrix?class_id=...&start_date=...&end_date=...` menampilkan rekap nomor absen per tanggal untuk kelas yang dipilih.
- Kode matriks: H=Hadir, S=Sakit, I=Izin, D=Dispensasi, A=Alpa, -=belum ada catatan. Jika satu nomor memiliki beberapa catatan JP pada tanggal yang sama, matriks menampilkan status non-hadir dengan prioritas tertinggi (Alpa, Sakit, Dispensasi, Izin, Hadir).
- Status `DISPENSED` ditambahkan khusus pada alur absensi nomor absen; tabel lama tidak diubah.
- Dashboard kelas menghitung catatan dari `ClassAttendanceRecord` terlebih dahulu, lalu fallback ke `AttendanceRecord` lama bila sesi belum memakai roster anonim.
- Endpoint `GET /teachers/me/current-schedule` mengembalikan tanggal/jam WIB (`Asia/Jakarta`), slot guru hari ini, mapel, kelas, JP, dan status CURRENT/UPCOMING/FINISHED, serta jurnal/sesi terkait jika sudah ada.
- GUI admin memiliki bagian Rekap absensi per nomor absen; GUI guru menampilkan jadwal mengajar hari ini dan JP yang sedang berlangsung.
- Catatan: deteksi JP sudah membaca waktu server WIB saat endpoint dipanggil atau saat tombol perbarui ditekan. Pembaruan otomatis berkala belum dibuat. Pembuatan sesi guru masih menggunakan alur jurnal yang sudah ada; integrasi sekali klik dari JP aktif menjadi task berikutnya.
- Verifikasi: compileall, import Flet, tes matriks, tes jadwal WIB, dan seluruh test suite.

## Update 2026-11-23 — Quick Start Sesi Guru

- Added `POST /teachers/me/current-session` for teachers. It accepts a schedule slot ID and lesson material, optionally actual start/end times.
- The endpoint verifies the logged-in teacher owns the slot, the slot is a LESSON slot for the current weekday, and the subject assignment exists.
- It finds the active class-officer period and automatically creates today's DRAFT journal when missing. The journal is attributed to that class's active officer.
- It then creates a session for the single assigned slot using the existing session validation and audit logic.
- Teacher GUI now has a quick-start panel under today's WIB schedule: the teacher sees the active class/subject/JP, enters material and (optionally) actual times, then starts/saves the session without selecting a journal or mapel.
- The previous manual journal/session form remains as a fallback for consecutive JP grouping and older workflows. Attendance entry remains available through the existing session attendance section.
- Verification: compileall, Flet import, all tests (126 passed, 1 dependency deprecation warning), git diff --check.
- Remaining: manual browser interaction; periodic automatic refresh; make the attendance form auto-follow the newly created quick session; support alternate teacher flow with an approved absence report in the quick-start endpoint.

## Update 2026-11-23 — Absensi Langsung Setelah Quick Start Guru

- Teacher quick-start flow in `frontend/app.py` now keeps the newly created session ID and its active schedule slot in local page state.
- After `POST /teachers/me/current-session` succeeds, the GUI immediately loads the anonymous class roster using `GET /classes/{class_id}/roster` and existing records using `GET /journal-sessions/{session_id}/class-attendance`.
- The attendance form appears directly below the quick-start panel, showing the class and JP, recorded count, and only active attendance numbers that have not yet been submitted for that JP.
- The teacher selects H/S/I/D/A status per remaining number and saves with `POST /journal-sessions/{session_id}/class-attendance`; after saving, the form reloads and shows the updated recorded count.
- The quick attendance state retains the original slot details so it can refresh after the scheduled JP ends; it does not depend on the current-slot detector still returning an active slot.
- The older manual journal/session/attendance flow remains available for grouped consecutive JP sessions and fallback use.
- Verification after this GUI change: Python compileall passed, Flet import passed, backend tests 126 passed with 1 dependency deprecation warning, and `git diff --check` passed.
- GUI still requires manual browser interaction. In particular, verify the complete teacher flow with a real test class/teacher and confirm that the attendance records appear in the class dashboard/matrix.
