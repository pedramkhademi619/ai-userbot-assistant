"""
Shared client instances.

The OpenAI-compatible AI client is always constructed here (both Rubika
and Telegram runtimes talk to it). The Rubika `Client` is instantiated
lazily via `get_rubika_app()` so that importing this module on the
Telegram path (where rubpy would fail with an empty session name) is
still safe.
"""

from openai import AsyncOpenAI

from . import config

openai_client = AsyncOpenAI(
    base_url=config.BASE_URL,
    api_key=config.API_KEY,
    timeout=config.REQUEST_TIMEOUT,
    max_retries=2,
)

_rubika_app = None


def get_rubika_app():
    """Construct (or return the existing) rubpy Client tied to config.RUBIKA_SESSION."""

    global _rubika_app

    if _rubika_app is None:
        from rubpy import Client
        _rubika_app = Client(config.RUBIKA_SESSION or "default")

    return _rubika_app


# Backward-compat: some existing code does `from .clients import app`.
# We keep the name but resolve it lazily via __getattr__ so importing
# `clients` on the Telegram path does not require a session name.
def __getattr__(name):
    if name == "app":
        return get_rubika_app()
    raise AttributeError(name)
