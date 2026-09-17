"""
Telegram runtime — connects as a *user* (userbot mode), not a bot.

Uses Telethon's MTProto client: the account owner logs in with their own
phone number + the code Telegram sends them in-app (+ optional 2FA
password). After that the assistant replies to private messages sent to
their real Telegram account.

Shares the AI logic (rate-limit, cache, generate_response, system
prompt) with the Rubika path. Only the messaging plumbing lives here.
"""

from __future__ import annotations

import asyncio
import logging

from telethon import TelegramClient
from telethon import events as tg_events

from . import auth_bridge, config, events, state
from .ai import generate_response
from .memory import cache_response, get_cached_response, is_rate_limited, user_locks

# Telethon is chatty at INFO; keep the console (and the Tk main thread,
# which shares stdout on Windows) quiet.
logging.getLogger("telethon").setLevel(logging.WARNING)


# ------------------------------------------------------------------
# Message handler
# ------------------------------------------------------------------


async def _on_private_message(event: tg_events.NewMessage.Event) -> None:
    # Only private (1-on-1) chats
    if not event.is_private:
        return
    # Ignore messages we sent ourselves
    if getattr(event.message, "out", False):
        return
    if not state.active:
        return

    text = (event.raw_text or "").strip()
    if not text:
        return

    sender = await event.get_sender()
    user_id = str(getattr(sender, "id", "unknown"))

    display = None
    if sender is not None:
        first = getattr(sender, "first_name", "") or ""
        last = getattr(sender, "last_name", "") or ""
        name = (first + " " + last).strip()
        display = name or getattr(sender, "username", None) or user_id

    events.emit("in", user_id=user_id, display_name=display, text=text)

    async def reply(text_out: str) -> None:
        await event.respond(text_out)

    if len(text) > config.MAX_MESSAGE_LENGTH:
        msg = "Your message is too long. Please shorten it."
        events.emit("out", user_id=user_id, display_name=display, text=msg, kind="system")
        await reply(msg)
        return

    if is_rate_limited(user_id):
        msg = "You're sending messages too fast. Wait a moment and try again."
        events.emit("out", user_id=user_id, display_name=display, text=msg, kind="system")
        await reply(msg)
        return

    cached = get_cached_response(text)
    if cached:
        events.emit("out", user_id=user_id, display_name=display, text=cached, kind="cache")
        await reply(cached)
        return

    lock = user_locks[user_id]
    if lock.locked():
        msg = "Your previous message is still being processed; give it a moment."
        events.emit("out", user_id=user_id, display_name=display, text=msg, kind="system")
        await reply(msg)
        return

    try:
        async with asyncio.timeout(config.USER_LOCK_TIMEOUT):
            async with lock:
                answer = await generate_response(user_id, text)
    except asyncio.TimeoutError:
        msg = "The request took too long to process. Please try again."
        events.emit("out", user_id=user_id, display_name=display, text=msg, kind="system")
        await reply(msg)
        return
    except Exception as exc:
        events.emit("error", user_id=user_id, detail=repr(exc))
        msg = "Something went wrong processing your message. Please try again."
        events.emit("out", user_id=user_id, display_name=display, text=msg, kind="error")
        await reply(msg)
        return

    cache_response(text, answer)
    events.emit("out", user_id=user_id, display_name=display, text=answer, kind="ai")
    await reply(answer)


# ------------------------------------------------------------------
# Auth helpers (used both by the wizard's login step and the runtime)
# ------------------------------------------------------------------


def _build_client(session_name: str, api_id: str | int, api_hash: str) -> TelegramClient:
    return TelegramClient(
        str(config.BASE_DIR / session_name),
        int(api_id),
        api_hash,
        device_model="Rubika AI Bot",
        system_version="1.0",
        app_version="1.0",
    )


async def _telethon_code_cb() -> str:
    return await auth_bridge.async_prompt("Code:")


async def _telethon_password_cb() -> str:
    return await auth_bridge.async_prompt("Password (2FA):")


async def _sign_in(client: TelegramClient, phone: str) -> None:
    """
    Log in interactively. If the session is already valid, this is a no-op.
    Any input Telethon needs is routed through auth_bridge -> the GUI.
    """

    await client.start(
        phone=lambda: phone,
        code_callback=_telethon_code_cb,
        password=_telethon_password_cb,
    )


# ------------------------------------------------------------------
# Runtime
# ------------------------------------------------------------------


async def _run_async() -> None:
    if not (config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH):
        events.emit("status", status="crashed",
                    detail="TELEGRAM_API_ID / TELEGRAM_API_HASH is not set.")
        return

    client = _build_client(
        config.TELEGRAM_SESSION,
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH,
    )

    state.bot_loop = asyncio.get_running_loop()

    try:
        await _sign_in(client, config.TELEGRAM_PHONE)

        me = await client.get_me()
        events.emit(
            "status",
            status="connected",
            username=getattr(me, "username", None),
            phone=getattr(me, "phone", None),
        )

        client.add_event_handler(_on_private_message, tg_events.NewMessage(incoming=True))

        await client.run_until_disconnected()
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def run_telegram() -> None:
    """Blocking entrypoint called from bot.main._bot_target on the bot thread."""

    auth_bridge.install()
    try:
        asyncio.run(_run_async())
    except Exception as exc:
        message = repr(exc).lower()
        if "auth" in message and ("unregistered" in message or "invalid" in message):
            try:
                config.telegram_session_file_path(config.TELEGRAM_SESSION).unlink(missing_ok=True)
            except OSError:
                pass
            events.emit(
                "session_invalid",
                platform="telegram",
                detail="The Telegram session is no longer valid. Please log in again.",
            )
        raise
    finally:
        auth_bridge.uninstall()


# ------------------------------------------------------------------
# Auth-only (used by the wizard's Telegram OTP step)
# ------------------------------------------------------------------


async def _login_only_async(session_name: str, api_id: str, api_hash: str, phone: str) -> dict:
    client = _build_client(session_name, api_id, api_hash)
    try:
        await _sign_in(client, phone)
        me = await client.get_me()
        return {
            "username": getattr(me, "username", None),
            "phone": getattr(me, "phone", None),
            "user_id": str(getattr(me, "id", "")),
        }
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def login_in_background(session_name: str, api_id: str, api_hash: str, phone: str):
    """
    Kick off the Telegram sign-in flow on a background thread. Mirrors
    bot.auth.login_in_background but for Telethon.

    Emits: auth_started, prompt (via auth_bridge), auth_done{success, ...}
    """

    import threading
    import traceback

    def _target():
        auth_bridge.clear()
        auth_bridge.install()
        events.emit("auth_started")
        try:
            info = asyncio.run(_login_only_async(session_name, api_id, api_hash, phone))
            events.emit("auth_done", success=True, **info)
        except Exception as exc:
            traceback.print_exc()
            events.emit("auth_done", success=False, detail=repr(exc))
        finally:
            auth_bridge.uninstall()

    thread = threading.Thread(target=_target, name="telegram-auth", daemon=True)
    thread.start()
    return thread
