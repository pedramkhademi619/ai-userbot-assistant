"""
The single-window ChatDashboard.

Composed from several mixin classes so the wizard, chat view, settings
view, dialogs, and event pump each live in their own module.
"""

import tkinter as tk
from tkinter import ttk

from .. import config, events
from .chat_view import ChatViewMixin
from .dialogs import DialogMixin
from .event_pump import EventPumpMixin
from .settings_view import SettingsViewMixin
from .theme import COLORS, HEADER_FONT, LABEL_FONT, META_FONT, MSG_FONT, platform_name_en
from .wizard import WizardMixin


class ChatDashboard(
    WizardMixin,
    ChatViewMixin,
    SettingsViewMixin,
    DialogMixin,
    EventPumpMixin,
    tk.Tk,
):

    def __init__(self):
        super().__init__()

        self.title("AI Bot")
        self.geometry("1100x740")
        self.minsize(920, 600)
        self.configure(bg=COLORS["bg"])

        self.meta_font = META_FONT
        self.msg_font = MSG_FONT
        self.header_font = HEADER_FONT
        self.label_font = LABEL_FONT

        self._event_queue = events.subscribe()
        self._prompt_dialog = None
        self._password_dialog = None
        self._error_dialog = None
        self._wizard_data: dict = {}
        self._auth_thread = None

        # Account-owner identity, populated on "status=connected". Used to
        # label outgoing bot bubbles as *me*, not the person we're replying to.
        self._me_username: str | None = None
        self._me_phone: str | None = None

        self._build_style()
        self._build_header()

        self.body = tk.Frame(self, bg=COLORS["bg"])
        self.body.pack(fill="both", expand=True)

        self._maybe_migrate_legacy_platform()
        self._refresh_header_title()

        if config.is_logged_in():
            self._show_chat_view()
        elif config.PLATFORM in config.VALID_PLATFORMS:
            self._route_wizard_first_step()
        else:
            self._show_platform_select()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._poll_events)

    # ------------------------------------------------------------------
    # Legacy migration
    # ------------------------------------------------------------------

    def _maybe_migrate_legacy_platform(self):
        """
        Older installs stored a Rubika session + API key but no PLATFORM.
        If we detect that shape, adopt "rubika" silently so the user
        isn't re-shown the platform picker on every launch.
        """

        if config.PLATFORM:
            return
        if not config.RUBIKA_SESSION:
            return
        if not config.session_file_path(config.RUBIKA_SESSION).exists():
            return
        if not config.API_KEY:
            return

        config.save_settings({"PLATFORM": "rubika"})
        config.reload_config()

    # ------------------------------------------------------------------
    # Style + header
    # ------------------------------------------------------------------

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Vertical.TScrollbar", background=COLORS["sidebar_bg"],
                        troughcolor=COLORS["bg"])
        style.configure("TSeparator", background=COLORS["muted"])

    def _build_header(self):
        header = tk.Frame(self, bg=COLORS["header_bg"], height=56)
        header.pack(side="top", fill="x")

        self.header_title = tk.Label(
            header, text="🤖  AI Bot",
            bg=COLORS["header_bg"], fg=COLORS["text"], font=self.header_font,
        )
        self.header_title.pack(side="left", padx=18, pady=12)

        status_frame = tk.Frame(header, bg=COLORS["header_bg"])
        status_frame.pack(side="right", padx=18)

        self.status_canvas = tk.Canvas(
            status_frame, width=12, height=12,
            bg=COLORS["header_bg"], highlightthickness=0,
        )
        self.status_dot = self.status_canvas.create_oval(1, 1, 11, 11,
                                                        fill=COLORS["muted"], outline="")
        self.status_canvas.pack(side="left", padx=(0, 8))

        self.status_label = tk.Label(
            status_frame, text="Ready",
            bg=COLORS["header_bg"], fg=COLORS["muted"], font=self.meta_font,
        )
        self.status_label.pack(side="left")

    def _refresh_header_title(self) -> None:
        """Reflect the currently selected platform in the app-bar title."""

        platform_label = platform_name_en(config.PLATFORM)

        text = f"🤖  {platform_label} AI Bot".strip() if platform_label else "🤖  AI Bot"
        win_title = f"{platform_label} AI Bot".strip() if platform_label else "AI Bot"

        if hasattr(self, "header_title") and self.header_title.winfo_exists():
            self.header_title.configure(text=text)
            self.title(win_title)

    # ------------------------------------------------------------------
    # Body swap helper
    # ------------------------------------------------------------------

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _on_close(self):
        try:
            from .. import main as bot_main
            bot_main.stop()
        except Exception:
            pass
        events.unsubscribe(self._event_queue)
        self.destroy()


def launch_gui():
    ChatDashboard().mainloop()
