"""
Application configuration.

Layout:
    * Non-sensitive settings (session name, base URL, model, tuning) live
      in .env — easy to edit, safe to keep in the repo directory.
    * Secrets (API keys, tokens) live in an out-of-repo key/value store
      managed by bot.secrets_store.SecretsStore.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .secrets_store import secrets_store

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


# --------------------------------------------------------------------
# Which keys are treated as secrets (stored in SecretsStore, NOT .env)
# --------------------------------------------------------------------

SECRET_KEYS = {
    "RUBIKA_API_KEY",
    "RUBIKA_PHONE",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_PHONE",
}

# Which chat platform the bot connects to: "rubika" or "telegram".
VALID_PLATFORMS = ("rubika", "telegram")


def get_env(key: str, default=None):
    val = os.getenv(key)
    if val is None or val == "":
        return default
    return val


def _int_env(key: str, default: int) -> int:
    val = get_env(key)
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _load_secret_or_env(key: str, default=None):
    """
    Secret precedence:
      1. SecretsStore    (preferred; encrypted on disk if `cryptography` is available)
      2. Env variable    (kept only as a one-time migration path for old .env files)
    """

    val = secrets_store.get(key)
    if val:
        return val
    return get_env(key, default)


# ============================================================
# Rubika / OpenAI credentials  (may be empty at first launch;
# the GUI setup screen fills them in and calls reload_config())
# ============================================================

PLATFORM = get_env("PLATFORM", "")  # "" until the user picks one in the wizard
API_KEY = _load_secret_or_env("RUBIKA_API_KEY", "")
BASE_URL = get_env("BASE_URL", "https://api.gapgpt.app/v1")
MODEL = get_env("MODEL", "gpt-4o-mini")
RUBIKA_SESSION = get_env("RUBIKA_SESSION", "session")
RUBIKA_PHONE = _load_secret_or_env("RUBIKA_PHONE", "")
TELEGRAM_API_ID = _load_secret_or_env("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = _load_secret_or_env("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = _load_secret_or_env("TELEGRAM_PHONE", "")
TELEGRAM_SESSION = get_env("TELEGRAM_SESSION", "telegram_user")


# ============================================================
# Conversation / rate-limit tuning
# ============================================================

MAX_HISTORY_PAIRS = _int_env("MAX_HISTORY_PAIRS", 3)
MAX_MESSAGE_LENGTH = _int_env("MAX_MESSAGE_LENGTH", 2000)
MAX_OUTPUT_TOKENS = _int_env("MAX_OUTPUT_TOKENS", 250)
REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 30)
RATE_LIMIT_COUNT = _int_env("RATE_LIMIT_COUNT", 5)
RATE_LIMIT_WINDOW = _int_env("RATE_LIMIT_WINDOW", 60)
USER_LOCK_TIMEOUT = _int_env("USER_LOCK_TIMEOUT", 30)


# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT_PATH = BASE_DIR / "system_prompt.txt"

if SYSTEM_PROMPT_PATH.exists():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()
else:
    SYSTEM_PROMPT = ""


def reload_system_prompt() -> str:
    """Re-read system_prompt.txt from disk and refresh the in-memory copy."""

    global SYSTEM_PROMPT

    if not SYSTEM_PROMPT_PATH.exists():
        SYSTEM_PROMPT = ""
        return SYSTEM_PROMPT

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()

    return SYSTEM_PROMPT


def append_to_system_prompt(text: str, label: str = None) -> str:
    """
    Append extra data/instructions to system_prompt.txt (e.g. typed in the
    GUI) and reload it so the very next AI call already uses it.
    """

    text = text.strip()

    if not text:
        return SYSTEM_PROMPT

    header = f"\n\n# {label}\n" if label else "\n\n"

    with open(SYSTEM_PROMPT_PATH, "a", encoding="utf-8") as f:
        f.write(header + text + "\n")

    return reload_system_prompt()


def overwrite_system_prompt(text: str) -> str:
    """Replace the whole system_prompt.txt with `text`."""

    with open(SYSTEM_PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

    return reload_system_prompt()


# ============================================================
# Persistence helpers (used by the GUI's settings panel)
# ============================================================

_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _save_env_only(updates: dict) -> None:
    """Write non-secret updates to .env, preserving comments/order."""

    if not updates:
        return

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    seen = set()
    new_lines = []

    for line in lines:
        match = _ENV_LINE_RE.match(line)
        if match and match.group(1) in updates:
            key = match.group(1)
            val = str(updates[key]).replace('"', '\\"')
            new_lines.append(f'{key} = "{val}"')
            seen.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key in seen:
            continue
        val = str(value).replace('"', '\\"')
        new_lines.append(f'{key} = "{val}"')

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _strip_secrets_from_env() -> None:
    """
    Best-effort migration: if RUBIKA_API_KEY (or any known secret) is still
    sitting in .env from an older run, remove that line — the value is now
    stored in the SecretsStore.
    """

    if not ENV_PATH.exists():
        return

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    filtered = []
    changed = False

    for line in lines:
        match = _ENV_LINE_RE.match(line)
        if match and match.group(1) in SECRET_KEYS:
            changed = True
            continue
        filtered.append(line)

    if changed:
        ENV_PATH.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def save_settings(updates: dict) -> None:
    """
    Persist a mixed dict of settings: secrets go to SecretsStore, everything
    else goes to .env. Keeps the two stores in sync from a single call.
    """

    if not updates:
        return

    env_updates = {}

    for key, value in updates.items():
        if key in SECRET_KEYS:
            if value:
                secrets_store.set(key, str(value))
            else:
                secrets_store.delete(key)
        else:
            env_updates[key] = value

    _save_env_only(env_updates)
    _strip_secrets_from_env()


# Kept for backward-compat with any older caller.
save_env_vars = save_settings


def session_file_path(session_name: str | None = None) -> Path:
    """Where rubpy stores this session's .rp file (project root)."""

    name = session_name or RUBIKA_SESSION or "session"
    return BASE_DIR / f"{name}.rp"


