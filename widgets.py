import tkinter as tk
from tkinter import ttk
from style import COLORS, FONTS


class FilterableTable(ttk.Frame):
    def __init__(self, parent, columns, filters_config, show_filters=True):
        super().__init__(parent)
        self.columns = columns
        self.filters_config = filters_config
        self.all_rows = []
        self.filter_widgets = {}
        self.sort_column = None
        self.sort_reverse = False

        self.configure(style="TFrame")
        self.build_ui(show_filters)

    def build_ui(self, show_filters):
        if show_filters and self.filters_config:
            filter_card = tk.Frame(self, bg=COLORS["card"], highlightthickness=1,
                                   highlightbackground=COLORS["border"])
            filter_card.pack(fill="x", pady=(0, 8))

            inner = tk.Frame(filter_card, bg=COLORS["card"])
            inner.pack(fill="x", padx=12, pady=10)

            tk.Label(inner, text="Фильтры:", bg=COLORS["card"],
                     fg=COLORS["muted"], font=FONTS["h3"]).pack(side="left", padx=(0, 12))

            for cfg in self.filters_config:
                self.build_filter_widget(inner, cfg)

            ttk.Button(inner, text="Сбросить", style="Ghost.TButton",
                       command=self.reset_filters).pack(side="right", padx=(6, 0))

        table_wrap = tk.Frame(self, bg=COLORS["card"], highlightthickness=1,
                              highlightbackground=COLORS["border"])
        table_wrap.pack(fill="both", expand=True)

        cols = [c[0] for c in self.columns]
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")

        for key, header, width, anchor in self.columns:
            self.tree.heading(key, text=header, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=False)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=(1, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(1, 0))
        hsb.grid(row=1, column=0, sticky="ew", padx=(1, 0))
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        self.tree.tag_configure("odd", background=COLORS["row_alt"])
        self.tree.tag_configure("even", background=COLORS["card"])

    def build_filter_widget(self, parent, cfg):
        key = cfg["key"]
        ftype = cfg.get("type", "text")

        box = tk.Frame(parent, bg=COLORS["card"])
        box.pack(side="left", padx=4)

        tk.Label(box, text=cfg["label"] + ":", bg=COLORS["card"],
                 fg=COLORS["text"], font=FONTS["small"]).pack(anchor="w")

        if ftype == "text":
            var = tk.StringVar()
            var.trace_add("write", lambda *_: self.apply_filters())
            entry = ttk.Entry(box, textvariable=var, width=16)
            entry.pack()
            self.filter_widgets[key] = ("text", var)

        elif ftype == "select":
            var = tk.StringVar(value="Все")
            combo = ttk.Combobox(box, textvariable=var, state="readonly",
                                 width=18, values=["Все"])
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
            self.filter_widgets[key] = ("select", var)

    def set_data(self, rows):
        self.all_rows = rows
        self.refresh_select_options()
        self.apply_filters()

    def refresh_select_options(self):
        for cfg in self.filters_config:
            if cfg.get("type") != "select":
                continue
            key = cfg["key"]
            idx = self.column_index(key)
            if idx is None:
                continue
            values = sorted({str(r[idx]) for r in self.all_rows if r[idx] not in (None, "")})
            _, var = self.filter_widgets[key]
            combo = None
            for child in self.winfo_children():
                for sub in child.winfo_children():
                    for w in sub.winfo_children():
                        if isinstance(w, ttk.Combobox):
                            if w.cget("textvariable") == str(var):
                                combo = w
            if combo is not None:
                combo["values"] = ["Все"] + values
                if var.get() not in (["Все"] + values):
                    var.set("Все")

    def column_index(self, key):
        for i, (k, *_rest) in enumerate(self.columns):
            if k == key:
                return i
        return None

    def apply_filters(self):
        rows = list(self.all_rows)
        for cfg in self.filters_config:
            key = cfg["key"]
            idx = self.column_index(key)
            if idx is None:
                continue
            ftype, var = self.filter_widgets[key]
            value = var.get().strip()
            if ftype == "text":
                if value:
                    low = value.lower()
                    rows = [r for r in rows if low in str(r[idx]).lower()]
            elif ftype == "select":
                if value and value != "Все":
                    rows = [r for r in rows if str(r[idx]) == value]

        if self.sort_column is not None:
            idx = self.column_index(self.sort_column)
            if idx is not None:
                def sort_key(r):
                    v = r[idx]
                    try:
                        return (0, float(v))
                    except (ValueError, TypeError):
                        return (1, str(v).lower())
                rows.sort(key=sort_key, reverse=self.sort_reverse)

        self.render(rows)

    def render(self, rows):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self.tree.insert("", "end", values=r, tags=(tag,))

    def sort_by(self, key):
        if self.sort_column == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = key
            self.sort_reverse = False

        for k, header, *_ in self.columns:
            arrow = ""
            if k == self.sort_column:
                arrow = " ▼" if self.sort_reverse else " ▲"
            self.tree.heading(k, text=header + arrow)
        self.apply_filters()

    def reset_filters(self):
        for key, (ftype, var) in self.filter_widgets.items():
            var.set("Все" if ftype == "select" else "")
        self.sort_column = None
        self.sort_reverse = False
        for k, header, *_ in self.columns:
            self.tree.heading(k, text=header)
        self.apply_filters()

    def get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0])["values"]