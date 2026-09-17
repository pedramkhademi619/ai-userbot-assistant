"""
Bridge between rubpy's stdin-based login flow and the Tkinter GUI.

rubpy.Client.start() prompts for phone number / OTP code / password with
plain input(). In our GUI-only app there is no attached terminal, so we
monkey-patch builtins.input inside the bot thread: every prompt is
forwarded to the GUI via the shared event bus, and the bot thread blocks
until the GUI publishes the user's answer.

Usage in the bot thread:

    from bot import auth_bridge
    auth_bridge.install()
    ...  # rubpy will now call our _gui_input for any input()

Usage in the GUI (main) thread:

    # on "prompt" event -> pop up a modal, then:
    auth_bridge.provide_answer(text)
"""

from __future__ import annotations

import builtins
import queue
import threading

from . import events

_lock = threading.Lock()
_answer_queue: "queue.Queue[str]" = queue.Queue()
_original_input = builtins.input
_installed = False


def _gui_input(prompt: str = "") -> str:
    """Replacement for builtins.input, called from the bot thread."""

    events.emit("prompt", prompt=str(prompt))

    while True:
        try:
            return _answer_queue.get(timeout=300)
        except queue.Empty:
            # Refresh the modal in case the user missed it.
            events.emit("prompt", prompt=str(prompt))


def install() -> None:
    """Monkey-patch builtins.input. Idempotent."""

    global _installed
    with _lock:
        if _installed:
            return
        builtins.input = _gui_input
        _installed = True


def uninstall() -> None:
    global _installed
    with _lock:
        if not _installed:
            return
        builtins.input = _original_input
        _installed = False


def provide_answer(answer: str) -> None:
    """Called by the GUI when the user submits a prompt response."""

    _answer_queue.put(answer)


def clear() -> None:
    """Drop any pending answers (called between sessions)."""

    while True:
        try:
            _answer_queue.get_nowait()
        except queue.Empty:
            return


async def async_prompt(prompt: str) -> str:
    """
    Async variant used by libraries that ask for input via an awaitable
    callback (e.g. Telethon's code_callback / password). Emits the same
    "prompt" event and yields until the GUI puts an answer on the queue.

    Uses non-blocking polling with a short sleep instead of
    run_in_executor(queue.get) — the executor path holds a whole
    thread-pool worker hostage on Windows while it waits, which starves
    Telethon's own background tasks and makes the whole GUI feel sluggish.
    """

    import asyncio

    events.emit("prompt", prompt=str(prompt))

    while True:
        try:
            return _answer_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.15)
