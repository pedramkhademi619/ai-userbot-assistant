"""Rubika message handlers."""

import asyncio

from rubpy import filters

from . import config, events, state
from .ai import generate_response
from .clients import app
from .memory import cache_response, get_cached_response, is_rate_limited, user_locks

my_guid = None


def _uid(update) -> str:
    """
    Best-effort stable identifier for a Rubika chat.

    `update.author_object_id` is the message sender's guid, but some update
    variants leave it unset (private chats often expose the chat guid via
    `object_guid` instead). We fall back through the sensible options so
    rate-limits and locks always key on *some* value.
    """

    for attr in ("author_object_id", "author_guid", "object_guid", "chat_id"):
        value = getattr(update, attr, None)
        if value:
            return str(value)
    return "unknown"


def _display_name(update) -> str | None:
    """Human-readable name of the sender when rubpy exposes one."""

    for attr in ("title", "first_name", "author_title", "username"):
        value = getattr(update, attr, None)
        if value:
            return str(value)
    return None


@app.on_message_updates(filters.private)
async def on_message(update):
    global my_guid

    if my_guid is None:
        me = await app.get_me()
        my_guid = me.user.user_guid
        # Safety net: if _on_startup somehow missed emitting connected, the
        # first real message proves we are online.
        events.emit("status", status="connected")

    user_id = _uid(update)
    display = _display_name(update)

    if user_id == my_guid:
        return

    # Paused via the Stop button — swallow silently.
    if not state.active:
        return

    text = (update.text or "").strip()

    if not text:
        return

    events.emit("in", user_id=user_id, display_name=display, text=text)

    # --------------------------------------------------------
    # Message length protection
    # --------------------------------------------------------

    if len(text) > config.MAX_MESSAGE_LENGTH:
        reply = "Your message is too long. Please shorten it."
        events.emit("out", user_id=user_id, display_name=display, text=reply, kind="system")
        await update.reply(reply)
        return

    # --------------------------------------------------------
    # Rate limit
    # --------------------------------------------------------

    if is_rate_limited(user_id):
        reply = "You're sending messages too fast. Wait a moment and try again."
        events.emit("out", user_id=user_id, display_name=display, text=reply, kind="system")
        await update.reply(reply)
        return

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    cached = get_cached_response(text)

    if cached:
        events.emit("out", user_id=user_id, display_name=display, text=cached, kind="cache")
        await update.reply(cached)
        return

    # --------------------------------------------------------
    # Prevent concurrent requests
    # --------------------------------------------------------

    lock = user_locks[user_id]

    if lock.locked():
        reply = "Your previous message is still being processed; give it a moment."
        events.emit("out", user_id=user_id, display_name=display, text=reply, kind="system")
        await update.reply(reply)
        return

    try:
        async with asyncio.timeout(config.USER_LOCK_TIMEOUT):
            async with lock:
                reply = await generate_response(user_id, text)

    except asyncio.TimeoutError:
        reply = "The request took too long to process. Please try again."
        events.emit("out", user_id=user_id, display_name=display, text=reply, kind="system")
        await update.reply(reply)
        return

    except Exception as e:
        events.emit("error", user_id=user_id, detail=repr(e))
        reply = "Something went wrong processing your message. Please try again."
        events.emit("out", user_id=user_id, display_name=display, text=reply, kind="error")
        await update.reply(reply)
        return

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    cache_response(text, reply)

    # --------------------------------------------------------
    # Send response
    # --------------------------------------------------------

    events.emit("out", user_id=user_id, display_name=display, text=reply, kind="ai")
    await update.reply(reply)
