"""Settings view — edit every config value after login; logout + switch platform."""

import tkinter as tk

from .. import config
from .theme import COLORS, platform_name_en
from .widgets import button


class SettingsViewMixin:

    def _show_settings_view(self):
        is_tg = config.PLATFORM == "telegram"
        platform_name = platform_name_en(config.PLATFORM) or "messenger"

        inner = self._wizard_card(
            f"⚙  Settings ({platform_name})",
            "You can edit the stored values below. To switch messenger or "
            "log out, use \"Log out & switch messenger\".",
        )

        s_api = tk.StringVar(value=config.API_KEY or "")
        s_base = tk.StringVar(value=config.BASE_URL or "")
        s_model = tk.StringVar(value=config.MODEL or "")
        s_tokens = tk.StringVar(value=str(config.MAX_OUTPUT_TOKENS))
        s_history = tk.StringVar(value=str(config.MAX_HISTORY_PAIRS))
        s_phone = tk.StringVar(value=config.RUBIKA_PHONE or "")
        s_session = tk.StringVar(value=config.RUBIKA_SESSION or "")
        s_tg_phone = tk.StringVar(value=config.TELEGRAM_PHONE or "")
        s_tg_session = tk.StringVar(value=config.TELEGRAM_SESSION or "")
        s_tg_api_id = tk.StringVar(value=config.TELEGRAM_API_ID or "")
        s_tg_api_hash = tk.StringVar(value=config.TELEGRAM_API_HASH or "")

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        row = 0
        if is_tg:
            self._add_field(form, row, 0, "Telegram phone number", s_tg_phone)
            self._add_field(form, row, 1, "Session name", s_tg_session,
                            hint="Changing this logs you out of the current account.")
            row += 1
            self._add_field(form, row, 0, "API ID", s_tg_api_id, hint="From my.telegram.org")
            self._add_field(form, row, 1, "API Hash", s_tg_api_hash, secret=True,
                            hint="From my.telegram.org")
            row += 1
        else:
            self._add_field(form, row, 0, "Rubika phone number", s_phone)
            self._add_field(form, row, 1, "Session name", s_session,
                            hint="Changing this logs you out of the current account.")
            row += 1

        self._add_field(form, row, 0, "API key", s_api, secret=True)
        self._add_field(form, row, 1, "Base URL", s_base)
        row += 1
        self._add_field(form, row, 0, "AI model", s_model)
        self._add_field(form, row, 1, "Max output tokens", s_tokens)
        row += 1
        self._add_field(form, row, 0, "History length", s_history)

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["ok"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(14, 6))

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def save():
            try:
                max_tokens = int(s_tokens.get())
                max_history = int(s_history.get())
            except ValueError:
                feedback.configure(text="⚠️  Token and history length must be numbers.", fg=COLORS["danger"])
                return

            updates = {
                "RUBIKA_API_KEY": s_api.get().strip(),
                "BASE_URL": s_base.get().strip(),
                "MODEL": s_model.get().strip(),
                "MAX_OUTPUT_TOKENS": max_tokens,
                "MAX_HISTORY_PAIRS": max_history,
            }
            if is_tg:
                updates["TELEGRAM_API_ID"] = s_tg_api_id.get().strip()
                updates["TELEGRAM_API_HASH"] = s_tg_api_hash.get().strip()
                updates["TELEGRAM_PHONE"] = s_tg_phone.get().strip()
                updates["TELEGRAM_SESSION"] = s_tg_session.get().strip()
            else:
                updates["RUBIKA_SESSION"] = s_session.get().strip()
                updates["RUBIKA_PHONE"] = s_phone.get().strip()

            config.save_settings(updates)
            config.reload_config()
            feedback.configure(
                text="✅ Saved. Stop and Start the bot again for changes to fully take effect.",
                fg=COLORS["ok"],
            )

        def logout():
            from .. import main as bot_main
            bot_main.stop()
            config.logout()
            config.save_settings({
                "RUBIKA_API_KEY": "",
                "RUBIKA_PHONE": "",
                "TELEGRAM_API_ID": "",
                "TELEGRAM_API_HASH": "",
                "TELEGRAM_PHONE": "",
                "PLATFORM": "",
            })
            config.reload_config()
            self._wizard_data.clear()
            self._me_username = None
            self._me_phone = None
            self._refresh_header_title()
            self._show_platform_select()

        button(actions, "💾  Save", save, kind="accent").pack(side="right")
        button(actions, "↩  Back to chat", self._show_chat_view, kind="ghost").pack(
            side="right", padx=(0, 8)
        )
        button(actions, "🚪  Log out & switch messenger", logout, kind="danger").pack(side="left")
