"""
storage.py  –  Encrypted keystroke log storage + CSV export
=============================================================
Educational Keystroke Logger Demo – DO NOT USE MALICIOUSLY

All data is written to  data/keylog.enc  using Fernet symmetric encryption.
The encryption key is auto-generated on first run and stored in  data/.key
(keep this file secret – without it the log cannot be decrypted).
"""

import csv
import io
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR  = Path(__file__).parent.parent / "data"
_KEY_FILE  = _DATA_DIR / ".key"
_LOG_FILE  = _DATA_DIR / "keylog.enc"


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _load_or_create_key() -> bytes:
    """Load the Fernet key from disk, or generate and save a new one."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    return key


def _fernet() -> Fernet:
    return Fernet(_load_or_create_key())


def _load_records() -> List[Dict[str, Any]]:
    """Decrypt and deserialise all stored keystroke records."""
    if not _LOG_FILE.exists():
        return []
    try:
        ciphertext = _LOG_FILE.read_bytes()
        plaintext  = _fernet().decrypt(ciphertext)
        return json.loads(plaintext.decode())
    except Exception:
        # If decryption fails (e.g., corrupted file) start fresh
        return []


def _save_records(records: List[Dict[str, Any]]) -> None:
    """Serialise and encrypt all records back to disk."""
    plaintext  = json.dumps(records).encode()
    ciphertext = _fernet().encrypt(plaintext)
    _LOG_FILE.write_bytes(ciphertext)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def append_keystroke(record: Dict[str, Any]) -> None:
    """
    Append a single keystroke record to the encrypted log.

    Expected keys in *record*:
        key        – str  – the key label (e.g. "a", "Key.space")
        timestamp  – float – Unix epoch (seconds)
        is_special – bool  – whether it's a special/modifier key
    """
    records = _load_records()
    records.append(record)
    _save_records(records)


def get_all_records() -> List[Dict[str, Any]]:
    """Return all stored keystroke records (decrypted)."""
    return _load_records()


def clear_records() -> None:
    """Delete all stored records (keeps the key file)."""
    _save_records([])


def export_csv() -> str:
    """Return a CSV string of all stored records for download."""
    records = _load_records()
    output  = io.StringIO()
    writer  = csv.DictWriter(
        output,
        fieldnames=["timestamp", "key", "is_special", "datetime"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for rec in records:
        rec["datetime"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(rec.get("timestamp", 0))
        )
        writer.writerow(rec)
    return output.getvalue()


def get_stats() -> Dict[str, Any]:
    """
    Compute quick statistics over all stored records.

    Returns:
        total        – int   – total keystrokes stored
        key_freq     – dict  – {key: count}
        session_mins – float – approximate session duration in minutes
        kpm          – float – keystrokes per minute (over full session window)
    """
    records = _load_records()
    if not records:
        return {"total": 0, "key_freq": {}, "session_mins": 0.0, "kpm": 0.0}

    key_freq: Dict[str, int] = {}
    for rec in records:
        k = rec.get("key", "?")
        key_freq[k] = key_freq.get(k, 0) + 1

    timestamps = [r["timestamp"] for r in records if "timestamp" in r]
    if len(timestamps) > 1:
        session_secs = max(timestamps) - min(timestamps)
        session_mins = session_secs / 60
        kpm = len(records) / session_mins if session_mins > 0 else 0.0
    else:
        session_mins = 0.0
        kpm = 0.0

    return {
        "total":        len(records),
        "key_freq":     key_freq,
        "session_mins": round(session_mins, 2),
        "kpm":          round(kpm, 2),
    }
