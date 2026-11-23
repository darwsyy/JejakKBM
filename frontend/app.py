"""Antarmuka JejakKBM menggunakan Python dan Flet."""

import os
from datetime import date

import flet as ft
import httpx

API_URL = os.getenv("JEJAKKBM_API_URL", "http://127.0.0.1:8000")


class ApiClient:
    def __init__(self):
        self.token = None

    def request(self, method, path, data=None, params=None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = httpx.request(
                method, f"{API_URL}{path}", json=data, params=params,
                headers=headers, timeout=15,
            )
        except httpx.RequestError as error:
            raise RuntimeError(
                "Backend belum berjalan. Jalankan FastAPI di port 8000 terlebih dahulu."
            ) from error

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"{response.status_code}: {detail}")

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def post(self, path, data):
        return self.request("POST", path, data=data)

    def put(self, path, data=None):
        return self.request("PUT", path, data=data)


def main(page: ft.Page):
    api = ApiClient()
    page.title = "JejakKBM"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 24
    page.window_min_width = 900
    page.window_min_height = 650
    page.scroll = ft.ScrollMode.AUTO

    def notify(message, error=False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
        )
        page.snack_bar.open = True
        page.update()

    def field(label, value="", password=False, width=320, multiline=False):
        return ft.TextField(
            label=label, value=value, password=password, can_reveal_password=password,
            width=width, multiline=multiline,
        )

    def button(label, action, primary=False):
        return ft.Button(
            label, on_click=action,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700 if primary else None,
                color=ft.Colors.WHITE if primary else None,
            ),
        )

    def heading(title, subtitle=None):
        items = [ft.Text(title, size=24, weight=ft.FontWeight.BOLD)]
        if subtitle:
            items.append(ft.Text(subtitle, color=ft.Colors.GREY_700))
        return ft.Column(items, spacing=4)

    def panel(title, controls):
        return ft.Container(
            content=ft.Column(
                [ft.Text(title, size=18, weight=ft.FontWeight.BOLD), *controls],
                spacing=12,
            ),
            padding=18,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=12,
            width=760,
        )

    def show_login(message=None):
        page.controls.clear()
        username = field("Username")
        password = field("Password", password=True)
        full_name = field("Nama lengkap (untuk admin pertama)")
        admin_password = field("Password admin pertama", password=True)

        def login(_):
            try:
                result = api.post("/auth/login", {
                    "username": username.value.strip(),
                    "password": password.value,
                })
                api.token = result["access_token"]
                show_home(result["user"])
            except Exception as error:
                notify(str(error), True)

        def bootstrap(_):
            try:
                api.post("/auth/bootstrap", {
                    "username": username.value.strip(),
                    "full_name": full_name.value.strip(),
                    "password": admin_password.value,
                })
                notify("Admin pertama berhasil dibuat. Silakan login.")
            except Exception as error:
                notify(str(error), True)

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("JejakKBM", size=34, weight=ft.FontWeight.BOLD),
                        ft.Text("Sistem Jurnal Kegiatan Belajar Mengajar"),
                        ft.Divider(),
                        username, password,
                        button("Masuk", login, True),
                        ft.Divider(),
                        ft.Text("Setup awal (hanya jika admin belum dibuat)", weight=ft.FontWeight.BOLD),
                        full_name, admin_password,
                        button("Buat admin pertama", bootstrap),
                        ft.Text(
                            message or "Pastikan backend FastAPI sudah aktif di http://127.0.0.1:8000",
                            color=ft.Colors.GREY_700,
                        ),
                    ],
                    width=420, spacing=14,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        )
        page.update()

    def show_home(user):
        page.controls.clear()
        role = user["role"]
        name = user["full_name"]

        def logout(_):
            try:
                api.post("/auth/logout", {})
            except Exception:
                pass
            api.token = None
            show_login("Kamu sudah logout.")

        def load_data(path, params=None):
            try:
                return api.get(path, params)
            except Exception as error:
                notify(str(error), True)
                return []

        def section(title, controls):
            page.add(panel(title, controls))

        page.add(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("JejakKBM", size=27, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{name} • {role.replace('_', ' ').title()}"),
                        ],
                        spacing=2,
                    ),
                    ft.Container(expand=True),
                    button("Logout", logout),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(),
        )

        if role == "admin":
            dashboard = load_data("/dashboard/daily", {"report_date": str(date.today())})
            section("Ringkasan hari ini", [
                ft.Text(f"Tanggal: {dashboard.get('report_date', date.today())}"),
                ft.Text(f"Total kelas: {dashboard.get('total_classes', 0)}"),
                ft.Text(f"Jurnal dibuat: {dashboard.get('total_journals', 0)}"),
                ft.Text(f"Belum membuat jurnal: {', '.join(dashboard.get('missing_classes', [])) or '-'}"),
                ft.Text(f"Status: {dashboard.get('status_counts', {})}"),
            ])

            users = load_data("/users")
            classes = load_data("/classes")
            section("Data pengguna", [
                ft.Text(f"Jumlah akun: {len(users)}"),
                ft.Text("\n".join(
                    f"ID {u['id']} • {u['full_name']} • {u['username']} • {u['role']}"
                    for u in users
                ) or "Belum ada akun."),
            ])
            new_username = field("Username")
            new_name = field("Nama lengkap")
            new_role = ft.Dropdown(
                label="Role", width=320, value="teacher",
                options=[
                    ft.DropdownOption(key="admin", text="Admin"),
                    ft.DropdownOption(key="teacher", text="Guru"),
                    ft.DropdownOption(key="class_officer", text="Petugas kelas"),
                ],
            )
            new_user_password = field("Password awal", password=True)

            def create_user(_):
                try:
                    if len(new_user_password.value) < 8:
                        raise RuntimeError("Password awal minimal 8 karakter.")
                    created = api.post("/users", {
                        "username": new_username.value.strip(),
                        "full_name": new_name.value.strip(),
                        "role": new_role.value,
                    })
                    api.put(f"/users/{created['id']}/password", {
                        "password": new_user_password.value,
                    })
                    notify(f"Akun {created['username']} berhasil dibuat.")
                    show_home(user)
                except Exception as error:
                    notify(str(error), True)

            section("Tambah akun", [
                new_username, new_name, new_role, new_user_password,
                button("Buat akun", create_user, True),
                ft.Text("Password awal langsung diatur setelah akun dibuat."),
            ])

            class_name = field("Nama kelas")
            academic_year = field("Tahun ajaran", "2026/2027")

            def create_class(_):
                try:
                    api.post("/classes", {
                        "name": class_name.value.strip(),
                        "academic_year": academic_year.value.strip(),
                    })
                    notify("Kelas berhasil dibuat.")
                    show_home(user)
                except Exception as error:
                    notify(str(error), True)

            section("Data kelas", [
                ft.Text(f"Jumlah kelas: {len(classes)}"),
                ft.Text("\n".join(
                    f"ID {c['id']} • {c['name']} • {c['academic_year']}" for c in classes
                ) or "Belum ada kelas."),
                class_name, academic_year,
                button("Tambah kelas", create_class, True),
            ])

            student_nis = field("NIS siswa")
            student_full_name = field("Nama siswa")
            student_class = ft.Dropdown(
                label="Kelas siswa", width=320,
                options=[ft.DropdownOption(key=str(c["id"]), text=f"{c['name']} (ID {c['id']})") for c in classes],
            )

            def create_student(_):
                try:
                    result = api.post("/students", {
                        "nis": student_nis.value.strip(),
                        "full_name": student_full_name.value.strip(),
                        "class_id": int(student_class.value),
                    })
                    notify(f"Siswa dibuat. ID siswa: {result['id']}")
                except Exception as error:
                    notify(str(error), True)

            section("Tambah siswa", [
                student_nis, student_full_name, student_class,
                button("Simpan siswa", create_student),
            ])

            officers = [u for u in users if u["role"] == "class_officer"]
            officer_class = ft.Dropdown(
                label="Kelas untuk petugas", width=320,
                options=[ft.DropdownOption(key=str(c["id"]), text=f"{c['name']} (ID {c['id']})") for c in classes],
            )
            officer_user = ft.Dropdown(
                label="Petugas kelas", width=320,
                options=[ft.DropdownOption(key=str(o["id"]), text=f"{o['full_name']} (ID {o['id']})") for o in officers],
            )
            officer_start = field("Mulai bertugas", str(date.today()))

            def assign_officer(_):
                try:
                    class_id = int(officer_class.value)
                    officer_id = int(officer_user.value)
                    try:
                        current = api.get(f"/classes/{class_id}/officer")
                    except RuntimeError as error:
                        if not str(error).startswith("404:"):
                            raise
                        current = None
                    if current is None:
                        api.put(f"/classes/{class_id}/officer/{officer_id}")
                    elif current["user_id"] != officer_id:
                        raise RuntimeError("Kelas sudah memiliki petugas jurnal utama yang berbeda.")
                    api.post(f"/classes/{class_id}/officer-periods", {
                        "user_id": officer_id,
                        "start_date": officer_start.value.strip(),
                        "end_date": None,
                    })
                    notify("Petugas jurnal kelas berhasil ditetapkan.")
                except Exception as error:
                    notify(str(error), True)

            section("Penetapan petugas jurnal kelas", [
                ft.Text("Pilih akun petugas dan tanggal mulai. Penetapan periode diperlukan agar petugas dapat membuat jurnal."),
                officer_class, officer_user, officer_start,
                button("Tetapkan petugas kelas", assign_officer, True),
            ])

            subject_name = field("Nama mata pelajaran")

            def create_subject(_):
                try:
                    result = api.post("/subjects", {"name": subject_name.value.strip()})
                    notify(f"Mata pelajaran dibuat. ID: {result['id']}")
                except Exception as error:
                    notify(str(error), True)

            section("Mata pelajaran", [
                subject_name, button("Tambah mata pelajaran", create_subject),
            ])

            schedule_class = ft.Dropdown(
                label="Kelas jadwal", width=320,
                options=[ft.DropdownOption(key=str(c["id"]), text=f"{c['name']} (ID {c['id']})") for c in classes],
            )
            schedule_day = ft.Dropdown(
                label="Hari", width=200, value="Monday",
                options=[ft.DropdownOption(key=d, text=d) for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]],
            )
            slot_order = field("Urutan slot", "1", width=150)
            jp_number = field("Nomor JP", "1", width=150)
            slot_start = field("Mulai", "07:00", width=150)
            slot_end = field("Selesai", "07:45", width=150)

            def create_slot(_):
                try:
                    result = api.post(f"/classes/{int(schedule_class.value)}/schedule-slots", {
                        "day_of_week": schedule_day.value,
                        "slot_order": int(slot_order.value),
                        "jp_number": int(jp_number.value),
                        "start_time": slot_start.value.strip(),
                        "end_time": slot_end.value.strip(),
                        "slot_type": "LESSON",
                    })
                    notify(f"Slot jadwal dibuat. ID slot: {result['id']}")
                except Exception as error:
                    notify(str(error), True)

            section("Tambah slot pelajaran", [
                ft.Text("Form ini membuat satu slot LESSON berdurasi 45 menit."),
                schedule_class, schedule_day,
                ft.Row([slot_order, jp_number]),
                ft.Row([slot_start, slot_end]),
                button("Buat slot jadwal", create_slot, True),
            ])

            slot_to_assign = field("ID slot")
            subject_to_assign = field("ID mata pelajaran")
            teacher_to_assign = ft.Dropdown(
                label="Guru pengajar", width=320,
                options=[ft.DropdownOption(key=str(t["id"]), text=f"{t['full_name']} (ID {t['id']})") for t in users if t["role"] == "teacher"],
            )

            def assign_subject(_):
                try:
                    api.put(f"/schedule-slots/{int(slot_to_assign.value)}/subject/{int(subject_to_assign.value)}")
                    notify("Mata pelajaran berhasil dipasang ke slot.")
                except Exception as error:
                    notify(str(error), True)

            def assign_teacher(_):
                try:
                    api.put(f"/schedule-slots/{int(slot_to_assign.value)}/teacher/{int(teacher_to_assign.value)}")
                    notify("Guru berhasil dipasang ke slot.")
                except Exception as error:
                    notify(str(error), True)

            section("Atur slot jadwal", [
                ft.Text("Masukkan ID slot dan ID mata pelajaran dari hasil pembuatan sebelumnya."),
                slot_to_assign, subject_to_assign, button("Pasang mata pelajaran", assign_subject),
                teacher_to_assign, button("Pasang guru", assign_teacher),
            ])

            teachers = [u for u in users if u["role"] == "teacher"]
            duty_date = field("Tanggal piket", str(date.today()))
            teacher_id = ft.Dropdown(
                label="Guru piket", width=320,
                options=[ft.DropdownOption(key=str(t["id"]), text=f"{t['full_name']} (ID {t['id']})") for t in teachers],
            )

            def assign_duty(_):
                try:
                    api.post("/duty-rosters", {
                        "duty_date": duty_date.value.strip(),
                        "teacher_user_id": int(teacher_id.value),
                        "assigned_by_user_id": user["id"],
                    })
                    notify("Jadwal guru piket berhasil disimpan.")
                except Exception as error:
                    notify(str(error), True)

            section("Penugasan guru piket", [
                duty_date, teacher_id, button("Simpan jadwal piket", assign_duty),
            ])

        elif role == "class_officer":
            classes = load_data("/classes")
            journals = load_data("/journals")
            class_options = [
                ft.DropdownOption(key=str(c["id"]), text=f"{c['name']} (ID {c['id']})")
                for c in classes
            ]
            class_choice = ft.Dropdown(label="Kelas", width=320, options=class_options)
            journal_date = field("Tanggal jurnal", str(date.today()))

            def create_journal(_):
                try:
                    result = api.post("/journals", {
                        "class_id": int(class_choice.value),
                        "journal_date": journal_date.value.strip(),
                        "officer_user_id": user["id"],
                    })
                    notify(f"Jurnal tanggal {result['journal_date']} siap. ID: {result['id']}")
                    show_home(user)
                except Exception as error:
                    notify(str(error), True)

            section("Buat jurnal harian", [
                class_choice, journal_date,
                button("Buat / buka jurnal", create_journal, True),
            ])

            journal_rows = []
            for journal in journals:
                class_label = next(
                    (c["name"] for c in classes if c["id"] == journal["class_id"]),
                    f"Kelas {journal['class_id']}",
                )
                journal_rows.append(
                    ft.Text(
                        f"Jurnal #{journal['id']} • {class_label} • "
                        f"{journal['journal_date']} • {journal['status']}"
                    )
                )
                if journal["officer_user_id"] == user["id"] and journal["status"] == "DRAFT":
                    def submit_journal(_, journal_id=journal["id"]):
                        try:
                            api.post(f"/journals/{journal_id}/submit", {
                                "officer_user_id": user["id"],
                            })
                            notify(f"Jurnal #{journal_id} berhasil dikirim.")
                            show_home(user)
                        except Exception as error:
                            notify(str(error), True)
                    journal_rows.append(button(f"Kirim jurnal #{journal['id']}", submit_journal))
            section("Daftar jurnal", journal_rows or [ft.Text("Belum ada jurnal.")])

            absence_journal_id = field("ID jurnal")
            absence_slot_id = field("ID slot JP")
            absence_note = field("Catatan (opsional)", width=600)

            def report_absence(_):
                try:
                    result = api.post(f"/journals/{int(absence_journal_id.value)}/absence-reports", {
                        "slot_id": int(absence_slot_id.value),
                        "officer_user_id": user["id"],
                        "notes": absence_note.value.strip() or None,
                    })
                    notify(f"Laporan guru tidak hadir tersimpan untuk JP {result['jp_number']}.")
                except Exception as error:
                    notify(str(error), True)

            section("Laporan guru tidak hadir", [
                ft.Text("Diperlukan jika guru yang mengisi sesi berbeda dari guru terjadwal."),
                absence_journal_id, absence_slot_id, absence_note,
                button("Simpan laporan", report_absence),
            ])

            notifications = load_data("/notifications", {"user_id": user["id"]})
            section("Notifikasi", [
                ft.Text(
                    "\n".join(f"{n['title']}: {n['message']}" for n in notifications)
                    or "Belum ada notifikasi."
                )
            ])

        elif role == "teacher":
            inbox = load_data("/reviews/inbox")
            notifications = load_data("/notifications", {"user_id": user["id"]})
            section("Notifikasi", [
                ft.Text(
                    "\n".join(f"{n['title']}: {n['message']}" for n in notifications)
                    or "Belum ada notifikasi."
                )
            ])

            review_controls = []
            for journal in inbox:
                classes = load_data("/classes")
                class_label = next(
                    (c["name"] for c in classes if c["id"] == journal["class_id"]),
                    f"Kelas {journal['class_id']}",
                )
                review_controls.append(
                    ft.Text(
                        f"Jurnal #{journal['id']} • {class_label} • "
                        f"{journal['journal_date']} • {journal['status']}",
                        weight=ft.FontWeight.BOLD,
                    )
                )
                note = field(f"Catatan jurnal #{journal['id']}", width=600)

                def review(_, journal_id=journal["id"], decision="APPROVE", note_field=note):
                    try:
                        api.post(f"/journals/{journal_id}/review", {
                            "reviewer_user_id": user["id"],
                            "decision": decision,
                            "notes": note_field.value.strip() or None,
                        })
                        notify(f"Jurnal #{journal_id} selesai diperiksa.")
                        show_home(user)
                    except Exception as error:
                        notify(str(error), True)

                review_controls.extend([
                    note,
                    ft.Row([
                        button("Setujui", lambda e, j=journal["id"], n=note: review(e, j, "APPROVE", n), True),
                        button("Minta revisi", lambda e, j=journal["id"], n=note: review(e, j, "REQUEST_REVISION", n)),
                        button("Tolak", lambda e, j=journal["id"], n=note: review(e, j, "REJECT", n)),
                    ])
                ])
            section("Antrean pemeriksaan guru piket", review_controls or [
                ft.Text("Tidak ada jurnal yang menunggu pemeriksaan.")
            ])

            journal_id = field("ID jurnal untuk mengisi sesi")
            slot_ids = field("ID slot JP (pisahkan koma)", "1")
            material = field("Materi pembelajaran", multiline=True, width=600)
            start_time = field("Jam mulai aktual", "07:00")
            end_time = field("Jam selesai aktual", "07:45")

            def create_session(_):
                try:
                    selected_slots = [
                        int(value.strip()) for value in slot_ids.value.split(",") if value.strip()
                    ]
                    result = api.post(f"/journals/{int(journal_id.value)}/sessions", {
                        "slot_ids": selected_slots,
                        "teacher_id": user["id"],
                        "material": material.value.strip(),
                        "actual_start_time": start_time.value.strip(),
                        "actual_end_time": end_time.value.strip(),
                    })
                    notify(f"Sesi pembelajaran berhasil dibuat. ID sesi: {result['id']}")
                except Exception as error:
                    notify(str(error), True)

            section("Isi sesi pembelajaran", [
                ft.Text("Gunakan ID slot dari jadwal kelas. Sesi hanya dapat dibuat untuk jurnal DRAFT."),
                journal_id, slot_ids, material,
                ft.Row([start_time, end_time]),
                button("Simpan sesi", create_session, True),
            ])

            session_id = field("ID sesi untuk absensi")
            attendance_slot_id = field("ID slot JP")
            student_id = field("ID siswa")
            attendance_status = ft.Dropdown(
                label="Status kehadiran", width=320, value="PRESENT",
                options=[
                    ft.DropdownOption(key="PRESENT", text="Hadir"),
                    ft.DropdownOption(key="SICK", text="Sakit"),
                    ft.DropdownOption(key="PERMITTED", text="Izin"),
                    ft.DropdownOption(key="ABSENT", text="Alpa"),
                ],
            )

            def save_attendance(_):
                try:
                    api.post(f"/journal-sessions/{int(session_id.value)}/attendance", {
                        "slot_id": int(attendance_slot_id.value),
                        "student_id": int(student_id.value),
                        "teacher_id": user["id"],
                        "attendance_status": attendance_status.value,
                    })
                    notify("Absensi siswa berhasil disimpan.")
                except Exception as error:
                    notify(str(error), True)

            section("Input absensi siswa", [
                ft.Text("Input satu siswa per penyimpanan. Hanya guru pengajar sesi yang dapat mengisi."),
                session_id, attendance_slot_id, student_id, attendance_status,
                button("Simpan absensi", save_attendance, True),
            ])

        else:
            section("Akun tidak dikenali", [
                ft.Text("Role akun ini belum didukung oleh tampilan JejakKBM.")
            ])

        page.update()

    show_login()


if __name__ == "__main__":
    ft.run(main, name="JejakKBM", host="0.0.0.0", port=8550, view=ft.AppView.WEB_BROWSER)
