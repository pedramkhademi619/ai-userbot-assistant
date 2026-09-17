"""
One-shot Rubika login flow used by the GUI setup wizard.

Runs on a background thread so the Tk main loop stays responsive. When
rubpy asks for the OTP code via `input()`, our auth_bridge intercepts it
and the GUI shows an OTP screen; the answer comes back through the same
bridge.

Once `Client.start()` returns, the session file (`{session_name}.rp`) is
saved in the project root. We then disconnect immediately — the real bot
process starts later, when the user presses "Start" on the chat screen.
"""

from __future__ import annotations

import asyncio
import threading
import traceback

from rubpy import Client

from . import auth_bridge, events


async def _do_login(session_name: str, phone_number: str) -> dict:
    client = Client(session_name, phone_number=phone_number)
    try:
        await client.start(phone_number=phone_number)
        me = await client.get_me()
        return {
            "user_guid": me.user.user_guid,
            "phone": getattr(me.user, "phone", phone_number),
            "username": getattr(me.user, "username", None),
        }
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def login_in_background(session_name: str, phone_number: str) -> threading.Thread:
    """
    Start a login attempt on a background thread. Emits:

        auth_started               — right after the thread begins
        prompt                     — whenever rubpy asks for input (OTP,
                                     password, phone confirmation...)
        auth_done  success=True    — session file saved successfully
        auth_done  success=False   — with `detail` on failure
    """

    def _target():
        auth_bridge.clear()
        auth_bridge.install()
        events.emit("auth_started")

        try:
            info = asyncio.run(_do_login(session_name, phone_number))
            events.emit("auth_done", success=True, **info)
        except Exception as exc:
            traceback.print_exc()
            events.emit("auth_done", success=False, detail=repr(exc))
        finally:
            auth_bridge.uninstall()

    thread = threading.Thread(target=_target, name="rubika-auth", daemon=True)
    thread.start()
    return thread
