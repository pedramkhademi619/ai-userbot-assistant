"""
Onboarding wizard views: platform picker, Rubika steps 1-3, Telegram steps 1-3.

Everything lives on a mixin so ChatDashboard can inherit it and call
`self._show_platform_select()` etc. directly.
"""

import tkinter as tk
from tkinter import ttk

from .. import auth_bridge, config
from .theme import COLORS
from .widgets import ScrollableFrame, button, entry, label


class WizardMixin:
    # ---------------------------------------------------------------
    # Card + form helpers
    # ---------------------------------------------------------------

    def _wizard_card(self, title: str, subtitle: str = "") -> tk.Frame:
        """Centred card container; returns the inner frame to pack into."""

        self._clear_body()

        wrapper = tk.Frame(self.body, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True)

        card = tk.Frame(wrapper, bg=COLORS["sidebar_bg"])
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.66, relheight=0.85)

        scroll = ScrollableFrame(card, bg=COLORS["sidebar_bg"])
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        inner = tk.Frame(scroll.inner, bg=COLORS["sidebar_bg"])
        inner.pack(fill="x", padx=32, pady=28)

        label(inner, title, bold=True, size=15).pack(anchor="w", pady=(0, 4))
        if subtitle:
            label(inner, subtitle, muted=True, wraplength=600).pack(anchor="w", pady=(0, 18))

        return inner

    def _wizard_error(self, feedback_label: tk.Label, msg: str):
        feedback_label.configure(text=f"⚠️  {msg}", fg=COLORS["danger"])

    def _add_field(self, parent, row, col, text, var, *, hint=None, secret=False):
        cell = tk.Frame(parent, bg=COLORS["sidebar_bg"])
        cell.grid(row=row, column=col, sticky="ew", padx=8, pady=6)
        cell.columnconfigure(0, weight=1)

        label(cell, text, bold=True).grid(row=0, column=0, sticky="w")

        ent = entry(cell, var, show="•" if secret else None)
        ent.grid(row=1, column=0, sticky="ew", ipady=6, pady=(3, 0))

        if hint:
            label(cell, hint, muted=True, size=8).grid(row=2, column=0, sticky="w", pady=(2, 0))

    # ---------------------------------------------------------------
    # Platform select
    # ---------------------------------------------------------------

    def _route_wizard_first_step(self):
        if config.PLATFORM == "telegram":
            self._show_tg_wizard_step1()
        else:
            self._show_wizard_step1()

    def _show_platform_select(self):
        self._clear_body()

        wrapper = tk.Frame(self.body, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True)

        card = tk.Frame(wrapper, bg=COLORS["sidebar_bg"])
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.65)

        inner = tk.Frame(card, bg=COLORS["sidebar_bg"])
        inner.pack(fill="both", expand=True, padx=32, pady=28)

        label(inner, "Welcome to AI Bot", bold=True, size=15).pack(anchor="w", pady=(0, 4))
        label(
            inner,
            "To get started, choose which messenger the assistant should run on.",
            muted=True,
            wraplength=560,
        ).pack(anchor="w", pady=(0, 24))

        options = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        options.pack(fill="both", expand=True)
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        def platform_card(col, title, subtitle, hint, on_click):
            frame = tk.Frame(options, bg=COLORS["input_bg"], cursor="hand2")
            frame.grid(row=0, column=col, sticky="nsew", padx=8, ipady=18)

            label(frame, title, bold=True, size=13).pack(anchor="center", pady=(16, 4))
            label(frame, subtitle, muted=False).pack(anchor="center")
            label(frame, hint, muted=True, wraplength=240).pack(anchor="center", pady=(10, 16))

            for w in [frame] + list(frame.winfo_children()):
                w.bind("<Button-1>", lambda _e: on_click())

        def pick_rubika():
            config.save_settings({"PLATFORM": "rubika"})
            config.reload_config()
            self._refresh_header_title()
            self._show_wizard_step1()

        def pick_telegram():
            config.save_settings({"PLATFORM": "telegram"})
            config.reload_config()
            self._refresh_header_title()
            self._show_tg_wizard_step1()

        platform_card(
            0,
            "📱  Rubika",
            "Rubika",
            "Connects to your personal Rubika account using your phone "
            "number and an SMS code.",
            pick_rubika,
        )
        platform_card(
            1,
            "✈️  Telegram",
            "Telegram",
            "Connects to your personal Telegram account using your own "
            "phone number (userbot).",
            pick_telegram,
        )

    # ---------------------------------------------------------------
    # Rubika Step 1: phone + session
    # ---------------------------------------------------------------

    def _show_wizard_step1(self):
        inner = self._wizard_card(
            "Log in to Rubika (1 of 3)",
            "Enter the Rubika phone number the bot should reply from, and a "
            "name for this session.",
        )

        self.var_phone = tk.StringVar(value=self._wizard_data.get("phone", config.RUBIKA_PHONE or ""))
        self.var_session = tk.StringVar(
            value=self._wizard_data.get("session", config.RUBIKA_SESSION or "")
        )

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)

        self._add_field(form, 0, 0, "Rubika phone number", self.var_phone, hint="e.g. 09123456789")
        self._add_field(form, 1, 0, "Session name", self.var_session,
                        hint="Any name you like; the session file is saved under it (e.g. work → work.rp)")

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["danger"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(14, 6))

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def on_next():
            phone = self.var_phone.get().strip()
            session = self.var_session.get().strip()
            if not phone:
                return self._wizard_error(feedback, "Enter a phone number.")
            if not session:
                return self._wizard_error(feedback, "Enter a session name.")

            self._wizard_data["phone"] = phone
            self._wizard_data["session"] = session

            if config.session_file_path(session).exists():
                self._show_wizard_step3()
            else:
                self._show_wizard_step2()

        button(actions, "Next  ➜", on_next, kind="accent").pack(side="right")
        button(actions, "Back", self._show_platform_select, kind="ghost").pack(
            side="right", padx=(0, 8)
        )

    # ---------------------------------------------------------------
    # Rubika Step 2: OTP
    # ---------------------------------------------------------------

    def _show_wizard_step2(self):
        inner = self._wizard_card(
            "Rubika verification code (2 of 3)",
            "Rubika is sending an SMS code to the number you entered. Enter it below.",
        )

        self.var_otp = tk.StringVar()

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)

        self._add_field(form, 0, 0, "Rubika login code (SMS)", self.var_otp,
                        hint="The 5-digit code sent to your phone")

        self.step2_status = tk.Label(inner, text="Sending code...",
                                     bg=COLORS["sidebar_bg"], fg=COLORS["muted"], font=self.meta_font)
        self.step2_status.pack(anchor="w", pady=(14, 4))

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["danger"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(2, 6))
        self.step2_feedback = feedback

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def submit_otp():
            code = self.var_otp.get().strip()
            if not code:
                return self._wizard_error(feedback, "Enter the code.")
            self.step2_status.configure(text="Verifying code...", fg=COLORS["muted"])
            auth_bridge.provide_answer(code)

        button(actions, "Submit code", submit_otp, kind="accent").pack(side="right")
        button(actions, "Back", self._show_wizard_step1, kind="ghost").pack(
            side="right", padx=(0, 8)
        )

        from ..auth import login_in_background
        self._auth_thread = login_in_background(
            self._wizard_data["session"],
            self._wizard_data["phone"],
        )

    # ---------------------------------------------------------------
    # Telegram Step 1: api_id / api_hash / phone / session
    # ---------------------------------------------------------------

    def _show_tg_wizard_step1(self):
        inner = self._wizard_card(
            "Log in to Telegram (1 of 3)",
            "The assistant logs into Telegram using your own phone number "
            "(userbot mode). You'll need an api_id and api_hash, issued "
            "for free at my.telegram.org.",
        )

        self.var_tg_api_id = tk.StringVar(
            value=self._wizard_data.get("tg_api_id", config.TELEGRAM_API_ID or "")
        )
        self.var_tg_api_hash = tk.StringVar(
            value=self._wizard_data.get("tg_api_hash", config.TELEGRAM_API_HASH or "")
        )
        self.var_tg_phone = tk.StringVar(
            value=self._wizard_data.get("tg_phone", config.TELEGRAM_PHONE or "")
        )
        self.var_tg_session = tk.StringVar(
            value=self._wizard_data.get("tg_session", config.TELEGRAM_SESSION or "telegram_user")
        )

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self._add_field(form, 0, 0, "Telegram phone number", self.var_tg_phone,
                        hint="Including country code, e.g. +989123456789")
        self._add_field(form, 0, 1, "Session name", self.var_tg_session,
                        hint="Any name you like; the session file is saved under it.")
        self._add_field(form, 1, 0, "API ID", self.var_tg_api_id,
                        hint="An integer, from my.telegram.org")
        self._add_field(form, 1, 1, "API Hash", self.var_tg_api_hash,
                        hint="A 32-character string, from my.telegram.org", secret=True)

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["danger"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(14, 6))

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def on_next():
            api_id = self.var_tg_api_id.get().strip()
            api_hash = self.var_tg_api_hash.get().strip()
            phone = self.var_tg_phone.get().strip()
            session = self.var_tg_session.get().strip()

            if not phone:
                return self._wizard_error(feedback, "Enter a phone number.")
            if not session:
                return self._wizard_error(feedback, "Enter a session name.")
            if not api_id.isdigit():
                return self._wizard_error(feedback, "API ID must be an integer.")
            if len(api_hash) < 30:
                return self._wizard_error(feedback, "API Hash is invalid.")

            self._wizard_data["tg_api_id"] = api_id
            self._wizard_data["tg_api_hash"] = api_hash
            self._wizard_data["tg_phone"] = phone
            self._wizard_data["tg_session"] = session

            if config.telegram_session_file_path(session).exists():
                self._show_wizard_step3()
            else:
                self._show_tg_wizard_step2()

        button(actions, "Next  ➜", on_next, kind="accent").pack(side="right")
        button(actions, "Back", self._show_platform_select, kind="ghost").pack(
            side="right", padx=(0, 8)
        )

    # ---------------------------------------------------------------
    # Telegram Step 2: OTP (+ 2FA handled by dialog)
    # ---------------------------------------------------------------

    def _show_tg_wizard_step2(self):
        inner = self._wizard_card(
            "Telegram verification code (2 of 3)",
            "Telegram is sending a code to your Telegram app on phone/desktop. "
            "Enter it below. If you have two-factor authentication enabled, "
            "you'll be asked for your password next.",
        )

        self.var_otp = tk.StringVar()

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)

        self._add_field(form, 0, 0, "Telegram login code", self.var_otp,
                        hint="The 5-digit code sent by Telegram")

        self.step2_status = tk.Label(inner, text="Sending code...",
                                     bg=COLORS["sidebar_bg"], fg=COLORS["muted"], font=self.meta_font)
        self.step2_status.pack(anchor="w", pady=(14, 4))

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["danger"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(2, 6))
        self.step2_feedback = feedback

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def submit_otp():
            code = self.var_otp.get().strip()
            if not code:
                return self._wizard_error(feedback, "Enter the code.")
            self.step2_status.configure(text="Verifying code...", fg=COLORS["muted"])
            auth_bridge.provide_answer(code)
            self.var_otp.set("")

        button(actions, "Submit code", submit_otp, kind="accent").pack(side="right")
        button(actions, "Back", self._show_tg_wizard_step1, kind="ghost").pack(
            side="right", padx=(0, 8)
        )

        from ..telegram_runtime import login_in_background
        self._auth_thread = login_in_background(
            self._wizard_data["tg_session"],
            self._wizard_data["tg_api_id"],
            self._wizard_data["tg_api_hash"],
            self._wizard_data["tg_phone"],
        )

    # ---------------------------------------------------------------
    # Shared Step 3: AI backend settings + system prompt
    # ---------------------------------------------------------------

    def _show_wizard_step3(self):
        is_tg = config.PLATFORM == "telegram"
        inner = self._wizard_card(
            "AI settings (3 of 3)",
            "Fill in your AI model details and the assistant's system prompt.",
        )

        backend = getattr(config.secrets_store, "backend_name", "?")
        backend_label = {
            "dpapi": "encrypted with Windows DPAPI (tied to your user account)",
            "fernet": "encrypted with Fernet (cryptography)",
        }.get(backend, f"backend: {backend}")

        self.var_api_key = tk.StringVar(value=config.API_KEY or "")
        self.var_base_url = tk.StringVar(value=config.BASE_URL or "")
        self.var_model = tk.StringVar(value=config.MODEL or "")
        self.var_max_tokens = tk.StringVar(value=str(config.MAX_OUTPUT_TOKENS))
        self.var_max_history = tk.StringVar(value=str(config.MAX_HISTORY_PAIRS))

        form = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self._add_field(form, 0, 0, "API key", self.var_api_key,
                        hint=f"Stored outside the project directory; {backend_label}",
                        secret=True)
        self._add_field(form, 0, 1, "Base URL", self.var_base_url,
                        hint="e.g. https://api.gapgpt.app/v1")
        self._add_field(form, 1, 0, "AI model", self.var_model, hint="e.g. gpt-4o-mini")
        self._add_field(form, 1, 1, "Max output tokens", self.var_max_tokens)
        self._add_field(form, 2, 0, "History length (message pairs)", self.var_max_history)

        label(inner, "Assistant data (System Prompt)", bold=True, size=11).pack(anchor="w", pady=(18, 4))
        label(
            inner,
            "This text is given to the model to shape how it replies. A "
            "default template is provided below and can be edited freely.",
            muted=True,
            wraplength=600,
        ).pack(anchor="w", pady=(0, 6))

        prompt_wrapper = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        prompt_wrapper.pack(fill="both", expand=True)

        prompt_scroll = ttk.Scrollbar(prompt_wrapper, orient="vertical")
        self.setup_prompt = tk.Text(
            prompt_wrapper, height=10, wrap="word",
            bg=COLORS["field_bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", font=self.msg_font, yscrollcommand=prompt_scroll.set,
        )
        prompt_scroll.configure(command=self.setup_prompt.yview)
        self.setup_prompt.pack(side="left", fill="both", expand=True)
        prompt_scroll.pack(side="right", fill="y")
        self.setup_prompt.insert("1.0", config.SYSTEM_PROMPT)

        feedback = tk.Label(inner, text="", bg=COLORS["sidebar_bg"], fg=COLORS["danger"],
                            font=self.meta_font)
        feedback.pack(anchor="w", pady=(14, 6))

        actions = tk.Frame(inner, bg=COLORS["sidebar_bg"])
        actions.pack(fill="x", pady=(6, 0))

        def finish():
            api_key = self.var_api_key.get().strip()
            base_url = self.var_base_url.get().strip()
            model = self.var_model.get().strip()

            if not api_key:
                return self._wizard_error(feedback, "Enter an API key.")
            if not base_url:
                return self._wizard_error(feedback, "Base URL is empty.")
            if not model:
                return self._wizard_error(feedback, "Model name is empty.")

            try:
                max_tokens = int(self.var_max_tokens.get())
                max_history = int(self.var_max_history.get())
            except ValueError:
                return self._wizard_error(feedback, "Token and history values must be integers.")

            settings_update = {
                "PLATFORM": config.PLATFORM,
                "RUBIKA_API_KEY": api_key,
                "BASE_URL": base_url,
                "MODEL": model,
                "MAX_OUTPUT_TOKENS": max_tokens,
                "MAX_HISTORY_PAIRS": max_history,
            }
            if is_tg:
                settings_update["TELEGRAM_API_ID"] = self._wizard_data.get(
                    "tg_api_id", config.TELEGRAM_API_ID)
                settings_update["TELEGRAM_API_HASH"] = self._wizard_data.get(
                    "tg_api_hash", config.TELEGRAM_API_HASH)
                settings_update["TELEGRAM_PHONE"] = self._wizard_data.get(
                    "tg_phone", config.TELEGRAM_PHONE)
                settings_update["TELEGRAM_SESSION"] = self._wizard_data.get(
                    "tg_session", config.TELEGRAM_SESSION)
            else:
                settings_update["RUBIKA_SESSION"] = self._wizard_data.get(
                    "session", config.RUBIKA_SESSION)
                settings_update["RUBIKA_PHONE"] = self._wizard_data.get(
                    "phone", config.RUBIKA_PHONE)

            try:
                config.save_settings(settings_update)
                config.reload_config()
                config.overwrite_system_prompt(self.setup_prompt.get("1.0", "end"))
            except Exception as exc:
                return self._wizard_error(feedback, f"Saving failed: {exc}")

            self._refresh_header_title()
            self._show_chat_view()

        button(actions, "Finish ➜", finish, kind="accent").pack(side="right")
        back = self._show_tg_wizard_step1 if is_tg else self._show_wizard_step1
        button(actions, "Back", back, kind="ghost").pack(side="right", padx=(0, 8))
