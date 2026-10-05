import tkinter as tk
from tkinter import ttk, messagebox
import database as db
from style import COLORS, FONTS, ICONS, apply_theme


class AuthWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("Вход — Система бронирования")
        self.root.geometry("460x440")
        self.root.resizable(False, False)

        apply_theme(self.root)
        self.build_ui()

    def build_ui(self):
        header = tk.Frame(self.root, bg=COLORS["header"], height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text=ICONS["building"], bg=COLORS["header"], fg="white",
                 font=("Segoe UI Emoji", 26)).pack(pady=(14, 0))
        tk.Label(header, text="Система бронирования переговорных",
                 bg=COLORS["header"], fg="white",
                 font=("Segoe UI", 12, "bold")).pack()

        card = tk.Frame(self.root, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="x", padx=24, pady=20)

        tk.Label(card, text="Вход в систему", bg=COLORS["card"],
                 fg=COLORS["text"], font=FONTS["h2"]).pack(anchor="w", padx=24, pady=(20, 12))

        def field(label, show=None):
            tk.Label(card, text=label, bg=COLORS["card"], fg=COLORS["muted"],
                     font=FONTS["small"]).pack(anchor="w", padx=24)
            e = ttk.Entry(card, font=FONTS["body"], show=show)
            e.pack(fill="x", padx=24, pady=(2, 10), ipady=4)
            return e

        self.entry_login = field("Логин")
        self.entry_password = field("Пароль", show="*")

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x", padx=24, pady=(4, 20))

        ttk.Button(btns, text="Войти", style="Accent.TButton",
                   command=self.login).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(btns, text="Регистрация", style="Ghost.TButton",
                   command=self.register).pack(side="left", fill="x", expand=True, padx=(6, 0))

        hint = tk.Label(self.root,
                        text="Демо:  admin/admin  ·  manager/manager  ·  user/user",
                        bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"])
        hint.pack(pady=(0, 12))

        self.root.bind("<Return>", lambda e: self.login())
        self.entry_login.focus_set()

    def login(self):
        login = self.entry_login.get().strip()
        password = self.entry_password.get().strip()
        if not login or not password:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return
        user = db.check_user(login, password)
        if user:
            self.root.destroy()
            self.on_success(user)
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def register(self):
        login = self.entry_login.get().strip()
        password = self.entry_password.get().strip()
        if not login or not password:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return
        if len(password) < 3:
            messagebox.showwarning("Внимание", "Пароль должен быть не короче 3 символов")
            return
        ok, msg = db.register_user(login, password)
        if ok:
            messagebox.showinfo("Готово", msg)
        else:
            messagebox.showerror("Ошибка", msg)