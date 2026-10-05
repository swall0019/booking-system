import tkinter as tk
from tkinter import ttk

# === Светлая тема ===
LIGHT = {
    "bg":          "#f4f6f9",
    "card":        "#ffffff",
    "header":      "#1f2a44",
    "header_text": "#ffffff",
    "accent":      "#3b82f6",
    "accent_hover":"#2563eb",
    "success":     "#10b981",
    "danger":      "#ef4444",
    "warning":     "#f59e0b",
    "text":        "#1f2937",
    "muted":       "#6b7280",
    "border":      "#e5e7eb",
    "row_alt":     "#f9fafb",
    "selected":    "#dbeafe",
    "entry_bg":    "#ffffff",
    "heading_bg":  "#eef2f7",
}

# === Тёмная тема ===
DARK = {
    "bg":          "#0f172a",
    "card":        "#1e293b",
    "header":      "#020617",
    "header_text": "#ffffff",
    "accent":      "#3b82f6",
    "accent_hover":"#2563eb",
    "success":     "#10b981",
    "danger":      "#ef4444",
    "warning":     "#fbbf24",
    "text":        "#e2e8f0",
    "muted":       "#94a3b8",
    "border":      "#334155",
    "row_alt":     "#1a2537",
    "selected":    "#1e40af",
    "entry_bg":    "#0f172a",
    "heading_bg":  "#334155",
}

COLORS = dict(LIGHT)   # текущая палитра (меняется при смене темы)

FONTS = {
    "h1":     ("Segoe UI", 16, "bold"),
    "h2":     ("Segoe UI", 13, "bold"),
    "h3":     ("Segoe UI", 11, "bold"),
    "body":   ("Segoe UI", 10),
    "small":  ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
}

# === Иконки (Unicode, работает везде) ===
ICONS = {
    "building":   "🏢",
    "plus":       "＋",
    "trash":      "🗑",
    "refresh":    "⟳",
    "edit":       "✎",
    "calendar":   "📅",
    "user":       "👤",
    "admin":      "👑",
    "manager":    "🛡",
    "check":      "✓",
    "search":     "🔍",
    "clock":      "⏱",
    "file":       "📎",
    "people":     "👥",
    "repeat":     "🔁",
    "sun":        "☀",
    "moon":       "🌙",
    "warn":       "⚠",
    "close":      "✕",
}


def set_theme(name):
    """name: 'light' | 'dark'"""
    global COLORS
    COLORS.clear()
    COLORS.update(DARK if name == "dark" else LIGHT)


def apply_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLORS["bg"])

    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=COLORS["card"],
                    foreground=COLORS["muted"],
                    padding=[20, 10],
                    font=FONTS["body"],
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", "white")])

    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("TFrame", background=COLORS["bg"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["body"])
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])

    style.configure("TEntry",
                    fieldbackground=COLORS["entry_bg"],
                    foreground=COLORS["text"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["border"],
                    darkcolor=COLORS["border"],
                    insertcolor=COLORS["text"],
                    padding=6)

    style.configure("TCombobox",
                    fieldbackground=COLORS["entry_bg"],
                    background=COLORS["entry_bg"],
                    foreground=COLORS["text"],
                    arrowcolor=COLORS["muted"],
                    bordercolor=COLORS["border"],
                    padding=6)

    style.configure("Accent.TButton",
                    background=COLORS["accent"],
                    foreground="white",
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=[14, 8])
    style.map("Accent.TButton",
              background=[("active", COLORS["accent_hover"])])

    style.configure("Success.TButton",
                    background=COLORS["success"],
                    foreground="white",
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=[14, 8])
    style.map("Success.TButton", background=[("active", "#059669")])

    style.configure("Danger.TButton",
                    background=COLORS["danger"],
                    foreground="white",
                    font=FONTS["button"],
                    borderwidth=0,
                    padding=[14, 8])
    style.map("Danger.TButton", background=[("active", "#dc2626")])

    style.configure("Ghost.TButton",
                    background=COLORS["card"],
                    foreground=COLORS["text"],
                    font=FONTS["body"],
                    borderwidth=1,
                    padding=[12, 6])
    style.map("Ghost.TButton",
              background=[("active", COLORS["border"])])

    style.configure("Treeview",
                    background=COLORS["card"],
                    fieldbackground=COLORS["card"],
                    foreground=COLORS["text"],
                    rowheight=32,
                    font=FONTS["body"],
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background=COLORS["heading_bg"],
                    foreground=COLORS["text"],
                    font=FONTS["h3"],
                    relief="flat",
                    padding=[8, 8])
    style.map("Treeview.Heading",
              background=[("active", COLORS["selected"])])
    style.map("Treeview",
              background=[("selected", COLORS["selected"])],
              foreground=[("selected", COLORS["text"])])

    style.configure("Vertical.TScrollbar",
                    background=COLORS["border"],
                    troughcolor=COLORS["bg"],
                    bordercolor=COLORS["bg"],
                    arrowcolor=COLORS["muted"])