"""
tests/test_demo.py  –  Unit and integration tests
===================================================
Educational Keystroke Logger Demo

Run with:
    cd "Keystroke Logging Demonstration"
    python -m pytest tests/test_demo.py -v
"""

import sys
import os
import time
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Make backend importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# =========================================================
# 1. Auth module tests
# =========================================================
class TestAuth:
    """Tests for auth.py — password hashing + session management."""

    def setup_method(self):
        """Use a temp dir so tests don't touch the real data folder."""
        self.tmp = tempfile.mkdtemp()
        import auth
        auth._CREDENTIALS_FILE = Path(self.tmp) / ".creds"
        self._auth = auth

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_password_works(self):
        """Default password 'demo1234' should authenticate successfully."""
        assert self._auth.verify_password("demo1234") is True

    def test_wrong_password_rejected(self):
        """Wrong password must never authenticate."""
        assert self._auth.verify_password("wrongpass") is False

    def test_empty_password_rejected(self):
        assert self._auth.verify_password("") is False

    def test_change_password(self):
        """Password change with correct old password should succeed."""
        result = self._auth.change_password("demo1234", "newSecure99")
        assert result is True
        assert self._auth.verify_password("newSecure99") is True
        assert self._auth.verify_password("demo1234") is False

    def test_change_password_wrong_old(self):
        """Password change with wrong old password must fail."""
        result = self._auth.change_password("wrongold", "newpass")
        assert result is False

    def test_session_create_and_validate(self):
        """A valid session token should validate correctly."""
        token = self._auth.create_session("demo1234")
        assert token is not None
        assert self._auth.validate_session(token) is True

    def test_invalid_session_rejected(self):
        assert self._auth.validate_session("not-a-real-token") is False

    def test_session_revoke(self):
        """Revoked tokens must no longer validate."""
        token = self._auth.create_session("demo1234")
        self._auth.revoke_session(token)
        assert self._auth.validate_session(token) is False

    def test_bad_password_no_session(self):
        """Wrong password must not produce a session token."""
        token = self._auth.create_session("badpassword")
        assert token is None


