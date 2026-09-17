"""
Event pump: poll the shared bus at a fixed interval and dispatch each
event to the appropriate view handler.

Also owns the "connected" identity — when the runtime reports our own
username / phone, we cache it on the dashboard so outgoing bubbles can
be labelled as *me* rather than the recipient.
"""

import queue
import tkinter as tk

from .. import config
from .theme import COLORS, platform_name_en

# Cap events processed per Tk after() tick. Prevents a single burst of
# events (e.g. many messages arriving at once) from freezing the UI.
_MAX_EVENTS_PER_TICK = 30
_POLL_INTERVAL_MS = 200


class EventPumpMixin:

    def _poll_events(self):
        processed = 0
        while processed < _MAX_EVENTS_PER_TICK:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event)
            except tk.TclError:
                pass  # widget torn down mid-swap
            processed += 1

        self.after(_POLL_INTERVAL_MS, self._poll_events)

    # ---------------------------------------------------------------
    # Dispatch
    # ---------------------------------------------------------------

    def _handle_event(self, event: dict):
        etype = event.get("type")

        if etype == "in":
            self._add_message(
                f"👤 {self._sender_label(event)}",
                event["text"],
                align="left",
                bubble_bg=COLORS["user_bubble"],
                text_fg=COLORS["text"],
            )

        elif etype == "out":
            kind = event.get("kind", "ai")
            bubble_bg = {
                "ai": COLORS["bot_bubble"],
                "cache": COLORS["bot_cache_bubble"],
                "system": COLORS["bot_system_bubble"],
                "error": COLORS["bot_error_bubble"],
            }.get(kind, COLORS["bot_bubble"])
            suffix = {
                "ai": "",
                "cache": " (cached)",
                "system": " (auto)",
                "error": " (error)",
            }.get(kind, "")

            self._add_message(
                f"🤖 {self._me_label()}{suffix}",
                event["text"],
                align="right",
                bubble_bg=bubble_bg,
                text_fg="white",
            )

        elif etype == "status":
            self._update_status(event)

        elif etype == "bot_control":
            self._on_bot_control_event(event)

        elif etype == "prompt":
            self._on_prompt_event(event.get("prompt", ""))

        elif etype == "auth_done":
            self._on_auth_done(event)

        elif etype == "session_invalid":
            self._on_session_invalid(event)

    # ---------------------------------------------------------------
    # Individual handlers
    # ---------------------------------------------------------------

    def _update_status(self, event: dict):
        status = event.get("status")
        platform_label = platform_name_en(config.PLATFORM) or "messenger"

        if status == "starting":
            self.status_canvas.itemconfigure(self.status_dot, fill=COLORS["warn"])
            self.status_label.configure(text="Starting...", fg=COLORS["muted"])
        elif status == "connected":
            # Cache the owner's identity for outgoing-bubble labels.
            self._me_username = event.get("username") or None
            self._me_phone = event.get("phone") or None

            self.status_canvas.itemconfigure(self.status_dot, fill=COLORS["ok"])
            extra = ""
            if self._me_username:
                extra = f"  ·  @{self._me_username}"
            elif self._me_phone:
                extra = f"  ·  {self._me_phone}"
            self.status_label.configure(
                text=f"Connected to {platform_label}{extra}", fg=COLORS["text"],
            )
        elif status == "crashed":
            detail = event.get("detail", "Unknown error")
            self.status_canvas.itemconfigure(self.status_dot, fill=COLORS["danger"])
            short = detail if len(detail) < 50 else detail[:47] + "..."
            self.status_label.configure(text=f"Error: {short}", fg=COLORS["danger"])
            self._show_error_dialog("Something went wrong", detail)

    def _on_bot_control_event(self, _event: dict):
        if hasattr(self, "bot_state_label"):
            self._refresh_bot_control_label()

    def _on_session_invalid(self, event: dict):
        detail = event.get("detail", "The current session is no longer valid. Please log in again.")

        def relogin():
            self._wizard_data.clear()
            self._me_username = None
            self._me_phone = None
            self._route_wizard_first_step()

        self._show_error_dialog(
            "Login required again",
            detail,
            action_label="Log in again",
            action_command=relogin,
        )

    def _on_prompt_event(self, prompt_text: str):
        raw = (prompt_text or "").strip()
        low = raw.lower()

        # 2FA / cloud password: always route to a masked dedicated dialog.
        if "password" in low:
            self._show_password_dialog()
            return

        platform_name = platform_name_en(config.PLATFORM) or "messenger"

        # OTP path: use the inline OTP status when the wizard step 2 is
        # visible; otherwise fall back to a dialog.
        if hasattr(self, "step2_status") and self.step2_status.winfo_exists():
            self.step2_status.configure(
                text=f"{platform_name} is asking for a code ({raw or 'Code:'})",
                fg=COLORS["muted"],
            )
            return

        self._show_login_prompt_dialog(raw)

    def _on_auth_done(self, event: dict):
        if event.get("success"):
            # Wizard step 2 was showing OTP; advance to AI settings.
            if hasattr(self, "step2_status") and self.step2_status.winfo_exists():
                self._show_wizard_step3()
        else:
            detail = event.get("detail", "Unknown error")
            if hasattr(self, "step2_feedback") and self.step2_feedback.winfo_exists():
                self._wizard_error(self.step2_feedback, f"Login failed: {detail}")
                self.step2_status.configure(text="", fg=COLORS["muted"])
