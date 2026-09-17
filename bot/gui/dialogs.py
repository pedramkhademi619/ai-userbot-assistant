"""Modal dialogs: error/info box, prompt fallback, 2FA password."""

import tkinter as tk

from .. import auth_bridge, config
from .theme import COLORS, platform_name_en
from .widgets import button, entry, label


class DialogMixin:

    # ---------------------------------------------------------------
    # Reusable error / info dialog
    # ---------------------------------------------------------------

    def _show_error_dialog(
        self,
        title: str,
        message: str,
        *,
        action_label: str | None = None,
        action_command=None,
    ):
        existing = getattr(self, "_error_dialog", None)
        if existing is not None and existing.winfo_exists():
            try:
                existing.destroy()
            except tk.TclError:
                pass

        dialog = tk.Toplevel(self)
        self._error_dialog = dialog
        dialog.title(title)
        dialog.configure(bg=COLORS["sidebar_bg"])
        dialog.transient(self)
        dialog.geometry("480x220")
        dialog.resizable(False, False)

        label(dialog, title, bold=True, size=12).pack(anchor="w", padx=20, pady=(18, 6))
        label(dialog, message, muted=True, wraplength=430).pack(anchor="w", padx=20, pady=(0, 12))

        row = tk.Frame(dialog, bg=COLORS["sidebar_bg"])
        row.pack(fill="x", padx=20, pady=(10, 18))

        def close():
            try:
                dialog.destroy()
            except tk.TclError:
                pass
            self._error_dialog = None

        button(row, "OK", close, kind="ghost").pack(side="right")

        if action_label and action_command:
            def do_action():
                close()
                action_command()

            button(row, action_label, do_action, kind="accent").pack(side="right", padx=(0, 8))

    # ---------------------------------------------------------------
    # 2FA password (Telethon cloud password)
    # ---------------------------------------------------------------

    def _show_password_dialog(self):
        existing = getattr(self, "_password_dialog", None)
        if existing is not None and existing.winfo_exists():
            try:
                existing.destroy()
            except tk.TclError:
                pass

        dialog = tk.Toplevel(self)
        self._password_dialog = dialog
        dialog.title("Telegram Two-Factor Password")
        dialog.configure(bg=COLORS["sidebar_bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("480x240")
        dialog.resizable(False, False)

        label(dialog, "Two-Factor Password (Cloud Password)", bold=True, size=12).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        label(
            dialog,
            "Your Telegram account has two-factor authentication enabled. "
            "Enter your account password (the one set under Two-Step "
            "Verification in Telegram settings).",
            muted=True, wraplength=430,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        var = tk.StringVar()
        ent = entry(dialog, var, show="•")
        ent.pack(fill="x", padx=20, ipady=6)
        ent.focus_set()

        def submit(_event=None):
            answer = var.get()
            if not answer:
                return
            auth_bridge.provide_answer(answer)
            try:
                dialog.destroy()
            except tk.TclError:
                pass
            self._password_dialog = None

        ent.bind("<Return>", submit)
        button(dialog, "Submit", submit, kind="accent").pack(pady=18)

    # ---------------------------------------------------------------
    # Fallback OTP prompt (when the wizard step 2 isn't visible)
    # ---------------------------------------------------------------

    def _show_login_prompt_dialog(self, prompt_text: str):
        existing = getattr(self, "_prompt_dialog", None)
        if existing is not None and existing.winfo_exists():
            try:
                existing.destroy()
            except tk.TclError:
                pass

        platform_name = platform_name_en(config.PLATFORM) or "messenger"

        dialog = tk.Toplevel(self)
        self._prompt_dialog = dialog
        dialog.title(f"Log in to {platform_name}")
        dialog.configure(bg=COLORS["sidebar_bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("460x220")
        dialog.resizable(False, False)

        label(dialog, f"Log in to your {platform_name} account", bold=True, size=12).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        label(
            dialog,
            f"{platform_name} is asking for:  {prompt_text.strip() or '?'}",
            muted=True, wraplength=420,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        var = tk.StringVar()
        ent = entry(dialog, var)
        ent.pack(fill="x", padx=20, ipady=6)
        ent.focus_set()

        def submit(_event=None):
            answer = var.get().strip()
            if not answer:
                return
            auth_bridge.provide_answer(answer)
            try:
                dialog.destroy()
            except tk.TclError:
                pass
            self._prompt_dialog = None

        ent.bind("<Return>", submit)
        button(dialog, "Submit", submit, kind="accent").pack(pady=18)
