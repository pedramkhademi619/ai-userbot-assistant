"""In-memory state: conversation history, rate limiting, locks and cache."""

import asyncio
import time
from collections import defaultdict, deque

from . import config

# ============================================================
# Conversation Memory
# ============================================================

# deque is preferred over list since it caps itself (maxlen).
chat_history = defaultdict(lambda: deque(maxlen=config.MAX_HISTORY_PAIRS * 2))


# ============================================================
# Rate Limiting
# ============================================================

user_requests = defaultdict(deque)


def is_rate_limited(user_id: str) -> bool:
    """
    Simple sliding-window rate limiter.
    """

    now = time.monotonic()
    requests = user_requests[user_id]

    # Drop requests that have aged out of the window.
    while requests and now - requests[0] > config.RATE_LIMIT_WINDOW:
        requests.popleft()

    if len(requests) >= config.RATE_LIMIT_COUNT:
        return True

    requests.append(now)

    return False


# ============================================================
# User Locks
# ============================================================

user_locks = defaultdict(asyncio.Lock)


# ============================================================
# Simple Response Cache
# ============================================================

# Keyed by the exact (normalized) message text, for fully duplicate messages.
response_cache = {}


def get_cached_response(text: str):
    return response_cache.get(text.strip().lower())


def cache_response(text: str, response: str):
    # Keep the cache small.
    if len(response_cache) >= 100:
        response_cache.pop(next(iter(response_cache)))

    response_cache[text.strip().lower()] = response
