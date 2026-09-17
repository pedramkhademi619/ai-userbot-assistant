"""Small Tk widget helpers used across every view."""

import tkinter as tk
from tkinter import ttk

from .theme import COLORS


class ScrollableFrame(tk.Frame):
    """A vertically-scrolling container (canvas + inner frame + scrollbar)."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)

        self.inner.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._window_id, width=e.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def scroll_to_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)


def entry(parent, textvariable, *, show=None):
    return tk.Entry(
        parent,
        textvariable=textvariable,
        bg=COLORS["field_bg"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        highlightthickness=1,
        highlightbackground="#1f2937",
        highlightcolor=COLORS["accent"],
        font=("Segoe UI", 10),
        show=show if show else "",
    )


def label(parent, text, *, muted=False, bold=False, size=10, wraplength=0):
    return tk.Label(
        parent,
        text=text,
        bg=parent["bg"],
        fg=COLORS["muted"] if muted else COLORS["text"],
        font=("Segoe UI", size, "bold" if bold else "normal"),
        wraplength=wraplength,
        justify="left",
        anchor="w",
    )


def button(parent, text, command, *, kind="accent"):
    bg, hover = {
        "accent": (COLORS["accent"], COLORS["accent_hover"]),
        "danger": (COLORS["danger"], COLORS["danger_hover"]),
        "ghost": (COLORS["sidebar_bg"], COLORS["input_bg"]),
    }[kind]

    fg = COLORS["muted"] if kind == "ghost" else "white"
    active_fg = COLORS["text"] if kind == "ghost" else "white"

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=active_fg,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
        padx=14,
        pady=8,
    )
