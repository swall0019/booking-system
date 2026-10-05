import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import database as db
from style import COLORS, FONTS, ICONS, apply_theme, set_theme
from widgets import FilterableTable

try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False


class MainWindow:
    def __init__(self, user):
        self.user_id, self.username, self.role = user
        self.is_admin = (self.role == "admin")
        self.is_manager = (self.role == "manager")

        self.settings = db.load_settings()

        self.root = tk.Tk()
        self.root.title(f"Система бронирования — {self.username}")
        self.root.geometry("1250x780")
        self.root.minsize(1100, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Применить тему из настроек
        set_theme(self.settings.get("theme", "light"))
        apply_theme(self.root)

        self.build_ui()
        self.refresh_all()

    # =========================================================
    #  ВЕРХНЯЯ ПАНЕЛЬ
    # =========================================================
    def build_header(self):
        header = tk.Frame(self.root, bg=COLORS["header"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=COLORS["header"])
        left.pack(side="left", padx=20)

        tk.Label(left, text=ICONS["building"], bg=COLORS["header"], fg="white",
                 font=("Segoe UI Emoji", 20)).pack(side="left", padx=(0, 10))

        titles = tk.Frame(left, bg=COLORS["header"])
        titles.pack(side="left")
        tk.Label(titles, text="Система бронирования переговорных",
                 bg=COLORS["header"], fg="white",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(titles, text="Управление помещениями и встречами",
                 bg=COLORS["header"], fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(anchor="w")

        right = tk.Frame(header, bg=COLORS["header"])
        right.pack(side="right", padx=20)

        # Кнопка смены темы
        self.theme_btn = tk.Label(right, text=ICONS["moon"], bg=COLORS["header"],
                                  fg="white", font=("Segoe UI Emoji", 16), cursor="hand2")
        self.theme_btn.pack(side="right", padx=(10, 0))
        self.theme_btn.bind("<Button-1>", lambda e: self.toggle_theme())

        role_map = {
            "admin":   (ICONS["admin"], "Администратор"),
            "manager": (ICONS["manager"], "Менеджер"),
            "user":    (ICONS["user"], "Пользователь"),
        }
        icon, label = role_map.get(self.role, (ICONS["user"], "Пользователь"))

        user_box = tk.Frame(right, bg=COLORS["header"])
        user_box.pack(side="right")
        tk.Label(user_box, text=f"{icon} {label}", bg=COLORS["header"], fg="#94a3b8",
                 font=FONTS["small"]).pack(anchor="e")
        tk.Label(user_box, text=self.username, bg=COLORS["header"], fg="white",
                 font=FONTS["h3"]).pack(anchor="e")

    def toggle_theme(self):
        new_theme = "dark" if self.settings.get("theme", "light") == "light" else "light"
        self.settings["theme"] = new_theme
        db.save_settings(self.settings)
        set_theme(new_theme)
        # Пересобрать интерфейс
        for w in self.root.winfo_children():
            w.destroy()
        apply_theme(self.root)
        self.build_ui()
        self.refresh_all()
        self.theme_btn.config(text=ICONS["sun"] if new_theme == "dark" else ICONS["moon"])

    # =========================================================
    #  ОБЩАЯ СБОРКА
    # =========================================================
    def build_ui(self):
        self.build_header()

        container = tk.Frame(self.root, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=16, pady=16)

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)

        self.tab_all = ttk.Frame(self.notebook, style="TFrame")
        self.tab_bookings = ttk.Frame(self.notebook, style="TFrame")
        self.tab_new = ttk.Frame(self.notebook, style="TFrame")
        self.tab_free = ttk.Frame(self.notebook, style="TFrame")
        self.tab_rooms = ttk.Frame(self.notebook, style="TFrame")

        self.notebook.add(self.tab_all,      text="📋  Все брони")
        self.notebook.add(self.tab_bookings, text="👤  Мои брони")
        self.notebook.add(self.tab_new,      text="➕  Новое бронирование")
        self.notebook.add(self.tab_free,     text="🔍  Поиск свободных")
        self.notebook.add(self.tab_rooms,    text="🏢  Помещения")

        self.build_all_bookings_tab()
        self.build_bookings_tab()
        self.build_new_booking_tab()
        self.build_free_rooms_tab()
        self.build_rooms_tab()

    # =========================================================
    #  ВКЛАДКА: ВСЕ БРОНИ
    # =========================================================
    def build_all_bookings_tab(self):
        top = tk.Frame(self.tab_all, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 10))

        tk.Label(top, text="Общий календарь — кто и когда занял помещение",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=FONTS["h2"]).pack(side="left")

        btns = tk.Frame(top, bg=COLORS["bg"])
        btns.pack(side="right")
        ttk.Button(btns, text=f"{ICONS['refresh']} Обновить", style="Ghost.TButton",
                   command=self.refresh_all_bookings).pack(side="left", padx=4)

        columns = [
            ("id",      "ID",            60,  "center"),
            ("room",    "Помещение",     170, "w"),
            ("user",    "Забронировал",  140, "center"),
            ("date",    "Дата",          110, "center"),
            ("start",   "Начало",        80,  "center"),
            ("end",     "Конец",         80,  "center"),
            ("purpose", "Цель встречи",  260, "w"),
            ("recur",   "Повтор",        90,  "center"),
            ("attach",  "Файл",          60,  "center"),
        ]
        filters = [
            {"key": "room",    "label": "Помещение",    "type": "select"},
            {"key": "user",    "label": "Кто занял",    "type": "select"},
            {"key": "date",    "label": "Дата",         "type": "text"},
            {"key": "purpose", "label": "Цель",         "type": "text"},
        ]
        self.table_all = FilterableTable(self.tab_all, columns, filters)
        self.table_all.pack(fill="both", expand=True)
        self.table_all.tree.tag_configure("mine", background="#dbeafe")
        self.table_all.tree.tag_configure("other", background=COLORS["card"])

    # =========================================================
    #  ВКЛАДКА: МОИ БРОНИ
    # =========================================================
    def build_bookings_tab(self):
        top = tk.Frame(self.tab_bookings, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 10))

        self.stat_rooms = self.make_stat_card(top, ICONS["building"], "Помещений", "0", COLORS["accent"])
        self.stat_total = self.make_stat_card(top, "📋", "Всего броней", "0", COLORS["success"])
        self.stat_today = self.make_stat_card(top, ICONS["calendar"], "На сегодня", "0", COLORS["warning"])

        btns = tk.Frame(top, bg=COLORS["bg"])
        btns.pack(side="right", padx=(10, 0))
        ttk.Button(btns, text=f"{ICONS['refresh']} Обновить", style="Ghost.TButton",
                   command=self.refresh_bookings).pack(side="left", padx=4)
        ttk.Button(btns, text=f"{ICONS['edit']} Изменить", style="Accent.TButton",
                   command=self.edit_booking).pack(side="left", padx=4)
        ttk.Button(btns, text=f"{ICONS['trash']} Удалить", style="Danger.TButton",
                   command=self.delete_booking).pack(side="left", padx=4)

        columns = [
            ("id",      "ID",            60,  "center"),
            ("room",    "Помещение",     170, "w"),
            ("user",    "Пользователь",  130, "center"),
            ("date",    "Дата",          110, "center"),
            ("start",   "Начало",        80,  "center"),
            ("end",     "Конец",         80,  "center"),
            ("purpose", "Цель встречи",  240, "w"),
            ("recur",   "Повтор",        90,  "center"),
            ("attach",  "Файл",          60,  "center"),
        ]
        filters = [
            {"key": "room",    "label": "Помещение", "type": "select"},
            {"key": "date",    "label": "Дата",      "type": "text"},
            {"key": "purpose", "label": "Цель",      "type": "text"},
        ]
        self.table_bookings = FilterableTable(self.tab_bookings, columns, filters)
        self.table_bookings.pack(fill="both", expand=True)

    def make_stat_card(self, parent, icon, label, value, color):
        card = tk.Frame(parent, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(side="left", padx=(0, 10))

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(padx=16, pady=10)

        tk.Label(inner, text=icon, bg=COLORS["card"], fg=color,
                 font=("Segoe UI Emoji", 18)).pack(side="left", padx=(0, 10))

        texts = tk.Frame(inner, bg=COLORS["card"])
        texts.pack(side="left")
        tk.Label(texts, text=label, bg=COLORS["card"], fg=COLORS["muted"],
                 font=FONTS["small"]).pack(anchor="w")
        val_label = tk.Label(texts, text=value, bg=COLORS["card"], fg=COLORS["text"],
                             font=FONTS["h2"])
        val_label.pack(anchor="w")
        card.value_label = val_label
        return card

    # =========================================================
    #  ВКЛАДКА: НОВОЕ БРОНИРОВАНИЕ
    # =========================================================
    def build_new_booking_tab(self):
        wrapper = tk.Frame(self.tab_new, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True)

        left_card = tk.Frame(wrapper, bg=COLORS["card"], highlightthickness=1,
                             highlightbackground=COLORS["border"])
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        right_card = tk.Frame(wrapper, bg=COLORS["card"], highlightthickness=1,
                              highlightbackground=COLORS["border"])
        right_card.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        self.build_booking_form(left_card)
        self.build_busy_panel(right_card)

    def build_booking_form(self, card):
        self.editing_id = None  # если редактируем — сюда ID

        tk.Label(card, text="Новое бронирование", bg=COLORS["card"],
                 fg=COLORS["text"], font=FONTS["h1"]).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4))
        tk.Label(card, text="Заполните поля и нажмите «Забронировать»",
                 bg=COLORS["card"], fg=COLORS["muted"], font=FONTS["small"]).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 16))

        card.columnconfigure(1, weight=1)
        row = [2]

        def label(text):
            tk.Label(card, text=text, bg=COLORS["card"], fg=COLORS["text"],
                     font=FONTS["h3"]).grid(row=row[0], column=0, sticky="w",
                                            padx=(24, 10), pady=8)

        def place(widget, cspan=1):
            widget.grid(row=row[0], column=1, columnspan=cspan, sticky="ew",
                        padx=(0, 24), pady=8)

        # Помещение
        label("Помещение")
        self.combo_room = ttk.Combobox(card, state="readonly", font=FONTS["body"])
        self.combo_room.bind("<<ComboboxSelected>>", lambda e: self.update_busy_panel())
        place(self.combo_room)
        row[0] += 1

        # Дата (календарь или обычный ввод)
        label("Дата")
        if HAS_CALENDAR:
            date_wrap = tk.Frame(card, bg=COLORS["card"])
            self.cal = DateEntry(date_wrap, width=12, date_pattern="yyyy-mm-dd",
                                 font=FONTS["body"], background=COLORS["accent"],
                                 foreground="white", borderwidth=0)
            self.cal.pack(side="left")
            self.cal.bind("<<DateEntrySelected>>", lambda e: self.update_busy_panel())
            self.entry_date = self.cal
            tk.Label(date_wrap, text="  (можно выбрать из календаря)",
                     bg=COLORS["card"], fg=COLORS["muted"],
                     font=FONTS["small"]).pack(side="left")
            place(date_wrap)
        else:
            self.entry_date = ttk.Entry(card)
            self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
            self.entry_date.bind("<FocusOut>", lambda e: self.update_busy_panel())
            place(self.entry_date)
            tk.Label(card, text="(tkcalendar не установлен — вводите вручную)",
                     bg=COLORS["card"], fg=COLORS["warning"],
                     font=FONTS["small"]).grid(row=row[0] + 1, column=1, sticky="w",
                                               padx=(0, 24), pady=(0, 6))
        row[0] += 1

        # Начало
        label("Начало (ЧЧ:ММ)")
        self.entry_start = ttk.Entry(card)
        self.entry_start.insert(0, "10:00")
        self.entry_start.bind("<KeyRelease>", lambda e: self.validate_time_field())
        place(self.entry_start)
        row[0] += 1

        # Продолжительность
        label("Продолжительность")
        self.duration_var = tk.StringVar(value="1 час")
        self.duration_combo = ttk.Combobox(card, textvariable=self.duration_var,
                                           state="readonly", font=FONTS["body"],
                                           values=["30 минут", "1 час", "1.5 часа",
                                                   "2 часа", "3 часа", "4 часа"])
        self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.validate_time_field())
        place(self.duration_combo)
        row[0] += 1

        # Окончание (вычисляется автоматически)
        label("Окончание")
        self.label_end = tk.Label(card, text="11:00", bg=COLORS["card"],
                                  fg=COLORS["text"], font=FONTS["h3"], anchor="w")
        place(self.label_end)
        row[0] += 1

        # Повтор
        label("Повторять")
        self.recur_combo = ttk.Combobox(card, state="readonly", font=FONTS["body"],
                                        values=["Не повторять", "Каждый день (8 раз)",
                                                "Каждую неделю (8 раз)",
                                                "Каждый месяц (8 раз)"])
        self.recur_combo.current(0)
        place(self.recur_combo)
        row[0] += 1

        # Цель
        label("Цель встречи")
        self.entry_purpose = ttk.Entry(card)
        place(self.entry_purpose)
        row[0] += 1

        # Участники
        label("Участники")
        part_wrap = tk.Frame(card, bg=COLORS["card"])
        self.part_listbox = tk.Listbox(part_wrap, selectmode="multiple",
                                       height=3, font=FONTS["body"],
                                       bg=COLORS["entry_bg"], fg=COLORS["text"],
                                       selectbackground=COLORS["accent"],
                                       highlightthickness=1,
                                       highlightbackground=COLORS["border"],
                                       borderwidth=0)
        self.part_listbox.pack(side="left", fill="x", expand=True)
        place(part_wrap)
        row[0] += 1

        # Вложение
        label("Вложение")
        att_wrap = tk.Frame(card, bg=COLORS["card"])
        self.attach_var = tk.StringVar()
        self.attach_label = tk.Label(att_wrap, textvariable=self.attach_var,
                                     bg=COLORS["card"], fg=COLORS["muted"],
                                     font=FONTS["small"], anchor="w")
        self.attach_label.pack(side="left", fill="x", expand=True)
        ttk.Button(att_wrap, text=f"{ICONS['file']} Выбрать", style="Ghost.TButton",
                   command=self.choose_attachment).pack(side="right")
        ttk.Button(att_wrap, text=f"{ICONS['close']}", style="Ghost.TButton",
                   command=lambda: self.attach_var.set("")).pack(side="right", padx=(0, 4))
        place(att_wrap)
        row[0] += 1

        # Кнопки
        btn_row = tk.Frame(card, bg=COLORS["card"])
        btn_row.grid(row=row[0], column=0, columnspan=2, sticky="e",
                     padx=24, pady=(12, 10))
        self.save_btn = ttk.Button(btn_row, text=f"{ICONS['check']} Забронировать",
                                   style="Success.TButton", command=self.create_booking)
        self.save_btn.pack(side="right")
        ttk.Button(btn_row, text="Очистить", style="Ghost.TButton",
                   command=self.clear_booking_form).pack(side="right", padx=(0, 8))
        ttk.Button(btn_row, text=f"{ICONS['search']} Ближайшее свободное",
                   style="Ghost.TButton",
                   command=self.find_nearest_free_slot).pack(side="right", padx=(0, 8))
        row[0] += 1

        # Подсказка
        self.hint_label = tk.Label(card, text="", bg=COLORS["card"],
                                   fg=COLORS["warning"], font=FONTS["small"],
                                   wraplength=500, justify="left")
        self.hint_label.grid(row=row[0], column=0, columnspan=2, sticky="w",
                             padx=24, pady=(0, 16))

        # Обновить список участников
        self.refresh_participants_list()
        # Автоподсчёт окончания
        self.update_end_time()

    def refresh_participants_list(self):
        self.part_listbox.delete(0, tk.END)
        self.users_map = {}
        for uid, uname in db.get_all_users():
            if uname == self.username:
                continue
            self.part_listbox.insert(tk.END, uname)
            self.users_map[uname] = uid

    def update_end_time(self):
        """Вычисляет время окончания из начала + продолжительности."""
        try:
            start = datetime.strptime(self.entry_start.get().strip(), "%H:%M")
        except ValueError:
            self.label_end.config(text="—", fg=COLORS["danger"])
            return None

        duration_map = {
            "30 минут": 30, "1 час": 60, "1.5 часа": 90,
            "2 часа": 120, "3 часа": 180, "4 часа": 240,
        }
        minutes = duration_map.get(self.duration_var.get(), 60)
        end = start + timedelta(minutes=minutes)
        self.label_end.config(text=end.strftime("%H:%M"), fg=COLORS["text"])
        return start.strftime("%H:%M"), end.strftime("%H:%M")

    def validate_time_field(self):
        """Пункт 1: подсветка поля времени — свободно/занято."""
        self.update_end_time()
        times = self.update_end_time()
        if not times or not self.combo_room.get():
            self.entry_start.config(foreground=COLORS["text"])
            return
        start, end = times
        try:
            date = self.get_date_value()
            datetime.strptime(date, "%Y-%m-%d")
        except (ValueError, TypeError):
            self.entry_start.config(foreground=COLORS["text"])
            return

        room_id = int(self.combo_room.get().split("|")[0].strip())
        free = db.is_room_free(room_id, date, start, end)
        self.entry_start.config(
            foreground=COLORS["success"] if free else COLORS["danger"]
        )

    def choose_attachment(self):
        path = filedialog.askopenfilename(title="Выберите файл")
        if path:
            self.attach_var.set(path)

    def build_busy_panel(self, card):
        tk.Label(card, text="Занятые слоты", bg=COLORS["card"],
                 fg=COLORS["text"], font=FONTS["h1"]).pack(anchor="w", padx=24, pady=(20, 4))
        self.busy_subtitle = tk.Label(card, text="Выберите помещение и дату",
                                      bg=COLORS["card"], fg=COLORS["muted"],
                                      font=FONTS["small"], wraplength=440, justify="left")
        self.busy_subtitle.pack(anchor="w", padx=24, pady=(0, 12))

        wrap = tk.Frame(card, bg=COLORS["card"])
        wrap.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self.busy_tree = ttk.Treeview(wrap, columns=("time", "user", "purpose"),
                                      show="headings", height=10)
        self.busy_tree.heading("time",    text="Интервал")
        self.busy_tree.heading("user",    text="Кто занял")
        self.busy_tree.heading("purpose", text="Цель")
        self.busy_tree.column("time",    width=120, anchor="center")
        self.busy_tree.column("user",    width=110, anchor="center")
        self.busy_tree.column("purpose", width=200, anchor="w")

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.busy_tree.yview)
        self.busy_tree.configure(yscrollcommand=vsb.set)
        self.busy_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        legend = tk.Frame(card, bg=COLORS["card"])
        legend.pack(fill="x", padx=24, pady=(0, 16))
        tk.Label(legend, text="🟦 — ваша бронь", bg=COLORS["card"],
                 fg=COLORS["muted"], font=FONTS["small"]).pack(side="left", padx=(0, 12))
        tk.Label(legend, text="⬜ — чужая бронь", bg=COLORS["card"],
                 fg=COLORS["muted"], font=FONTS["small"]).pack(side="left")

    def get_date_value(self):
        """Универсально получает дату из DateEntry или Entry."""
        if HAS_CALENDAR and hasattr(self.entry_date, "get_date"):
            try:
                return self.entry_date.get_date().strftime("%Y-%m-%d")
            except Exception:
                pass
        return self.entry_date.get().strip()

    def set_date_value(self, date_str):
        if HAS_CALENDAR and hasattr(self.entry_date, "set_date"):
            try:
                self.entry_date.set_date(datetime.strptime(date_str, "%Y-%m-%d"))
                return
            except Exception:
                pass
        if hasattr(self.entry_date, "delete"):
            self.entry_date.delete(0, tk.END)
            self.entry_date.insert(0, date_str)

    def update_busy_panel(self):
        self.busy_tree.delete(*self.busy_tree.get_children())
        if not self.combo_room.get():
            self.busy_subtitle.config(text="Выберите помещение и дату")
            return

        room_id = int(self.combo_room.get().split("|")[0].strip())
        date = self.get_date_value()

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            self.busy_subtitle.config(text=f"{ICONS['warn']} Неверный формат даты")
            return

        room_name = self.combo_room.get().split("|")[1].split("(")[0].strip()
        self.busy_subtitle.config(text=f"{room_name}  ·  {date}")

        slots = db.get_busy_slots(room_id, date)
        if not slots:
            self.busy_tree.insert("", "end", values=("—", "свободно весь день", ""))
            return
        for start, end, username, purpose, _id in slots:
            tag = "mine" if username == self.username else "other"
            self.busy_tree.insert("", "end",
                                  values=(f"{start} – {end}", username, purpose or "—"),
                                  tags=(tag,))
        self.busy_tree.tag_configure("mine", background="#dbeafe")
        self.busy_tree.tag_configure("other", background=COLORS["card"])

        # Пункт 1: подсветка
        self.validate_time_field()

    def find_nearest_free_slot(self):
        """Пункт 2: автоподстановка ближайшего свободного слота."""
        if not self.combo_room.get():
            messagebox.showwarning("Внимание", "Выберите помещение")
            return
        room_id = int(self.combo_room.get().split("|")[0].strip())
        date = self.get_date_value()

        duration_map = {"30 минут": 30, "1 час": 60, "1.5 часа": 90,
                        "2 часа": 120, "3 часа": 180, "4 часа": 240}
        minutes = duration_map.get(self.duration_var.get(), 60)

        now = datetime.now()
        from_time = "08:00"
        if date == now.strftime("%Y-%m-%d"):
            from_time = max(now.strftime("%H:%M"), "08:00")

        start, end = db.find_nearest_free(room_id, date, minutes, from_time)
        if start:
            self.entry_start.delete(0, tk.END)
            self.entry_start.insert(0, start)
            self.update_end_time()
            self.validate_time_field()
            messagebox.showinfo("Готово", f"Ближайший свободный слот: {start} – {end}")
        else:
            messagebox.showwarning("Не найдено", "На эту дату свободных слотов нет")

    def clear_booking_form(self):
        self.editing_id = None
        self.set_date_value(datetime.now().strftime("%Y-%m-%d"))
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, "10:00")
        self.entry_purpose.delete(0, tk.END)
        self.attach_var.set("")
        self.recur_combo.current(0)
        self.part_listbox.selection_clear(0, tk.END)
        self.hint_label.config(text="")
        self.save_btn.config(text=f"{ICONS['check']} Забронировать")
        self.update_busy_panel()

    # =========================================================
    #  ВКЛАДКА: ПОИСК СВОБОДНЫХ
    # =========================================================
    def build_free_rooms_tab(self):
        top = tk.Frame(self.tab_free, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 10))

        tk.Label(top, text="Найти свободное помещение на интервал",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=FONTS["h2"]).pack(side="left")

        form = tk.Frame(self.tab_free, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        form.pack(fill="x", pady=(0, 10))

        inner = tk.Frame(form, bg=COLORS["card"])
        inner.pack(padx=16, pady=12, fill="x")

        tk.Label(inner, text="Дата:", bg=COLORS["card"], fg=COLORS["text"],
                 font=FONTS["body"]).pack(side="left")
        self.free_date = ttk.Entry(inner, width=14)
        self.free_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.free_date.pack(side="left", padx=(6, 16))

        tk.Label(inner, text="Начало:", bg=COLORS["card"], fg=COLORS["text"],
                 font=FONTS["body"]).pack(side="left")
        self.free_start = ttk.Entry(inner, width=8)
        self.free_start.insert(0, "10:00")
        self.free_start.pack(side="left", padx=(6, 16))

        tk.Label(inner, text="Окончание:", bg=COLORS["card"], fg=COLORS["text"],
                 font=FONTS["body"]).pack(side="left")
        self.free_end = ttk.Entry(inner, width=8)
        self.free_end.insert(0, "11:00")
        self.free_end.pack(side="left", padx=(6, 16))

        ttk.Button(inner, text=f"{ICONS['search']} Найти", style="Accent.TButton",
                   command=self.search_free_rooms).pack(side="left")
        ttk.Button(inner, text="Забронировать выбранное", style="Success.TButton",
                   command=self.book_free_room).pack(side="right")

        columns = [
            ("id",        "ID",           60,  "center"),
            ("name",      "Название",     260, "w"),
            ("capacity",  "Вместимость",  130, "center"),
            ("equipment", "Оборудование", 420, "w"),
        ]
        self.table_free = FilterableTable(self.tab_free, columns, [], show_filters=False)
        self.table_free.pack(fill="both", expand=True)

    def search_free_rooms(self):
        date = self.free_date.get().strip()
        start = self.free_start.get().strip()
        end = self.free_end.get().strip()
        try:
            datetime.strptime(date, "%Y-%m-%d")
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте формат даты и времени")
            return
        if end <= start:
            messagebox.showerror("Ошибка", "Конец должен быть позже начала")
            return

        rooms = db.find_free_rooms(date, start, end)
        self.table_free.set_data(rooms)
        if not rooms:
            messagebox.showinfo("Готово", "На этот интервал свободных помещений нет")

    def book_free_room(self):
        row = self.table_free.get_selected()
        if not row:
            messagebox.showwarning("Внимание", "Выберите помещение")
            return
        room_id = row[0]
        date = self.free_date.get().strip()
        start = self.free_start.get().strip()
        end = self.free_end.get().strip()

        self.notebook.select(self.tab_new)
        # Найдём нужную строку в combobox
        for i, val in enumerate(self.combo_room["values"]):
            if val.startswith(f"{room_id} |"):
                self.combo_room.current(i)
                break
        self.set_date_value(date)
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, start)
        # рассчитаем продолжительность
        t1 = datetime.strptime(start, "%H:%M")
        t2 = datetime.strptime(end, "%H:%M")
        minutes = int((t2 - t1).total_seconds() // 60)
        dur_map = {30: "30 минут", 60: "1 час", 90: "1.5 часа",
                   120: "2 часа", 180: "3 часа", 240: "4 часа"}
        if minutes in dur_map:
            self.duration_var.set(dur_map[minutes])
        self.update_end_time()
        self.update_busy_panel()

    # =========================================================
    #  ВКЛАДКА: ПОМЕЩЕНИЯ
    # =========================================================
    def build_rooms_tab(self):
        top = tk.Frame(self.tab_rooms, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 10))

        tk.Label(top, text="Список переговорных помещений", bg=COLORS["bg"],
                 fg=COLORS["text"], font=FONTS["h2"]).pack(side="left")

        btns = tk.Frame(top, bg=COLORS["bg"])
        btns.pack(side="right")

        if self.is_admin:
            ttk.Button(btns, text=f"{ICONS['plus']} Добавить", style="Accent.TButton",
                       command=self.add_room_dialog).pack(side="left", padx=4)
            ttk.Button(btns, text=f"{ICONS['trash']} Удалить", style="Danger.TButton",
                       command=self.delete_room).pack(side="left", padx=4)
        ttk.Button(btns, text=f"{ICONS['refresh']} Обновить", style="Ghost.TButton",
                   command=self.refresh_rooms).pack(side="left", padx=4)

        columns = [
            ("id",         "ID",            60,  "center"),
            ("name",       "Название",      240, "w"),
            ("capacity",   "Вместимость",   120, "center"),
            ("equipment",  "Оборудование",  340, "w"),
            ("department", "Отдел",         140, "center"),
        ]
        filters = [
            {"key": "name",       "label": "Название",     "type": "text"},
            {"key": "department", "label": "Отдел",        "type": "select"},
            {"key": "capacity",   "label": "Мин. мест",    "type": "text"},
            {"key": "equipment",  "label": "Оборудование", "type": "text"},
        ]
        self.table_rooms = FilterableTable(self.tab_rooms, columns, filters)
        self.table_rooms.pack(fill="both", expand=True)

    # =========================================================
    #  ДЕЙСТВИЯ
    # =========================================================
    def refresh_all(self):
        self.refresh_bookings()
        self.refresh_all_bookings()
        self.refresh_rooms()
        self.update_busy_panel()

    def refresh_rooms(self):
        self.table_rooms.set_data(db.get_rooms())
        rooms = db.get_rooms()
        self.combo_room["values"] = [f"{r[0]} | {r[1]} ({r[2]} чел.)" for r in rooms]
        if rooms and not self.combo_room.get():
            self.combo_room.current(0)
        r, t, td = db.get_stats()
        self.stat_rooms.value_label.config(text=str(r))
        self.stat_total.value_label.config(text=str(t))
        self.stat_today.value_label.config(text=str(td))

    def refresh_bookings(self):
        self.table_bookings.set_data(db.get_bookings(self.user_id, self.is_admin, self.is_manager))
        r, t, td = db.get_stats()
        self.stat_rooms.value_label.config(text=str(r))
        self.stat_total.value_label.config(text=str(t))
        self.stat_today.value_label.config(text=str(td))

    def refresh_all_bookings(self):
        rows = db.get_all_bookings()
        display = []
        for r in rows:
            # r = (id, room, user, date, start, end, purpose, user_id)
            booking = db.get_booking(r[0])
            recur = booking[7] if booking else "none"
            recur_str = {"none": "", "daily": "Ежедневно",
                         "weekly": "Еженедельно", "monthly": "Ежемесячно"}.get(recur, "")
            attach = ICONS["file"] if (booking and booking[9]) else ""
            display.append((r[0], r[1], r[2], r[3], r[4], r[5], r[6], recur_str, attach))
        self.table_all.set_data(display)

        tree = self.table_all.tree
        for item in tree.get_children():
            values = tree.item(item)["values"]
            if len(values) >= 3 and str(values[2]) == self.username:
                tree.item(item, tags=("mine",))
            else:
                tree.item(item, tags=("other",))

    def create_booking(self):
        """Пункт 4, 16, 17, 18 — создание с продолжительностью, серией, участниками, вложением."""
        if not self.combo_room.get():
            messagebox.showwarning("Внимание", "Выберите помещение")
            return

        room_id = int(self.combo_room.get().split("|")[0].strip())
        date = self.get_date_value()
        purpose = self.entry_purpose.get().strip()

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты.\nИспользуйте ГГГГ-ММ-ДД")
            return

        times = self.update_end_time()
        if not times:
            messagebox.showerror("Ошибка", "Неверный формат времени начала")
            return
        start, end = times

        # Пункт 5: запрет прошлого
        try:
            dt_meeting = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте дату и время")
            return
        if dt_meeting < datetime.now():
            messagebox.showerror("Ошибка", "Нельзя бронировать в прошлом")
            return

        if not purpose:
            messagebox.showwarning("Внимание", "Укажите цель встречи")
            return

        # Участники
        participants = [self.users_map[self.part_listbox.get(i)]
                        for i in self.part_listbox.curselection()]

        # Вложение
        attachment = self.attach_var.get().strip()

        # Режим редактирования
        if self.editing_id:
            ok, msg = db.update_booking(self.editing_id, room_id, date, start, end,
                                        purpose, attachment, participants)
            if ok:
                messagebox.showinfo("Готово", msg)
                self.clear_booking_form()
                self.refresh_all()
                self.notebook.select(self.tab_all)
            else:
                self.hint_label.config(text=f"{ICONS['warn']} {msg}")
                self.update_busy_panel()
                messagebox.showerror("Ошибка", msg)
            return

        # Повтор
        recur_map = {
            "Не повторять": "none",
            "Каждый день (8 раз)": "daily",
            "Каждую неделю (8 раз)": "weekly",
            "Каждый месяц (8 раз)": "monthly",
        }
        recurrence = recur_map.get(self.recur_combo.get(), "none")

        if recurrence == "none":
            ok, msg = db.add_booking(room_id, self.user_id, date, start, end,
                                     purpose, "none", "", attachment, participants)
        else:
            ok, msg = db.create_recurring_bookings(room_id, self.user_id, date,
                                                   start, end, purpose,
                                                   recurrence, participants, attachment)

        if ok:
            messagebox.showinfo("Готово", msg)
            self.clear_booking_form()
            self.refresh_all()
            self.notebook.select(self.tab_all)
        else:
            self.hint_label.config(text=f"{ICONS['warn']} {msg}. Смотрите список справа.")
            self.update_busy_panel()
            messagebox.showerror("Ошибка", msg)

    def edit_booking(self):
        """Пункт 7: редактирование брони."""
        row = self.table_bookings.get_selected()
        if not row:
            messagebox.showwarning("Внимание", "Выберите бронирование")
            return
        booking_id = row[0]
        b = db.get_booking(booking_id)
        if not b:
            return

        # b = (id, room_id, user_id, date, time_start, time_end, purpose, recurrence,
        #      series_id, attachment, room_name, username)
        if b[2] != self.user_id and not self.is_admin:
            messagebox.showerror("Ошибка", "Можно редактировать только свои брони")
            return

        self.editing_id = booking_id
        self.notebook.select(self.tab_new)

        # Заполняем форму
        for i, val in enumerate(self.combo_room["values"]):
            if val.startswith(f"{b[1]} |"):
                self.combo_room.current(i)
                break
        self.set_date_value(b[3])
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, b[4])
        # рассчитаем длительность
        t1 = datetime.strptime(b[4], "%H:%M")
        t2 = datetime.strptime(b[5], "%H:%M")
        minutes = int((t2 - t1).total_seconds() // 60)
        dur_map = {30: "30 минут", 60: "1 час", 90: "1.5 часа",
                   120: "2 часа", 180: "3 часа", 240: "4 часа"}
        self.duration_var.set(dur_map.get(minutes, "1 час"))
        self.entry_purpose.delete(0, tk.END)
        self.entry_purpose.insert(0, b[6] or "")
        self.attach_var.set(b[9] or "")

        # Участники
        self.part_listbox.selection_clear(0, tk.END)
        parts = db.get_participants(booking_id)
        for i in range(self.part_listbox.size()):
            name = self.part_listbox.get(i)
            if any(p[1] == name for p in parts):
                self.part_listbox.selection_set(i)

        self.save_btn.config(text=f"{ICONS['check']} Сохранить изменения")
        self.update_end_time()
        self.update_busy_panel()

    def delete_booking(self):
        row = self.table_bookings.get_selected()
        if not row:
            messagebox.showwarning("Внимание", "Выберите бронирование")
            return
        booking_id = row[0]
        b = db.get_booking(booking_id)

        # Если серия — спросим
        if b and b[8]:
            answer = messagebox.askyesnocancel(
                "Серия встреч",
                "Это повторяющаяся встреча.\n\n"
                "Да — удалить всю серию\n"
                "Нет — удалить только эту\n"
                "Отмена — ничего не делать"
            )
            if answer is None:
                return
            if answer:
                db.delete_series(b[8])
            else:
                db.delete_booking(booking_id)
        else:
            if not messagebox.askyesno("Подтверждение", f"Удалить бронирование #{booking_id}?"):
                return
            db.delete_booking(booking_id)
        self.refresh_all()

    def add_room_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Новое помещение")
        dialog.geometry("460x360")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        card = tk.Frame(dialog, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(card, text="Добавить помещение", bg=COLORS["card"],
                 fg=COLORS["text"], font=FONTS["h2"]).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 12))

        def field(r, label, init=""):
            tk.Label(card, text=label, bg=COLORS["card"], fg=COLORS["text"],
                     font=FONTS["body"]).grid(row=r, column=0, sticky="w",
                                              padx=(20, 10), pady=8)
            e = ttk.Entry(card, width=30)
            e.insert(0, init)
            e.grid(row=r, column=1, sticky="ew", padx=(0, 20), pady=8)
            return e

        card.columnconfigure(1, weight=1)
        e_name = field(1, "Название")
        e_cap  = field(2, "Вместимость (чел.)", "5")
        e_eq   = field(3, "Оборудование")
        e_dept = field(4, "Отдел", "Общий")

        def save():
            name = e_name.get().strip()
            cap = e_cap.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Введите название")
                return
            if not cap.isdigit() or int(cap) <= 0:
                messagebox.showerror("Ошибка", "Вместимость должна быть положительным числом")
                return
            db.add_room(name, int(cap), e_eq.get().strip(), e_dept.get().strip())
            dialog.destroy()
            self.refresh_rooms()

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=20, pady=(10, 16))
        ttk.Button(btns, text="Отмена", style="Ghost.TButton",
                   command=dialog.destroy).pack(side="right", padx=(0, 8))
        ttk.Button(btns, text="Сохранить", style="Accent.TButton",
                   command=save).pack(side="right")

    def delete_room(self):
        row = self.table_rooms.get_selected()
        if not row:
            messagebox.showwarning("Внимание", "Выберите помещение")
            return
        room_id = row[0]
        if messagebox.askyesno("Подтверждение", f"Удалить помещение «{row[1]}»?"):
            try:
                db.delete_room(room_id)
                self.refresh_all()
            except Exception:
                messagebox.showerror("Ошибка", "Нельзя удалить помещение с активными бронированиями")

    def on_close(self):
        """Пункт 6: подтверждение выхода."""
        if messagebox.askyesno("Выход", "Выйти из системы?"):
            self.root.destroy()

    def run(self):
        self.root.mainloop()