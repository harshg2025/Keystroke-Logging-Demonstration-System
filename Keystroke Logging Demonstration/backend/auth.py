"""
auth.py  –  Password protection & session token management
============================================================
Educational Keystroke Logger Demo – DO NOT USE MALICIOUSLY
"""

import hashlib
import hmac
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Default credentials (change via /api/change-password endpoint)
# ---------------------------------------------------------------------------
_CREDENTIALS_FILE = Path(__file__).parent.parent / "data" / ".creds"
_DEFAULT_PASSWORD  = "demo1234"         # shown in README so users can log in


def _hash_password(password: str) -> str:
    """Return a SHA-256 hex digest of the password (salted with a fixed prefix)."""
    salted = f"keylogger_demo_salt__{password}"
    return hashlib.sha256(salted.encode()).hexdigest()


def _ensure_creds_file() -> None:
    """Create the credentials file with the default password if missing."""
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _CREDENTIALS_FILE.exists():
        _CREDENTIALS_FILE.write_text(_hash_password(_DEFAULT_PASSWORD))


def verify_password(password: str) -> bool:
    """Return True when *password* matches the stored hash."""
    _ensure_creds_file()
    stored_hash = _CREDENTIALS_FILE.read_text().strip()
    candidate    = _hash_password(password)
    return hmac.compare_digest(stored_hash, candidate)


def change_password(old_password: str, new_password: str) -> bool:
    """
    Replace the stored has with a hash of *new_password*.
    Returns True on success, False if *old_password* is wrong.
    """
    if not verify_password(old_password):
        return False
    _CREDENTIALS_FILE.write_text(_hash_password(new_password))
    return True


# ---------------------------------------------------------------------------
# Lightweight session-token store (in-memory, resets on server restart)
# ---------------------------------------------------------------------------
_SESSION_TTL = 3600          # seconds – 1 hour
_active_sessions: dict[str, float] = {}


def create_session(password: str) -> str | None:
    """
    Validate *password* and return a time-limited session token.
    Returns None when credentials are invalid.
    """
    if not verify_password(password):
        return None
    token = hashlib.sha256(f"{password}{time.time()}".encode()).hexdigest()
    _active_sessions[token] = time.time()
    return token


def validate_session(token: str) -> bool:
    """Return True when *token* is present and not expired."""
    created_at = _active_sessions.get(token)
    if created_at is None:
        return False
    if time.time() - created_at > _SESSION_TTL:
        _active_sessions.pop(token, None)
        return False
    return True


def revoke_session(token: str) -> None:
    """Remove *token* from the active-session store (logout)."""
    _active_sessions.pop(token, None)
