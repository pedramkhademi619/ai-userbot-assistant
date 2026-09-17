"""
Tiny publish/subscribe event bus.

It decouples the bot logic (handlers.py, main.py) from any UI that wants to
observe what is happening (e.g. the Tkinter dashboard in gui.py). If nothing
subscribes, emit() is a cheap no-op, so headless/console mode is unaffected.
"""

import queue
import threading

_subscribers = []
_lock = threading.Lock()


def subscribe() -> "queue.Queue":
    """Register a new listener and return its private queue."""

    q = queue.Queue()

    with _lock:
        _subscribers.append(q)

    return q


def unsubscribe(q: "queue.Queue") -> None:
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def emit(event_type: str, **data) -> None:
    """Push an event to every active subscriber (no-op if none)."""

    if not _subscribers:
        return

    payload = {"type": event_type, **data}

    with _lock:
        listeners = list(_subscribers)

    for q in listeners:
        q.put(payload)
