"""
Shared bot runtime state (thread + active flag).

Kept in its own module so both `main.py` (which owns the bot thread) and
`handlers.py` (which asks "should I respond?") can touch it without
creating a circular import.
"""

import threading

# The asyncio thread that hosts rubpy's message loop.
bot_thread: "threading.Thread | None" = None

# The asyncio loop running inside bot_thread — used to schedule
# thread-safe coroutines (e.g. a clean disconnect).
bot_loop = None

# True while the bot should reply to incoming messages. False = paused.
# Independent of whether the thread is alive.
active: bool = False


def is_running() -> bool:
    return bot_thread is not None and bot_thread.is_alive()
