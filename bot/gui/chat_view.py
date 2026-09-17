"""Chat view + sidebar (bot controls, system-prompt preview / append)."""

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .. import config
from .theme import COLORS
from .widgets import ScrollableFrame, button, label


class ChatViewMixin:

    def _show_chat_view(self):
        self._clear_body()
        self._build_chat_area(self.body)
        self._build_sidebar(self.body)
        self._refresh_prompt_preview()
        self._refresh_bot_control_label()

    def _build_chat_area(self, parent):
        wrapper = tk.Frame(parent, bg=COLORS["chat_bg"])
        wrapper.pack(side="left", fill="both", expand=True)

        self.chat_area = ScrollableFrame(wrapper, bg=COLORS["chat_bg"])
        self.chat_area.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=COLORS["sidebar_bg"], width=380)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        # --- Bot control ------------------------------------------------
        control = tk.Frame(sidebar, bg=COLORS["sidebar_bg"])
        control.pack(fill="x", padx=16, pady=(16, 8))

        label(control, "🎛️  Bot Control", bold=True, size=11).pack(anchor="w")

        row = tk.Frame(control, bg=COLORS["sidebar_bg"])
        row.pack(fill="x", pady=(8, 0))

        self.btn_start = button(row, "▶  Start", self._on_start_clicked, kind="accent")
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.btn_stop = button(row, "■  Stop", self._on_stop_clicked, kind="danger")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.bot_state_label = tk.Label(
            control, text="Stopped",
            bg=COLORS["sidebar_bg"], fg=COLORS["muted"], font=self.meta_font,
        )
        self.bot_state_label.pack(anchor="w", pady=(6, 0))

        button(control, "⚙  Settings", self._show_settings_view, kind="ghost").pack(
            fill="x", pady=(10, 0)
        )

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=16, pady=12)

        # --- System-prompt preview -------------------------------------
        label(sidebar, "🧠 System Prompt", bold=True).pack(anchor="w", padx=16)

        preview_frame = tk.Frame(sidebar, bg=COLORS["sidebar_bg"])
        preview_frame.pack(fill="x", padx=16, pady=(4, 0))

        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
        self.prompt_preview = tk.Text(
            preview_frame, height=8, wrap="word",
            bg=COLORS["input_bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", font=self.meta_font,
            yscrollcommand=preview_scroll.set, state="disabled",
        )
        preview_scroll.configure(command=self.prompt_preview.yview)
        self.prompt_preview.pack(side="left", fill="both", expand=True)
        preview_scroll.pack(side="right", fill="y")

        button(sidebar, "🔄 Reload from file", self._refresh_prompt_preview, kind="ghost").pack(
            anchor="e", padx=16, pady=(4, 12)
        )

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=16, pady=4)

        label(sidebar, "➕ Add new information", bold=True).pack(anchor="w", padx=16, pady=(10, 4))
        label(
            sidebar,
            "The text below is appended to the end of system_prompt.txt.",
            muted=True, wraplength=340,
        ).pack(anchor="w", padx=16, pady=(0, 6))

        self.prompt_input = tk.Text(
            sidebar, height=4, wrap="word",
            bg=COLORS["input_bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", font=self.msg_font,
        )
        self.prompt_input.pack(fill="x", padx=16)

        button(sidebar, "Add to System Prompt", self._on_add_data, kind="accent").pack(
            fill="x", padx=16, pady=10
        )

        self.feedback_label = tk.Label(
            sidebar, text="", bg=COLORS["sidebar_bg"], fg=COLORS["ok"], font=self.meta_font,
        )
        self.feedback_label.pack(anchor="w", padx=16)

    # ---------------------------------------------------------------
    # Bot control
    # ---------------------------------------------------------------

    def _refresh_bot_control_label(self):
        from .. import state as bot_state
        if bot_state.is_running() and bot_state.active:
            self.bot_state_label.configure(text="Running", fg=COLORS["ok"])
        elif bot_state.is_running():
            self.bot_state_label.configure(text="Paused", fg=COLORS["warn"])
        else:
            self.bot_state_label.configure(text="Offline", fg=COLORS["muted"])

    def _on_start_clicked(self):
        from .. import main as bot_main
        phone = config.TELEGRAM_PHONE if config.PLATFORM == "telegram" else config.RUBIKA_PHONE
        bot_main.start(phone_number=phone)

    def _on_stop_clicked(self):
        from .. import main as bot_main
        bot_main.pause()

    # ---------------------------------------------------------------
    # System prompt actions
    # ---------------------------------------------------------------

    def _refresh_prompt_preview(self):
        config.reload_system_prompt()
        self.prompt_preview.configure(state="normal")
        self.prompt_preview.delete("1.0", "end")
        self.prompt_preview.insert("1.0", config.SYSTEM_PROMPT)
        self.prompt_preview.configure(state="disabled")

    def _on_add_data(self):
        text = self.prompt_input.get("1.0", "end").strip()
        if not text:
            self._flash_feedback("⚠️ Text cannot be empty.", error=True)
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        config.append_to_system_prompt(text, label=f"Note added from the panel ({timestamp})")

        self.prompt_input.delete("1.0", "end")
        self._refresh_prompt_preview()
        self._flash_feedback("✅ Added to the System Prompt.")

    def _flash_feedback(self, message: str, error: bool = False):
        self.feedback_label.configure(text=message, fg=COLORS["danger"] if error else COLORS["ok"])
        self.after(2500, lambda: self.feedback_label.configure(text=""))

    # ---------------------------------------------------------------
    # Message bubbles
    # ---------------------------------------------------------------

    def _sender_label(self, event: dict) -> str:
        """
        Display name of the OTHER party in a message. Wrapped in Unicode
        LTR marks so mixed RTL (e.g. Persian, Arabic) and Latin text does
        not render backwards.
        """

        name = event.get("display_name")
        if name:
            return f"‎{name}‎"

        uid = event.get("user_id", "")
        short = uid[-6:] if len(uid) > 6 else uid
        return f"‎{short}‎"

    def _me_label(self) -> str:
        """Own display name for the bot bubble."""

        if self._me_username:
            return f"‎@{self._me_username}‎"
        if self._me_phone:
            return f"‎{self._me_phone}‎"
        return "Me"

    def _add_message(self, sender_label, text, *, align, bubble_bg, text_fg):
        if not hasattr(self, "chat_area") or not self.chat_area.winfo_exists():
            return
        row = tk.Frame(self.chat_area.inner, bg=COLORS["chat_bg"])
        row.pack(fill="x", padx=12, pady=5)

        bubble = tk.Frame(row, bg=bubble_bg)
        bubble.pack(anchor="e" if align == "right" else "w")

        tk.Label(
            bubble,
            text=f"{sender_label}   ·   {datetime.now().strftime('%H:%M:%S')}",
            bg=bubble_bg,
            fg="#dbeafe" if align == "right" else COLORS["muted"],
            font=self.meta_font, anchor="w", justify="left",
        ).pack(fill="x", padx=12, pady=(8, 0))

        tk.Label(
            bubble, text=text, bg=bubble_bg, fg=text_fg,
            font=self.msg_font, wraplength=440, justify="left", anchor="w",
        ).pack(padx=12, pady=(2, 8))

        self.chat_area.scroll_to_bottom()