def telegram_session_file_path(session_name: str | None = None) -> Path:
    """Where Telethon stores this session's .session file (project root)."""

    name = session_name or TELEGRAM_SESSION or "telegram_user"
    return BASE_DIR / f"{name}.session"


def is_logged_in() -> bool:
    """
    True when the current platform has everything it needs to run
    (saved session + platform-specific credentials + AI-backend config).
    """

    if not (API_KEY and BASE_URL and MODEL):
        return False

    if PLATFORM == "rubika":
        return bool(
            RUBIKA_SESSION
            and session_file_path(RUBIKA_SESSION).exists()
        )
    if PLATFORM == "telegram":
        return bool(
            TELEGRAM_API_ID
            and TELEGRAM_API_HASH
            and TELEGRAM_SESSION
            and telegram_session_file_path(TELEGRAM_SESSION).exists()
        )

    return False


def logout() -> None:
    """Delete platform session files so the app treats the user as logged out."""

    for path in (
        session_file_path(RUBIKA_SESSION),
        telegram_session_file_path(TELEGRAM_SESSION),
    ):
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


def reload_config() -> None:
    """
    Re-load .env + SecretsStore from disk and refresh every module-level
    setting so the rest of the code sees the newly saved values without a
    process restart.
    """

    global PLATFORM, API_KEY, BASE_URL, MODEL
    global RUBIKA_SESSION, RUBIKA_PHONE
    global TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELEGRAM_SESSION
    global MAX_HISTORY_PAIRS, MAX_MESSAGE_LENGTH, MAX_OUTPUT_TOKENS
    global REQUEST_TIMEOUT, RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW, USER_LOCK_TIMEOUT

    load_dotenv(ENV_PATH, override=True)

    PLATFORM = get_env("PLATFORM", "")
    API_KEY = _load_secret_or_env("RUBIKA_API_KEY", "")
    BASE_URL = get_env("BASE_URL", "https://api.gapgpt.app/v1")
    MODEL = get_env("MODEL", "gpt-4o-mini")
    RUBIKA_SESSION = get_env("RUBIKA_SESSION", "session")
    RUBIKA_PHONE = _load_secret_or_env("RUBIKA_PHONE", "")
    TELEGRAM_API_ID = _load_secret_or_env("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH = _load_secret_or_env("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE = _load_secret_or_env("TELEGRAM_PHONE", "")
    TELEGRAM_SESSION = get_env("TELEGRAM_SESSION", "telegram_user")

    MAX_HISTORY_PAIRS = _int_env("MAX_HISTORY_PAIRS", 3)
    MAX_MESSAGE_LENGTH = _int_env("MAX_MESSAGE_LENGTH", 2000)
    MAX_OUTPUT_TOKENS = _int_env("MAX_OUTPUT_TOKENS", 250)
    REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 30)
    RATE_LIMIT_COUNT = _int_env("RATE_LIMIT_COUNT", 5)
    RATE_LIMIT_WINDOW = _int_env("RATE_LIMIT_WINDOW", 60)
    USER_LOCK_TIMEOUT = _int_env("USER_LOCK_TIMEOUT", 30)
