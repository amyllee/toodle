"""
Pop-up To-Do Notes (Reminders-style)
A small, always-on-top checklist widget for your desktop, styled after
Apple's Reminders app.

Run by double-clicking this file (Windows uses pythonw.exe for .pyw files,
so no console window appears).

Data is saved to todo_notes_data.json in the same folder, organized by day,
so you can flip back to any previous day's list with the arrows in the header.
"""

import tkinter as tk
from tkinter import font as tkfont
import json
import os
import datetime

# ---------------------------------------------------------------------------
# Config / styling
# ---------------------------------------------------------------------------

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "todo_notes_data.json")

BG = "#FFFFFF"
HEADER_BG = "#FFFFFF"
BORDER = "#EAEAEA"
TEXT = "#1C1C1E"
TEXT_DONE = "#B0B0B5"
SUBTEXT = "#8E8E93"
ACCENT = "#007AFF"       # Reminders blue
ACCENT_HOVER = "#0064D6"
OVERDUE = "#FF3B30"       # Reminders red
HANDLE_COLOR = "#D8D8DC"
HANDLE_HOVER = "#A8A8AE"

FONT_FAMILY = "Segoe UI"


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.data = {}                 # {"YYYY-MM-DD": [ {text, done, due}, ... ]}
        self.current_date = datetime.date.today()
        self.items = []                 # live reference to today's/selected day's list
        self.always_on_top = True
        self._row_refs = []
        self._drag_index = None

        self._setup_window()
        self._load_data()
        self._refresh_items_ref()
        self._build_ui()
        self._render_items()

    # -----------------------------------------------------------------
    # Window setup
    # -----------------------------------------------------------------
    def _setup_window(self):
        self.root.title("To-Do")
        self.root.geometry("320x480+80+80")
        self.root.minsize(280, 320)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", self.always_on_top)

    # -----------------------------------------------------------------
    # Data persistence
    # -----------------------------------------------------------------
    def _date_key(self, d):
        return d.strftime("%Y-%m-%d")

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    # migrate from the old single-list format
                    self.data = {self._date_key(self.current_date): loaded}
                elif isinstance(loaded, dict):
                    self.data = loaded
            except Exception:
                self.data = {}

    def _save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def _refresh_items_ref(self):
        key = self._date_key(self.current_date)
        if key not in self.data:
            self.data[key] = []
        self.items = self.data[key]

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        title_font = tkfont.Font(family=FONT_FAMILY, size=17, weight="bold")
        nav_font = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")
        today_font = tkfont.Font(family=FONT_FAMILY, size=9)

        # ---- Header ----
        header = tk.Frame(self.root, bg=HEADER_BG)
        header.pack(fill="x", side="top")
        pad = tk.Frame(header, bg=HEADER_BG)
        pad.pack(fill="x", padx=16, pady=(14, 8))

        top_row = tk.Frame(pad, bg=HEADER_BG)
        top_row.pack(fill="x")
        self.title_label = tk.Label(top_row, text="To Do", font=title_font, bg=HEADER_BG, fg=TEXT, anchor="w")
        self.title_label.pack(side="left")
        self.pin_btn = tk.Label(top_row, text="📌", font=(FONT_FAMILY, 12), bg=HEADER_BG,
                                 fg=ACCENT, cursor="hand2")
        self.pin_btn.pack(side="right")
        self.pin_btn.bind("<Button-1>", self._toggle_pin)

        nav_row = tk.Frame(pad, bg=HEADER_BG)
        nav_row.pack(fill="x", pady=(6, 0))

        prev_btn = tk.Label(nav_row, text="‹", font=nav_font, bg=HEADER_BG, fg=ACCENT, cursor="hand2")
        prev_btn.pack(side="left", padx=(0, 10))
        prev_btn.bind("<Button-1>", lambda e: self._change_day(-1))

        self.date_label = tk.Label(nav_row, text="", font=(FONT_FAMILY, 10, "bold"), bg=HEADER_BG, fg=TEXT)
        self.date_label.pack(side="left", expand=True)

        next_btn = tk.Label(nav_row, text="›", font=nav_font, bg=HEADER_BG, fg=ACCENT, cursor="hand2")
        next_btn.pack(side="right", padx=(10, 0))
        next_btn.bind("<Button-1>", lambda e: self._change_day(1))

        self.today_link = tk.Label(pad, text="Jump to Today", font=today_font, bg=HEADER_BG,
                                    fg=ACCENT, cursor="hand2")
        self.today_link.bind("<Button-1>", lambda e: self._jump_today())

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ---- Scrollable list area ----
        list_container = tk.Frame(self.root, bg=BG)
        list_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_container, bg=BG, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(self.canvas, bg=BG)
        self.list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.list_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ---- Add-item row ----
        add_row = tk.Frame(self.root, bg=BG)
        add_row.pack(fill="x", side="bottom", padx=14, pady=12)

        entry_font = tkfont.Font(family=FONT_FAMILY, size=10)
        self.entry = tk.Entry(add_row, font=entry_font, bg="#F5F5F7", fg=TEXT, relief="flat",
                               highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                               insertbackground=TEXT)
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self.entry.bind("<Return>", self._on_add)
        self.entry.focus_set()

        self.add_btn = tk.Label(add_row, text="＋", font=(FONT_FAMILY, 14, "bold"), bg=ACCENT,
                                 fg="white", width=3, cursor="hand2")
        self.add_btn.pack(side="right", fill="y")
        self.add_btn.bind("<Button-1>", self._on_add)
        self.add_btn.bind("<Enter>", lambda e: self.add_btn.configure(bg=ACCENT_HOVER))
        self.add_btn.bind("<Leave>", lambda e: self.add_btn.configure(bg=ACCENT))

        self._update_date_header()

    def _update_date_header(self):
        today = datetime.date.today()
        if self.current_date == today:
            text = "Today · " + self.current_date.strftime("%a, %b %d")
            self.today_link.pack_forget()
        else:
            text = self.current_date.strftime("%A, %b %d, %Y")
            self.today_link.pack(anchor="w", pady=(4, 0))
        self.date_label.configure(text=text)

    # -----------------------------------------------------------------
    # Day navigation
    # -----------------------------------------------------------------
    def _change_day(self, delta):
        self.current_date += datetime.timedelta(days=delta)
        self._refresh_items_ref()
        self._update_date_header()
        self._render_items()

    def _jump_today(self):
        self.current_date = datetime.date.today()
        self._refresh_items_ref()
        self._update_date_header()
        self._render_items()

    # -----------------------------------------------------------------
    # Item rendering
    # -----------------------------------------------------------------
    def _render_items(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self._row_refs = []

        if not self.items:
            empty = tk.Label(self.list_frame, text="Nothing here yet — add a task below.",
                              font=(FONT_FAMILY, 9), fg=SUBTEXT, bg=BG, wraplength=250, justify="left")
            empty.pack(padx=16, pady=20, anchor="w")
            return

        for idx, item in enumerate(self.items):
            self._build_row(idx, item)

    def _build_row(self, idx, item):
        done = item.get("done", False)
        due = item.get("due")

        row = tk.Frame(self.list_frame, bg=BG)
        row.pack(fill="x")
        self._row_refs.append(row)

        inner = tk.Frame(row, bg=BG)
        inner.pack(fill="x", padx=10, pady=8)

        # drag handle
        handle = tk.Label(inner, text="⋮⋮", font=(FONT_FAMILY, 10), bg=BG, fg=HANDLE_COLOR, cursor="fleur")
        handle.pack(side="left", padx=(0, 6))
        handle.bind("<ButtonPress-1>", lambda e, i=idx: self._drag_start(e, i))
        handle.bind("<ButtonRelease-1>", self._drag_stop)
        handle.bind("<Enter>", lambda e: handle.configure(fg=HANDLE_HOVER))
        handle.bind("<Leave>", lambda e: handle.configure(fg=HANDLE_COLOR))

        # checkbox
        cb = tk.Canvas(inner, width=20, height=20, bg=BG, highlightthickness=0, cursor="hand2")
        cb.pack(side="left", padx=(0, 10))
        self._draw_checkbox(cb, done)
        cb.bind("<Button-1>", lambda e, i=idx: self._toggle_item(i))

        # text + due date stacked
        text_frame = tk.Frame(inner, bg=BG)
        text_frame.pack(side="left", fill="x", expand=True)

        item_font = tkfont.Font(family=FONT_FAMILY, size=10, overstrike=1 if done else 0)
        lbl = tk.Label(text_frame, text=item["text"], font=item_font, bg=BG,
                        fg=TEXT_DONE if done else TEXT, anchor="w", justify="left", wraplength=175)
        lbl.pack(fill="x", anchor="w")
        lbl.bind("<Button-1>", lambda e, i=idx: self._toggle_item(i))

        if due:
            due_date = datetime.date.fromisoformat(due)
            overdue = (due_date < datetime.date.today()) and not done
            due_text = due_date.strftime("%b %d")
            if due_date.year != datetime.date.today().year:
                due_text = due_date.strftime("%b %d, %Y")
            due_lbl = tk.Label(text_frame, text=("⚠ " if overdue else "") + due_text,
                                font=(FONT_FAMILY, 8), bg=BG,
                                fg=OVERDUE if overdue else SUBTEXT, anchor="w")
            due_lbl.pack(fill="x", anchor="w")

        # right-side controls
        controls = tk.Frame(inner, bg=BG)
        controls.pack(side="right")

        cal_btn = tk.Label(controls, text="📅", font=(FONT_FAMILY, 10), bg=BG, fg=SUBTEXT, cursor="hand2")
        cal_btn.pack(side="left", padx=(4, 4))
        cal_btn.bind("<Button-1>", lambda e, i=idx: self._open_due_picker(i, e))

        del_btn = tk.Label(controls, text="✕", font=(FONT_FAMILY, 9), bg=BG, fg="#D8D6D0", cursor="hand2")
        del_btn.pack(side="left")
        del_btn.bind("<Button-1>", lambda e, i=idx: self._delete_item(i))
        del_btn.bind("<Enter>", lambda e: del_btn.configure(fg=OVERDUE))
        del_btn.bind("<Leave>", lambda e: del_btn.configure(fg="#D8D6D0"))

        tk.Frame(self.list_frame, bg=BORDER, height=1).pack(fill="x", padx=10)

    def _draw_checkbox(self, canvas, done):
        canvas.delete("all")
        if done:
            canvas.create_oval(2, 2, 18, 18, fill=ACCENT, outline=ACCENT)
            canvas.create_line(6, 10, 9, 13, 14, 6, fill="white", width=2, capstyle="round", joinstyle="round")
        else:
            canvas.create_oval(2, 2, 18, 18, fill="", outline="#C7C7CC", width=1.5)

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------
    def _on_add(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.items.append({"text": text, "done": False, "due": None})
        self.entry.delete(0, "end")
        self._save_data()
        self._render_items()
        self.canvas.yview_moveto(1.0)

    def _toggle_item(self, idx):
        self.items[idx]["done"] = not self.items[idx]["done"]
        self._save_data()
        self._render_items()

    def _delete_item(self, idx):
        self.items.pop(idx)
        self._save_data()
        self._render_items()

    def _toggle_pin(self, event=None):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        self.pin_btn.configure(fg=ACCENT if self.always_on_top else SUBTEXT)

    # -----------------------------------------------------------------
    # Drag to reorder
    # -----------------------------------------------------------------
    def _drag_start(self, event, idx):
        self._drag_index = idx

    def _drag_stop(self, event):
        if self._drag_index is None or not self._row_refs:
            self._drag_index = None
            return
        ptr_y = event.widget.winfo_pointery() - self.list_frame.winfo_rooty()
        target = len(self._row_refs) - 1
        for i, row in enumerate(self._row_refs):
            top = row.winfo_y()
            bottom = top + row.winfo_height()
            if ptr_y < bottom:
                target = i
                break
        if target != self._drag_index:
            moved = self.items.pop(self._drag_index)
            self.items.insert(target, moved)
            self._save_data()
            self._render_items()
        self._drag_index = None

    # -----------------------------------------------------------------
    # Due date picker
    # -----------------------------------------------------------------
    def _parse_due(self, text):
        text = text.strip()
        today = datetime.date.today()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d"):
            try:
                parsed = datetime.datetime.strptime(text, fmt).date()
                if fmt == "%m/%d":
                    parsed = parsed.replace(year=today.year)
                    if parsed < today:
                        parsed = parsed.replace(year=today.year + 1)
                return parsed
            except ValueError:
                continue
        return None

    def _open_due_picker(self, idx, event):
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=BORDER)
        x = event.x_root
        y = event.y_root
        top.geometry(f"+{x}+{y}")

        frame = tk.Frame(top, bg="white")
        frame.pack(padx=1, pady=1)

        tk.Label(frame, text="Due date (e.g. 9/5)", font=(FONT_FAMILY, 8), bg="white",
                 fg=SUBTEXT).pack(padx=10, pady=(8, 2), anchor="w")

        entry = tk.Entry(frame, font=(FONT_FAMILY, 10), width=14, relief="flat",
                          highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(padx=10, pady=(0, 8), ipady=3)

        existing = self.items[idx].get("due")
        if existing:
            d = datetime.date.fromisoformat(existing)
            entry.insert(0, f"{d.month}/{d.day}")
        entry.focus_set()

        btn_row = tk.Frame(frame, bg="white")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        def save(e=None):
            text = entry.get().strip()
            if text:
                parsed = self._parse_due(text)
                if parsed:
                    self.items[idx]["due"] = parsed.isoformat()
            top.destroy()
            self._save_data()
            self._render_items()

        def clear():
            self.items[idx]["due"] = None
            top.destroy()
            self._save_data()
            self._render_items()

        save_btn = tk.Label(btn_row, text="Save", fg=ACCENT, bg="white", cursor="hand2",
                             font=(FONT_FAMILY, 9, "bold"))
        save_btn.pack(side="left")
        save_btn.bind("<Button-1>", save)

        clear_btn = tk.Label(btn_row, text="Clear", fg=OVERDUE, bg="white", cursor="hand2",
                              font=(FONT_FAMILY, 9))
        clear_btn.pack(side="right")
        clear_btn.bind("<Button-1>", lambda e: clear())

        entry.bind("<Return>", save)
        entry.bind("<Escape>", lambda e: top.destroy())


def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
