"""Antarmuka JejakKBM menggunakan Python dan Flet."""

from datetime import date

import flet as ft

from frontend.api import ApiClient


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

            class_options = [
                ft.DropdownOption(key=str(c["id"]), text=c["name"])
                for c in classes
            ]
            student_nis = field("NIS siswa")
            student_full_name = field("Nama siswa")
            student_class = ft.Dropdown(
                label="Kelas siswa", width=320,
                options=class_options,
            )
            student_filter_class = ft.Dropdown(
                label="Tampilkan siswa kelas", width=320,
                options=class_options,
                value=str(classes[0]["id"]) if classes else None,
            )
            student_to_edit = ft.Dropdown(
                label="Pilih siswa untuk diedit", width=520, options=[],
            )
            student_edit_nis = field("NIS", width=250)
            student_edit_name = field("Nama lengkap", width=400)
            student_edit_class = ft.Dropdown(
                label="Pindahkan ke kelas", width=320,
                options=class_options,
            )
            student_list = ft.Column(spacing=4)
            loaded_students = []

            def refresh_student_list(_=None):
                loaded_students.clear()
                student_list.controls.clear()
                student_to_edit.options = []
                student_to_edit.value = None
                if not student_filter_class.value:
                    student_list.controls.append(ft.Text("Buat kelas terlebih dahulu."))
                    page.update()
                    return
                loaded_students.extend(api.get(
                    "/students",
                    {"class_id": int(student_filter_class.value)},
                ))
                student_to_edit.options = [
                    ft.DropdownOption(
                        key=str(item["id"]),
                        text=(
                            f"{item['full_name']} • NIS {item['nis']} "
                            f"({'Aktif' if item['is_active'] else 'Nonaktif'})"
                        ),
                    )
                    for item in loaded_students
                ]
                student_list.controls.extend([
                    ft.Text(
                        f"{item['full_name']} • NIS {item['nis']} • "
                        f"{'Aktif' if item['is_active'] else 'Nonaktif'}"
                    )
                    for item in loaded_students
                ] or [ft.Text("Belum ada siswa di kelas ini.")])
                page.update()

            def load_student_to_edit(_=None):
                selected = next(
                    (item for item in loaded_students
                     if str(item["id"]) == student_to_edit.value),
                    None,
                )
                if selected is None:
                    return
                student_edit_nis.value = selected["nis"]
                student_edit_name.value = selected["full_name"]
                student_edit_class.value = str(selected["class_id"])
                page.update()

            student_to_edit.on_change = load_student_to_edit
            student_filter_class.on_change = refresh_student_list

            def create_student(_):
                try:
                    result = api.post("/students", {
                        "nis": student_nis.value.strip(),
                        "full_name": student_full_name.value.strip(),
                        "class_id": int(student_class.value),
                    })
                    notify(f"Siswa dibuat. ID siswa: {result['id']}")
                    refresh_student_list()
                except Exception as error:
                    notify(str(error), True)

            def update_student(_):
                try:
                    if not student_to_edit.value:
                        raise RuntimeError("Pilih siswa yang akan diubah.")
                    student_id = int(student_to_edit.value)
                    api.put(f"/students/{student_id}", {
                        "nis": student_edit_nis.value.strip(),
                        "full_name": student_edit_name.value.strip(),
                        "class_id": int(student_edit_class.value),
                    })
                    notify("Data siswa berhasil diperbarui.")
                    refresh_student_list()
                except Exception as error:
                    notify(str(error), True)

            def deactivate_student(_):
                try:
                    if not student_to_edit.value:
                        raise RuntimeError("Pilih siswa yang akan dinonaktifkan.")
                    student_id = int(student_to_edit.value)
                    api.request("DELETE", f"/students/{student_id}")
                    notify("Siswa dinonaktifkan. Riwayat absensinya tetap tersimpan.")
                    refresh_student_list()
                except Exception as error:
                    notify(str(error), True)

            section("Tambah siswa", [
                student_nis, student_full_name, student_class,
                button("Simpan siswa", create_student),
            ])
            section("Daftar dan pengelolaan siswa", [
                student_filter_class,
                button("Muat ulang daftar siswa", refresh_student_list),
                student_list,
                student_to_edit,
                ft.Row([student_edit_nis, student_edit_name]),
                student_edit_class,
                ft.Row([
                    button("Simpan perubahan", update_student, True),
                    button("Nonaktifkan siswa", deactivate_student),
                ]),
            ])
            refresh_student_list()

            # Profil guru dihubungkan ke akun dengan role teacher.
            teacher_records = []
            teacher_account = ft.Dropdown(
                label="Akun guru yang belum memiliki profil", width=420,
                options=[],
            )
            teacher_nip = field("NIP guru (opsional)", width=320)
            teacher_to_edit = ft.Dropdown(
                label="Pilih profil guru", width=520, options=[],
            )
            teacher_edit_nip = field("Ubah NIP", width=320)
            teacher_list = ft.Column(spacing=4)

            def refresh_teacher_list(_=None):
                teacher_records.clear()
                teacher_records.extend(api.get("/teachers"))
                linked_user_ids = {item["user_id"] for item in teacher_records}
                available_accounts = [
                    account for account in users
                    if account["role"] == "teacher"
                    and account.get("is_active", True)
                    and account["id"] not in linked_user_ids
                ]
                teacher_account.options = [
                    ft.DropdownOption(
                        key=str(account["id"]),
                        text=f"{account['full_name']} • {account['username']}",
                    )
                    for account in available_accounts
                ]
                teacher_account.value = None
                teacher_to_edit.options = [
                    ft.DropdownOption(
                        key=str(item["id"]),
                        text=f"{item['full_name']} • {item['username']} "
                             f"({'Aktif' if item['is_active'] else 'Nonaktif'})",
                    )
                    for item in teacher_records
                ]
                teacher_to_edit.value = None
                teacher_list.controls = [
                    ft.Text(
                        f"{item['full_name']} • Akun: {item['username']} • "
                        f"NIP: {item['nip'] or '-'} • "
                        f"{'Aktif' if item['is_active'] else 'Nonaktif'}"
                    )
                    for item in teacher_records
                ] or [ft.Text("Belum ada profil guru.")]
                page.update()

            def load_teacher_to_edit(_=None):
                selected = next(
                    (item for item in teacher_records
                     if str(item["id"]) == teacher_to_edit.value),
                    None,
                )
                if selected is None:
                    return
                teacher_edit_nip.value = selected["nip"] or ""
                page.update()

            teacher_to_edit.on_change = load_teacher_to_edit

            def create_teacher_profile(_):
                try:
                    if not teacher_account.value:
                        raise RuntimeError("Pilih akun guru yang belum memiliki profil.")
                    result = api.post("/teachers", {
                        "user_id": int(teacher_account.value),
                        "nip": teacher_nip.value.strip() or None,
                    })
                    notify(f"Profil guru {result['full_name']} berhasil dibuat.")
                    refresh_teacher_list()
                except Exception as error:
                    notify(str(error), True)

            def update_teacher_profile(_):
                try:
                    if not teacher_to_edit.value:
                        raise RuntimeError("Pilih profil guru yang akan diubah.")
                    teacher_id = int(teacher_to_edit.value)
                    api.put(f"/teachers/{teacher_id}", {
                        "nip": teacher_edit_nip.value.strip() or None,
                    })
                    notify("NIP guru berhasil diperbarui.")
                    refresh_teacher_list()
                except Exception as error:
                    notify(str(error), True)

            def deactivate_teacher_profile(_):
                try:
                    if not teacher_to_edit.value:
                        raise RuntimeError("Pilih profil guru yang akan dinonaktifkan.")
                    teacher_id = int(teacher_to_edit.value)
                    api.request("DELETE", f"/teachers/{teacher_id}")
                    notify("Profil guru dinonaktifkan. Riwayat terkait tetap tersimpan.")
                    refresh_teacher_list()
                except Exception as error:
                    notify(str(error), True)

            section("Tambah profil guru", [
                ft.Text("Pilih akun ber-role Guru yang belum terhubung ke profil guru."),
                teacher_account, teacher_nip,
                button("Hubungkan akun dan buat profil", create_teacher_profile, True),
            ])
            section("Daftar dan pengelolaan guru", [
                button("Muat ulang daftar guru", refresh_teacher_list),
                teacher_list,
                teacher_to_edit, teacher_edit_nip,
                ft.Row([
                    button("Simpan perubahan NIP", update_teacher_profile, True),
                    button("Nonaktifkan profil", deactivate_teacher_profile),
                ]),
            ])
            refresh_teacher_list()

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
                    show_home(user)
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
            jp_number = field("Nomor JP (kosongkan untuk slot khusus)", "1", width=220)
            slot_start = field("Mulai", "07:00", width=150)
            slot_end = field("Selesai", "07:45", width=150)
            slot_type = ft.Dropdown(
                label="Jenis slot", width=320, value="LESSON",
                options=[
                    ft.DropdownOption(key="LESSON", text="Pelajaran"),
                    ft.DropdownOption(key="ASSEMBLY", text="Apel"),
                    ft.DropdownOption(key="COCURRICULAR", text="Kokurikuler"),
                    ft.DropdownOption(key="BREAK", text="Istirahat"),
                    ft.DropdownOption(key="FREE", text="Jam kosong"),
                    ft.DropdownOption(key="SPECIAL_EVENT", text="Acara khusus"),
                ],
            )

            def update_slot_type(_=None):
                is_lesson = slot_type.value == "LESSON"
                jp_number.disabled = not is_lesson
                if not is_lesson:
                    jp_number.value = ""
                elif not jp_number.value.strip():
                    jp_number.value = "1"
                page.update()

            slot_type.on_change = update_slot_type

            schedule_preview = ft.Column(spacing=4)

            def refresh_schedule_preview(_=None):
                schedule_preview.controls.clear()
                if not schedule_class.value:
                    schedule_preview.controls.append(ft.Text("Pilih kelas terlebih dahulu."))
                else:
                    slots = load_data(
                        f"/classes/{int(schedule_class.value)}/schedule-slots",
                        {"day": schedule_day.value},
                    )
                    type_names = {
                        "LESSON": "Pelajaran",
                        "ASSEMBLY": "Apel",
                        "COCURRICULAR": "Kokurikuler",
                        "BREAK": "Istirahat",
                        "FREE": "Jam kosong",
                        "SPECIAL_EVENT": "Acara khusus",
                    }
                    schedule_preview.controls.extend([
                        ft.Text(
                            f"Urutan {slot['slot_order']} • "
                            f"{type_names.get(slot['slot_type'], slot['slot_type'])} • "
                            f"{slot['start_time']}-{slot['end_time']}" +
                            (f" • JP {slot['jp_number']}" if slot["jp_number"] else "")
                        )
                        for slot in slots
                    ] or [ft.Text("Belum ada slot pada hari ini.")])
                page.update()

            schedule_class.on_change = refresh_schedule_preview
            schedule_day.on_change = refresh_schedule_preview
            refresh_schedule_preview()

            def create_slot(_):
                try:
                    selected_type = slot_type.value
                    jp_value = jp_number.value.strip()
                    if selected_type == "LESSON" and not jp_value:
                        raise RuntimeError("Slot pelajaran wajib memiliki nomor JP.")
                    result = api.post(f"/classes/{int(schedule_class.value)}/schedule-slots", {
                        "day_of_week": schedule_day.value,
                        "slot_order": int(slot_order.value),
                        "jp_number": int(jp_value) if selected_type == "LESSON" else None,
                        "start_time": slot_start.value.strip(),
                        "end_time": slot_end.value.strip(),
                        "slot_type": selected_type,
                    })
                    notify(f"Slot jadwal dibuat. ID slot: {result['id']}")
                    refresh_slot_options()
                    refresh_schedule_preview()
                except Exception as error:
                    notify(str(error), True)

            section("Tambah slot jadwal", [
                ft.Text(
                    "Pelajaran memakai nomor JP dan durasi 45 menit. "
                    "Slot khusus tidak perlu nomor JP dan boleh memiliki durasi berbeda."
                ),
                schedule_class, schedule_day, slot_type,
                ft.Row([slot_order, jp_number]),
                ft.Row([slot_start, slot_end]),
                button("Buat slot jadwal", create_slot, True),
            ])
            section("Jadwal kelas yang dipilih", [
                ft.Text("Daftar slot untuk kelas dan hari yang sedang dipilih."),
                schedule_preview,
            ])

            subjects = load_data("/subjects")
            teachers = [u for u in users if u["role"] == "teacher"]
            slot_to_assign = ft.Dropdown(label="Slot jadwal", width=520, options=[])
            subject_to_assign = ft.Dropdown(
                label="Mata pelajaran", width=320,
                options=[
                    ft.DropdownOption(key=str(s["id"]), text=s["name"])
                    for s in subjects
                ],
            )
            teacher_to_assign = ft.Dropdown(
                label="Guru pengajar", width=320,
                options=[
                    ft.DropdownOption(key=str(t["id"]), text=t["full_name"])
                    for t in teachers
                ],
            )

            def refresh_slot_options(_=None):
                if not schedule_class.value:
                    slot_to_assign.options = []
                    slot_to_assign.value = None
                else:
                    slots = load_data(
                        f"/classes/{int(schedule_class.value)}/schedule-slots",
                        {"day": schedule_day.value},
                    )
                    slot_to_assign.options = [
                        ft.DropdownOption(
                            key=str(slot["id"]),
                            text=(
                                f"JP {slot['jp_number']} • "
                                f"{slot['start_time']}-{slot['end_time']} "
                                f"(slot {slot['slot_order']})"
                            ),
                        )
                        for slot in slots if slot["slot_type"] == "LESSON"
                    ]
                    slot_to_assign.value = None
                page.update()

            def refresh_schedule_controls(_=None):
                refresh_schedule_preview()
                refresh_slot_options()

            schedule_class.on_change = refresh_schedule_controls
            schedule_day.on_change = refresh_schedule_controls
            refresh_slot_options()

            def assign_subject(_):
                try:
                    if not slot_to_assign.value or not subject_to_assign.value:
                        raise RuntimeError("Pilih slot dan mata pelajaran terlebih dahulu.")
                    api.put(
                        f"/schedule-slots/{int(slot_to_assign.value)}/subject/"
                        f"{int(subject_to_assign.value)}"
                    )
                    notify("Mata pelajaran berhasil dipasang ke slot.")
                except Exception as error:
                    notify(str(error), True)

            def assign_teacher(_):
                try:
                    if not slot_to_assign.value or not teacher_to_assign.value:
                        raise RuntimeError("Pilih slot dan guru terlebih dahulu.")
                    api.put(
                        f"/schedule-slots/{int(slot_to_assign.value)}/teacher/"
                        f"{int(teacher_to_assign.value)}"
                    )
                    notify("Guru berhasil dipasang ke slot.")
                except Exception as error:
                    notify(str(error), True)

            section("Atur slot jadwal", [
                ft.Text("Slot diambil otomatis dari kelas dan hari yang dipilih."),
                slot_to_assign, subject_to_assign,
                button("Pasang mata pelajaran", assign_subject),
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
            all_journals = load_data("/journals")
            journals = [
                item for item in all_journals
                if item["officer_user_id"] == user["id"]
            ]
            journal_date = field("Tanggal jurnal", str(date.today()))
            class_choice = ft.Dropdown(
                label="Kelas yang ditugaskan", width=360, options=[],
            )

            def refresh_officer_classes(_=None):
                class_choice.options = []
                class_choice.value = None
                try:
                    selected_date = journal_date.value.strip()
                    assigned_classes = []
                    for classroom in classes:
                        try:
                            assignment = api.get(
                                f"/classes/{classroom['id']}/officer-current",
                                {"on_date": selected_date},
                            )
                        except RuntimeError as error:
                            if str(error).startswith("404:"):
                                continue
                            raise
                        if assignment["user_id"] == user["id"]:
                            assigned_classes.append(classroom)
                    class_choice.options = [
                        ft.DropdownOption(
                            key=str(item["id"]), text=item["name"]
                        )
                        for item in assigned_classes
                    ]
                    if not assigned_classes:
                        notify("Tidak ada kelas yang ditugaskan ke akun ini pada tanggal tersebut.", True)
                except Exception as error:
                    notify(str(error), True)
                page.update()

            journal_date.on_change = refresh_officer_classes
            refresh_officer_classes()

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
                journal_detail = ft.Column(spacing=4)

                def show_officer_journal_detail(
                    _, class_id=journal["class_id"],
                    journal_date=journal["journal_date"],
                    target=journal_detail,
                ):
                    try:
                        detail = api.get(
                            f"/dashboard/classes/{class_id}",
                            {"report_date": journal_date},
                        )
                        lines = [
                            f"Status: {detail['journal_status']}",
                            f"Jumlah sesi: {detail['total_sessions']}",
                            "Rekap kehadiran: " + ", ".join(
                                f"{key}: {value}"
                                for key, value in detail["attendance_counts"].items()
                            ),
                        ]
                        for session in detail["sessions"]:
                            lines.extend([
                                f"JP {', '.join(map(str, session['jp_numbers']))} • "
                                f"{session['subject_name']} • {session['teacher_name']}",
                                f"Materi: {session['material']}",
                                f"Waktu aktual: {session['actual_start_time']}-"
                                f"{session['actual_end_time']}",
                            ])
                        target.controls = [ft.Text(line) for line in lines]
                        page.update()
                    except Exception as error:
                        notify(str(error), True)

                journal_rows.append(
                    button("Lihat ringkasan jurnal", show_officer_journal_detail)
                )
                journal_rows.append(journal_detail)
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

            absence_journal = ft.Dropdown(
                label="Jurnal", width=560,
                options=[
                    ft.DropdownOption(
                        key=str(item["id"]),
                        text=(
                            f"#{item['id']} • "
                            f"{next((c['name'] for c in classes if c['id'] == item['class_id']), 'Kelas')} • "
                            f"{item['journal_date']} • {item['status']}"
                        ),
                    )
                    for item in journals if item["status"] == "DRAFT"
                ],
            )
            absence_slot = ft.Dropdown(
                label="JP guru tidak hadir", width=420, options=[],
            )
            absence_note = field("Catatan (opsional)", width=600)

            def load_absence_slots(_):
                absence_slot.options = []
                if not absence_journal.value:
                    page.update()
                    return
                selected = next(
                    item for item in journals if item["id"] == int(absence_journal.value)
                )
                schedule = load_data(
                    f"/classes/{selected['class_id']}/daily-schedule",
                    {"on_date": selected["journal_date"]},
                )
                absence_slot.options = [
                    ft.DropdownOption(
                        key=str(slot["slot_id"]),
                        text=(
                            f"JP {slot['jp_number']} • {slot['start_time']}-"
                            f"{slot['end_time']} • "
                            f"{slot['scheduled_teacher_name'] or 'Guru belum diatur'}"
                        ),
                    )
                    for slot in schedule.get("slots", [])
                    if slot["slot_type"] == "LESSON" and slot["jp_number"] is not None
                ]
                absence_slot.value = None
                page.update()

            absence_journal.on_change = load_absence_slots

            def report_absence(_):
                try:
                    if not absence_journal.value or not absence_slot.value:
                        raise RuntimeError("Pilih jurnal dan JP terlebih dahulu.")
                    result = api.post(
                        f"/journals/{int(absence_journal.value)}/absence-reports",
                        {
                            "slot_id": int(absence_slot.value),
                            "officer_user_id": user["id"],
                            "notes": absence_note.value.strip() or None,
                        },
                    )
                    notify(
                        f"Laporan guru tidak hadir tersimpan untuk JP {result['jp_number']}."
                    )
                except Exception as error:
                    notify(str(error), True)

            section("Laporan guru tidak hadir", [
                ft.Text("Pilih jurnal dan JP dari jadwal kelas. Diperlukan jika guru pengisi berbeda dari guru terjadwal."),
                absence_journal, absence_slot, absence_note,
                button("Muat daftar JP", load_absence_slots),
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
            duty_rosters = load_data("/duty-rosters", {"duty_date": str(date.today())})
            is_duty_teacher = any(
                roster["teacher_user_id"] == user["id"]
                for roster in duty_rosters
            )
            inbox = load_data("/reviews/inbox") if is_duty_teacher else []
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
                detail_area = ft.Column(spacing=4)

                def show_journal_detail(
                    _, class_id=journal["class_id"],
                    journal_date=journal["journal_date"],
                    target=detail_area,
                ):
                    try:
                        detail = api.get(
                            f"/dashboard/classes/{class_id}",
                            {"report_date": journal_date},
                        )
                        lines = [
                            f"Status jurnal: {detail['journal_status']}",
                            f"Jumlah sesi: {detail['total_sessions']}",
                            "Rekap kehadiran: " + ", ".join(
                                f"{key}: {value}"
                                for key, value in detail["attendance_counts"].items()
                            ),
                        ]
                        for session in detail["sessions"]:
                            lines.extend([
                                f"JP {', '.join(map(str, session['jp_numbers']))} • "
                                f"{session['subject_name']} • {session['teacher_name']}",
                                f"Materi: {session['material']}",
                                f"Waktu aktual: {session['actual_start_time']}-"
                                f"{session['actual_end_time']}",
                                "Absensi: " + ", ".join(
                                    f"{key}: {value}"
                                    for key, value in session["attendance_counts"].items()
                                ),
                            ])
                        if detail["reviews"]:
                            lines.append("Riwayat pemeriksaan:")
                            lines.extend(
                                f"{item['decision']} • {item['reviewer_name']} • "
                                f"{item['notes'] or '-'}"
                                for item in detail["reviews"]
                            )
                        target.controls = [ft.Text(line) for line in lines]
                        page.update()
                    except Exception as error:
                        notify(str(error), True)

                review_controls.append(
                    button("Lihat detail jurnal", show_journal_detail)
                )
                review_controls.append(detail_area)
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
                ft.Text(
                    "Tidak ada jurnal yang menunggu pemeriksaan."
                    if is_duty_teacher
                    else "Kamu tidak dijadwalkan sebagai guru piket hari ini. Fitur mengajar tetap tersedia."
                )
            ])

            classes = load_data("/classes")
            class_names = {item["id"]: item["name"] for item in classes}
            journals = load_data("/journals")
            journal_options = [
                ft.DropdownOption(
                    key=str(item["id"]),
                    text=(
                        f"#{item['id']} • {class_names.get(item['class_id'], 'Kelas')} • "
                        f"{item['journal_date']} • {item['status']}"
                    ),
                )
                for item in journals if item["status"] == "DRAFT"
            ]
            journal_choice = ft.Dropdown(
                label="Jurnal kelas", width=560, options=journal_options,
            )
            material = field("Materi pembelajaran", multiline=True, width=600)
            start_time = field("Jam mulai aktual", "07:00")
            end_time = field("Jam selesai aktual", "07:45")
            slot_checks = []
            schedule_info = ft.Column(spacing=4)

            def load_journal_slots(_):
                slot_checks.clear()
                schedule_info.controls.clear()
                if not journal_choice.value:
                    notify("Pilih jurnal terlebih dahulu.", True)
                    return
                selected_journal = next(
                    item for item in journals if item["id"] == int(journal_choice.value)
                )
                schedule = load_data(
                    f"/classes/{selected_journal['class_id']}/daily-schedule",
                    {"on_date": selected_journal["journal_date"]},
                )
                for slot in schedule.get("slots", []):
                    if slot["slot_type"] != "LESSON" or slot["jp_number"] is None:
                        continue
                    label = (
                        f"JP {slot['jp_number']} • {slot['start_time']}-{slot['end_time']} • "
                        f"{slot['subject_name'] or 'Mapel belum diatur'} • "
                        f"{slot['scheduled_teacher_name'] or 'Guru belum diatur'}"
                    )
                    check = ft.Checkbox(
                        label=label, value=False, data=slot["slot_id"]
                    )
                    slot_checks.append(check)
                    schedule_info.controls.append(check)
                if not slot_checks:
                    schedule_info.controls.append(
                        ft.Text("Tidak ada slot pelajaran pada tanggal jurnal ini.")
                    )
                page.update()

            def create_session(_):
                try:
                    if not journal_choice.value:
                        raise RuntimeError("Pilih jurnal terlebih dahulu.")
                    selected_slots = [
                        int(check.data) for check in slot_checks if check.value
                    ]
                    if not selected_slots:
                        raise RuntimeError("Pilih minimal satu JP.")
                    result = api.post(
                        f"/journals/{int(journal_choice.value)}/sessions",
                        {
                            "slot_ids": selected_slots,
                            "teacher_id": user["id"],
                            "material": material.value.strip(),
                            "actual_start_time": start_time.value.strip(),
                            "actual_end_time": end_time.value.strip(),
                        },
                    )
                    notify(f"Sesi pembelajaran berhasil dibuat. ID sesi: {result['id']}")
                    load_sessions(None)
                except Exception as error:
                    notify(str(error), True)

            section("Isi sesi pembelajaran", [
                ft.Text("Pilih jurnal, muat jadwal, lalu centang satu atau beberapa JP berurutan."),
                journal_choice, button("Muat jadwal JP", load_journal_slots),
                schedule_info, material,
                ft.Row([start_time, end_time]),
                button("Simpan sesi", create_session, True),
            ])

            session_choice = ft.Dropdown(
                label="Sesi pembelajaran", width=560, options=[],
            )
            attendance_slot = ft.Dropdown(
                label="JP untuk absensi", width=320, options=[],
            )
            attendance_form = ft.Column(spacing=6)
            attendance_rows = []
            attendance_status_options = [
                ft.DropdownOption(key="PRESENT", text="Hadir"),
                ft.DropdownOption(key="SICK", text="Sakit"),
                ft.DropdownOption(key="PERMITTED", text="Izin"),
                ft.DropdownOption(key="ABSENT", text="Alpa"),
            ]
            loaded_sessions = []

            def load_sessions(_):
                session_choice.options = []
                attendance_slot.options = []
                attendance_form.controls.clear()
                attendance_rows.clear()
                loaded_sessions.clear()
                if not journal_choice.value:
                    page.update()
                    return
                loaded_sessions.extend(
                    api.get(f"/journals/{int(journal_choice.value)}/sessions")
                )
                session_choice.options = [
                    ft.DropdownOption(
                        key=str(item["id"]),
                        text=f"Sesi #{item['id']} • {item['subject_name']} • JP {', '.join(map(str, item['jp_numbers']))}",
                    )
                    for item in loaded_sessions
                ]
                if loaded_sessions:
                    session_choice.value = str(loaded_sessions[-1]["id"])
                    load_session_options(None)
                page.update()

            def load_session_options(_):
                selected = next(
                    (item for item in loaded_sessions
                     if str(item["id"]) == session_choice.value),
                    None,
                )
                if selected is None:
                    attendance_slot.options = []
                    attendance_form.controls = [ft.Text("Pilih sesi terlebih dahulu.")]
                    attendance_rows.clear()
                    page.update()
                    return
                attendance_slot.options = [
                    ft.DropdownOption(
                        key=str(slot_id), text=f"JP {jp_number}"
                    )
                    for slot_id, jp_number in zip(
                        selected["slot_ids"], selected["jp_numbers"]
                    )
                ]
                valid_slot_ids = [option.key for option in attendance_slot.options]
                if attendance_slot.value not in valid_slot_ids:
                    attendance_slot.value = (
                        attendance_slot.options[0].key
                        if attendance_slot.options else None
                    )
                selected_journal = next(
                    item for item in journals if item["id"] == int(journal_choice.value)
                )
                students = load_data(
                    "/students", {"class_id": selected_journal["class_id"]}
                )
                existing_records = load_data(
                    f"/journal-sessions/{selected['id']}/attendance"
                )
                recorded_ids = {
                    item["student_id"] for item in existing_records
                    if item["slot_id"] == int(attendance_slot.value)
                }
                attendance_rows.clear()
                attendance_form.controls.clear()
                if recorded_ids:
                    attendance_form.controls.append(
                        ft.Text(f"Absensi sudah tercatat untuk {len(recorded_ids)} siswa.")
                    )
                for student in students:
                    if not student["is_active"] or student["id"] in recorded_ids:
                        continue
                    status_choice = ft.Dropdown(
                        width=150, value="PRESENT",
                        options=attendance_status_options,
                    )
                    attendance_rows.append((student["id"], status_choice))
                    attendance_form.controls.append(
                        ft.Row([
                            ft.Text(student["full_name"], width=300),
                            status_choice,
                        ])
                    )
                if not attendance_rows:
                    attendance_form.controls.append(
                        ft.Text("Semua siswa aktif sudah memiliki catatan absensi untuk sesi ini.")
                    )
                page.update()

            session_choice.on_change = load_session_options
            attendance_slot.on_change = load_session_options

            def save_attendance(_):
                try:
                    if not session_choice.value or not attendance_slot.value:
                        raise RuntimeError("Pilih sesi dan JP terlebih dahulu.")
                    if not attendance_rows:
                        raise RuntimeError("Tidak ada siswa baru yang perlu dicatat.")
                    api.post(
                        f"/journal-sessions/{int(session_choice.value)}/attendance/batch",
                        {
                            "slot_id": int(attendance_slot.value),
                            "teacher_id": user["id"],
                            "records": [
                                {
                                    "student_id": student_id,
                                    "attendance_status": status_choice.value,
                                }
                                for student_id, status_choice in attendance_rows
                            ],
                        },
                    )
                    notify(f"Absensi {len(attendance_rows)} siswa berhasil disimpan.")
                    load_session_options(None)
                except Exception as error:
                    notify(str(error), True)

            section("Input absensi siswa", [
                ft.Text("Daftar sesi, JP, dan siswa diambil dari jurnal yang dipilih."),
                button("Muat / perbarui daftar sesi", load_sessions),
                session_choice, attendance_slot, attendance_form,
                button("Simpan absensi seluruh siswa", save_attendance, True),
            ])

        else:
            section("Akun tidak dikenali", [
                ft.Text("Role akun ini belum didukung oleh tampilan JejakKBM.")
            ])

        page.update()

    show_login()


if __name__ == "__main__":
    ft.run(main, name="JejakKBM", host="0.0.0.0", port=8550, view=ft.AppView.WEB_BROWSER)
