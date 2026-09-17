r"""
Encrypted key/value store for anything security-sensitive
(API keys, tokens, ...).

Threat model
------------
Someone gets a copy of the DB file (accidentally emailed, backed up to a
cloud drive, ex-employee walks off with the laptop's disk image, ...).
They must NOT be able to read the values.

We keep secrets out of the project directory:

    %USERPROFILE%\.rubika_bot\secrets.db   (Windows)
    ~/.rubika_bot/secrets.db               (Linux/Mac)

And every value is encrypted before it hits sqlite. Two backends, tried in
this order:

1. **Windows DPAPI** (`CryptProtectData` / `CryptUnprotectData`) —
   stdlib-only, no external deps, and the encryption key is derived from
   the current Windows user account by the OS itself. The key never lives
   on disk, so lifting `secrets.db` to another machine (or another Windows
   user on the same machine) yields ciphertext that cannot be decrypted.

2. **Fernet (`cryptography` package)** — cross-platform fallback. The
   symmetric key is stored in `secret.key` next to the DB with 0600 perms.
   Not as strong as DPAPI (whoever grabs both files can decrypt), but
   still far better than plaintext.

If neither is available we refuse to write secrets at all — surfacing the
problem is safer than silently downgrading to base64 obfuscation.

Usage:
    store = SecretsStore()
    store.set("RUBIKA_API_KEY", "sk-...")
    store.get("RUBIKA_API_KEY")
    store.delete("RUBIKA_API_KEY")
    store.all()          # -> dict[str, str]
"""

from __future__ import annotations

import ctypes
import os
import sqlite3
import sys
import threading
from ctypes import wintypes
from pathlib import Path

# ================================================================
# Backend interface
# ================================================================


class _Backend:
    name: str = "none"

    def encrypt(self, data: bytes) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def decrypt(self, data: bytes) -> bytes:  # pragma: no cover
        raise NotImplementedError


# ----------------------------------------------------------------
# Windows DPAPI backend
# ----------------------------------------------------------------


class _Blob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class _DPAPIBackend(_Backend):
    name = "dpapi"

    # Bind values encrypted here to this application to add a small extra
    # hurdle (some other program running as the same user would still need
    # to supply the same entropy to decrypt).
    _ENTROPY = b"rubika-ai-bot/secrets_store/v1"

    def __init__(self):
        self._crypt32 = ctypes.windll.crypt32
        self._kernel32 = ctypes.windll.kernel32

    def _to_blob(self, data: bytes) -> _Blob:
        buf = ctypes.create_string_buffer(data, len(data))
        return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))

    def _from_blob(self, blob: _Blob) -> bytes:
        try:
            return ctypes.string_at(blob.pbData, blob.cbData)
        finally:
            if blob.pbData:
                self._kernel32.LocalFree(blob.pbData)

    def encrypt(self, data: bytes) -> bytes:
        in_blob = self._to_blob(data)
        entropy_blob = self._to_blob(self._ENTROPY)
        out_blob = _Blob()

        ok = self._crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if not ok:
            raise OSError(f"CryptProtectData failed (error {ctypes.get_last_error()})")

        return self._from_blob(out_blob)

    def decrypt(self, data: bytes) -> bytes:
        in_blob = self._to_blob(data)
        entropy_blob = self._to_blob(self._ENTROPY)
        out_blob = _Blob()

        ok = self._crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
        if not ok:
            raise OSError(f"CryptUnprotectData failed (error {ctypes.get_last_error()})")

        return self._from_blob(out_blob)


# ----------------------------------------------------------------
# Fernet fallback (cross-platform, needs `cryptography`)
# ----------------------------------------------------------------


class _FernetBackend(_Backend):
    name = "fernet"

    def __init__(self, key_path: Path):
        from cryptography.fernet import Fernet  # local import so it's optional

        if key_path.exists():
            key = key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass

        self._fernet = Fernet(key)

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)


# ================================================================
# SecretsStore
# ================================================================


def _default_store_dir() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".rubika_bot"


def _pick_backend(key_path: Path) -> _Backend:
    if sys.platform == "win32":
        try:
            return _DPAPIBackend()
        except Exception:
            pass  # fall through

    try:
        return _FernetBackend(key_path)
    except ImportError:
        raise RuntimeError(
            "No encryption backend available. On non-Windows systems, "
            "install `cryptography` (pip install cryptography) so secrets "
            "can be stored safely."
        )


class SecretsStore:
    """SQLite-backed key/value store where every value is encrypted."""

    def __init__(self, directory: Path | None = None):
        self._dir = Path(directory) if directory else _default_store_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

        # Tighten directory perms where the OS supports it.
        try:
            os.chmod(self._dir, 0o700)
        except OSError:
            pass

        self._db_path = self._dir / "secrets.db"
        self._key_path = self._dir / "secret.key"
        self._lock = threading.Lock()

        self._backend = _pick_backend(self._key_path)

        self._init_schema()

    # --------------------------------------------------------------
    # DB helpers
    # --------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS secrets (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
                """
            )

        try:
            os.chmod(self._db_path, 0o600)
        except OSError:
            pass

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------

    def set(self, key: str, value: str) -> None:
        encoded = self._backend.encrypt(value.encode("utf-8"))
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO secrets(key, value, updated_at)
                VALUES(?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (key, encoded),
            )

    def get(self, key: str, default: str | None = None) -> str | None:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT value FROM secrets WHERE key=?", (key,)).fetchone()

        if row is None:
            return default

        try:
            return self._backend.decrypt(row[0]).decode("utf-8")
        except Exception:
            # e.g. DB was copied here from another Windows account and
            # DPAPI refuses to decrypt. Treat as "not available".
            return default

    def delete(self, key: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM secrets WHERE key=?", (key,))

    def all(self) -> dict:
        with self._lock, self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM secrets").fetchall()

        out = {}
        for key, blob in rows:
            try:
                out[key] = self._backend.decrypt(blob).decode("utf-8")
            except Exception:
                continue
        return out

    # --------------------------------------------------------------
    # Introspection
    # --------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._db_path

    @property
    def backend_name(self) -> str:
        return self._backend.name


# Shared instance for the rest of the app.
secrets_store = SecretsStore()
