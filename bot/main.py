"""
Bot runtime: message loop + Start / Stop (pause) controls used by the GUI.

    start(phone)  -> spins up the bot thread if it isn't running, or
                     resumes it if it is currently paused
    pause()       -> keep the thread alive but stop replying
    resume()      -> re-enable replies
    stop()        -> best-effort disconnect (called on window close)

Events emitted:
    "bot_control"  state="running" | "paused" | "stopped"
    "status"       status="starting" | "connected" | "crashed"
"""

from __future__ import annotations

import asyncio
import threading
import traceback

from . import auth_bridge, config, events, state


def _friendly_error(exc: Exception) -> str:
    """
    Translate common backend failures into a short, user-facing sentence.
    Falls back to the raw repr for anything unknown.
    """

    text = repr(exc)
    lower = text.lower()

    if "invalid_input" in lower or "invalidinput" in lower:
        return "The submitted data is invalid (likely a wrong phone number or login code)."
    if "notregistered" in lower:
        return "The current session is no longer valid; you need to log in again."
    if "phone" in lower and "invalid" in lower:
        return "The phone number is invalid."
    if "flood" in lower or "too_many" in lower:
        return "Too many requests; wait a few minutes and try again."
    if "connection" in lower or "timeout" in lower or "network" in lower:
        return "Could not connect to the server; check your internet connection."
    if "unauthorized" in lower or "authkey" in lower or "authkeyunregistered" in lower:
        return "The session was revoked by the server; please log in again."

    # Truncate very long tracebacks
    if len(text) > 160:
        text = text[:157] + "..."
    return text


async def _on_rubika_startup():
    """
    Runs once rubpy has authenticated (or restored a session). Records
    the running loop so `stop()` can disconnect cleanly, and tells the GUI
    we're online.
    """

    from . import handlers
    from .clients import app

    try:
        state.bot_loop = asyncio.get_running_loop()
        me = await app.get_me()
        handlers.my_guid = me.user.user_guid
        events.emit(
            "status",
            status="connected",
            phone=getattr(me.user, "phone", None),
            username=getattr(me.user, "username", None),
        )
    except Exception as exc:
        events.emit("status", status="crashed", detail=repr(exc))
        raise


def _run_rubika(phone_number: str | None) -> None:
    from . import handlers  # noqa: F401  (registers on_message)
    from .clients import app  # deferred so it uses the live config

    auth_bridge.install()
    try:
        app.run(_on_rubika_startup(), phone_number=phone_number)
    except Exception as exc:
        # If rubpy tripped over an invalidated / half-corrupted session
        # (INVALID_INPUT on send_code, NotRegistered on get_me, an import_key
        # of None), the .rp file cannot be trusted any more. Delete it so
        # the next Start walks the user through a fresh OTP.
        message = repr(exc)
        looks_broken = any(
            marker in message
            for marker in (
                "INVALID_INPUT",
                "NotRegistered",
                "import_key",
                "AttributeError",
            )
        )
        if looks_broken:
            try:
                config.session_file_path(config.RUBIKA_SESSION).unlink(missing_ok=True)
            except OSError:
                pass
            events.emit(
                "session_invalid",
                platform="rubika",
                detail="The Rubika session is no longer valid. Please log in again.",
            )
        else:
            events.emit(
                "status",
                status="crashed",
                detail=_friendly_error(exc),
            )
        raise
    finally:
        auth_bridge.uninstall()


def _run_telegram() -> None:
    from .telegram_runtime import run_telegram
    run_telegram()


def _bot_target(phone_number: str | None):
    state.active = True
    events.emit("status", status="starting")
    events.emit("bot_control", state="running")

    try:
        if config.PLATFORM == "telegram":
            _run_telegram()
        else:
            _run_rubika(phone_number)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        events.emit("status", status="crashed", detail=_friendly_error(exc))
        traceback.print_exc()
    finally:
        state.bot_loop = None
        state.active = False
        state.bot_thread = None
        events.emit("bot_control", state="stopped")


def start(phone_number: str | None = None) -> None:
    """Start the bot, or resume it if it is already running."""

    if state.is_running():
        if not state.active:
            state.active = True
            events.emit("bot_control", state="running")
        return

    thread = threading.Thread(
        target=_bot_target,
        args=(phone_number,),
        name="rubika-bot",
        daemon=True,
    )
    state.bot_thread = thread
    thread.start()


def pause() -> None:
    """Stop replying to new messages. Thread stays alive so we can resume."""

    if not state.is_running():
        events.emit("bot_control", state="stopped")
        return

    state.active = False
    events.emit("bot_control", state="paused")


def resume() -> None:
    if not state.is_running():
        return

    state.active = True
    events.emit("bot_control", state="running")


def stop() -> None:
    """
    Best-effort shutdown (called from the GUI's close handler and from
    the Logout button). Uses run_coroutine_threadsafe so we can ask
    rubpy's loop to disconnect from any thread.
    """

    loop = state.bot_loop
    if loop is None:
        state.active = False
        return

    async def _bye():
        from .clients import app
        try:
            await app.disconnect()
        except Exception:
            pass

    try:
        asyncio.run_coroutine_threadsafe(_bye(), loop)
    except Exception:
        pass


# ------------------------------------------------------------------
# Console entry-point (kept for parity with run.py)
# ------------------------------------------------------------------


def run(phone_number: str | None = None):
    """Blocking console mode — no GUI."""

    from .clients import app
    app.run(_on_rubika_startup(), phone_number=phone_number)


if __name__ == "__main__":
    run()


# Legacy alias.
run_in_background = start