# =========================================================
# 2. Storage module tests
# =========================================================
class TestStorage:
    """Tests for storage.py — encrypted persistence."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        import storage
        storage._DATA_DIR = Path(self.tmp)
        storage._KEY_FILE  = Path(self.tmp) / ".key"
        storage._LOG_FILE  = Path(self.tmp) / "keylog.enc"
        self._storage = storage

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_record(self, key="a", special=False):
        return {"key": key, "timestamp": time.time(), "is_special": special}

    def test_starts_empty(self):
        records = self._storage.get_all_records()
        assert records == []

    def test_append_and_retrieve(self):
        self._storage.append_keystroke(self._make_record("x"))
        records = self._storage.get_all_records()
        assert len(records) == 1
        assert records[0]["key"] == "x"

    def test_multiple_records_preserved(self):
        for ch in ["h", "e", "l", "l", "o"]:
            self._storage.append_keystroke(self._make_record(ch))
        records = self._storage.get_all_records()
        assert len(records) == 5

    def test_encryption_is_opaque(self):
        """The .enc file should not contain plaintext key values."""
        self._storage.append_keystroke(self._make_record("mysecretkey"))
        raw = (Path(self.tmp) / "keylog.enc").read_bytes()
        assert b"mysecretkey" not in raw

    def test_clear_records(self):
        self._storage.append_keystroke(self._make_record("z"))
        self._storage.clear_records()
        assert self._storage.get_all_records() == []

    def test_stats_total_count(self):
        for _ in range(10):
            self._storage.append_keystroke(self._make_record())
        stats = self._storage.get_stats()
        assert stats["total"] == 10

    def test_stats_key_frequency(self):
        for ch in ["a", "a", "b"]:
            self._storage.append_keystroke(self._make_record(ch))
        stats = self._storage.get_stats()
        assert stats["key_freq"]["a"] == 2
        assert stats["key_freq"]["b"] == 1

    def test_csv_export_format(self):
        self._storage.append_keystroke(self._make_record("q"))
        csv_out = self._storage.export_csv()
        assert "timestamp" in csv_out
        assert "key" in csv_out
        assert "q" in csv_out

    def test_csv_header_columns(self):
        csv_out = self._storage.export_csv()
        first_line = csv_out.strip().split("\n")[0]
        for col in ["timestamp", "key", "is_special", "datetime"]:
            assert col in first_line


# =========================================================
# 3. Analysis module tests
# =========================================================
class TestAnalysis:
    """Tests for analysis.py — statistics and chart generation."""

    def setup_method(self):
        import analysis
        self._analysis = analysis

    def _make_records(self, keys, base_ts=None):
        base_ts = base_ts or time.time()
        return [
            {"key": k, "timestamp": base_ts + i * 0.5, "is_special": k.startswith("[")}
            for i, k in enumerate(keys)
        ]

    def test_top_keys_empty(self):
        result = self._analysis.top_keys([])
        assert result == []

    def test_top_keys_ordered(self):
        records = self._make_records(["a", "a", "a", "b", "b", "c"])
        tops = self._analysis.top_keys(records, n=3)
        assert tops[0][0] == "a"
        assert tops[0][1] == 3
        assert tops[1][1] == 2

    def test_top_keys_limit(self):
        records = self._make_records(list("abcdefghijklmnopqrst"))
        tops = self._analysis.top_keys(records, n=5)
        assert len(tops) == 5

    def test_kpm_over_time_empty(self):
        labels, values = self._analysis.compute_kpm_over_time([])
        assert labels == []
        assert values == []

    def test_kpm_over_time_returns_lists(self):
        records = self._make_records(["a"] * 20, base_ts=1_700_000_000)
        labels, values = self._analysis.compute_kpm_over_time(records, bucket_secs=5)
        assert isinstance(labels, list)
        assert isinstance(values, list)
        assert len(labels) > 0

    def test_bar_chart_returns_base64(self):
        records = self._make_records(["a", "b", "a", "c"])
        b64 = self._analysis.generate_bar_chart(records)
        assert isinstance(b64, str)
        assert len(b64) > 100          # non-trivial base64 string

    def test_pie_chart_returns_base64(self):
        records = self._make_records(["a", "[SPACE]", "b"])
        b64 = self._analysis.generate_pie_chart(records)
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_kpm_chart_returns_base64(self):
        records = self._make_records(["x"] * 30, base_ts=1_700_000_000)
        b64 = self._analysis.generate_kpm_chart(records)
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_generate_all_charts_keys(self):
        records = self._make_records(["a", "[ENTER]", "b"])
        result = self._analysis.generate_all_charts(records)
        assert "bar" in result
        assert "kpm" in result
        assert "pie" in result


# =========================================================
# 4. Logger module tests (mocked pynput)
# =========================================================
class TestLogger:
    """Tests for logger.py – without actually hooking the OS keyboard."""

    def setup_method(self):
        # Patch pynput.keyboard.Listener so no real OS hooks are set
        self.listener_patch = patch("pynput.keyboard.Listener")
        self.mock_listener_cls = self.listener_patch.start()
        self.mock_listener = MagicMock()
        self.mock_listener_cls.return_value = self.mock_listener

        from logger import KeystrokeLogger
        self.Logger = KeystrokeLogger

    def teardown_method(self):
        self.listener_patch.stop()

    def test_starts_stopped(self):
        logger = self.Logger(persist=False)
        assert logger.is_running is False

    def test_starts_after_start(self):
        logger = self.Logger(persist=False)
        logger.start()
        assert logger.is_running is True
        logger.stop()

    def test_stops_after_stop(self):
        logger = self.Logger(persist=False)
        logger.start()
        logger.stop()
        assert logger.is_running is False

    def test_reset_clears_buffer(self):
        logger = self.Logger(persist=False)
        logger.start()
        # Manually inject a fake record into the buffer
        logger._buffer.append({"key": "a", "timestamp": time.time(), "is_special": False})
        logger.total_count = 1
        logger.reset()
        assert logger.get_buffer() == []
        assert logger.total_count == 0
        assert logger.is_running is False

    def test_kpm_zero_when_not_running(self):
        logger = self.Logger(persist=False)
        assert logger.kpm == 0.0

    def test_double_start_is_safe(self):
        """Calling start() twice must not crash or create duplicate listeners."""
        logger = self.Logger(persist=False)
        logger.start()
        logger.start()      # should be a no-op
        assert self.mock_listener_cls.call_count == 1
        logger.stop()

    def test_stop_without_start_is_safe(self):
        logger = self.Logger(persist=False)
        logger.stop()       # must not raise
        assert logger.is_running is False


# =========================================================
# 5. Integration smoke-test (no actual server)
# =========================================================
class TestIntegration:
    """Lightweight integration: auth → storage → analysis pipeline."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        import auth, storage, analysis
        auth._CREDENTIALS_FILE = Path(self.tmp) / ".creds"
        storage._DATA_DIR      = Path(self.tmp)
        storage._KEY_FILE      = Path(self.tmp) / ".key"
        storage._LOG_FILE      = Path(self.tmp) / "keylog.enc"
        self._auth    = auth
        self._storage = storage
        self._analysis = analysis

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_pipeline(self):
        """Auth → store keystrokes → generate stats → generate charts."""
        # 1. Authenticate
        token = self._auth.create_session("demo1234")
        assert token is not None

        # 2. Store some keystrokes
        base = time.time()
        for i, ch in enumerate("Hello World"):
            self._storage.append_keystroke({
                "key":        ch if ch != " " else "[SPACE]",
                "timestamp":  base + i * 0.3,
                "is_special": ch == " ",
            })

        # 3. Check stats
        stats = self._storage.get_stats()
        assert stats["total"] == 11
        assert "H" in stats["key_freq"]

        # 4. Generate charts (just check they return strings)
        records = self._storage.get_all_records()
        charts  = self._analysis.generate_all_charts(records)
        assert all(isinstance(v, str) and len(v) > 10 for v in charts.values() if v)

        # 5. CSV export
        csv = self._storage.export_csv()
        assert "H" in csv

        # 6. Revoke session
        self._auth.revoke_session(token)
        assert self._auth.validate_session(token) is False
