"""Unit tests for drivers/detect.py (Task 1.6 - exception handling coverage)."""

from __future__ import annotations

import pytest

from drivers.detect import _probe, has_idf, has_west


class TestProbeFunction:
    """Test _probe helper with various scenarios."""

    def test_probe_command_not_found(self, monkeypatch):
        """Line 16-17: _probe handles command not in PATH."""
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        found, msg = _probe("nonexistent_cmd")
        assert not found
        assert "not found in PATH" in msg

    def test_probe_command_found_success(self, monkeypatch):
        """_probe returns version info when command succeeds."""
        class MockResult:
            returncode = 0
            stdout = "version 1.2.3"
            stderr = ""

        monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
        monkeypatch.setattr("subprocess.run", lambda *a, **k: MockResult())

        found, msg = _probe("some_tool")
        assert found
        assert "/usr/bin/some_tool" in msg
        assert "version 1.2.3" in msg

    def test_probe_subprocess_timeout_exception(self, monkeypatch):
        """Line 16-17: _probe handles subprocess timeout/exception gracefully."""
        import subprocess

        def raise_timeout(*a, **k):
            raise subprocess.TimeoutExpired("cmd", 5)

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/tool")
        monkeypatch.setattr("subprocess.run", raise_timeout)

        found, msg = _probe("tool")
        # Should still return True (found) but with failure message
        assert found
        assert "/usr/bin/tool" in msg
        assert "version probe failed" in msg

    def test_probe_generic_exception(self, monkeypatch):
        """Line 16-17: _probe handles generic exception."""

        def raise_error(*a, **k):
            raise RuntimeError("unexpected error")

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/tool")
        monkeypatch.setattr("subprocess.run", raise_error)

        found, msg = _probe("tool")
        assert found
        assert "/usr/bin/tool" in msg
        assert "version probe failed" in msg
        assert "unexpected error" in msg

    def test_probe_version_stderr_fallback(self, monkeypatch):
        """_probe uses stderr if stdout is empty."""
        class MockResult:
            returncode = 0
            stdout = ""
            stderr = "version info from stderr"

        monkeypatch.setattr("shutil.which", lambda cmd: f"/bin/{cmd}")
        monkeypatch.setattr("subprocess.run", lambda *a, **k: MockResult())

        found, msg = _probe("cmd")
        assert found
        assert "version info from stderr" in msg

    def test_probe_no_version_output(self, monkeypatch):
        """_probe handles case where --version produces no output."""
        class MockResult:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr("shutil.which", lambda cmd: f"/bin/{cmd}")
        monkeypatch.setattr("subprocess.run", lambda *a, **k: MockResult())

        found, msg = _probe("cmd")
        assert found
        assert "(no version output)" in msg


class TestHasIDFAndWest:
    """Test has_idf and has_west detector wrappers."""

    def test_has_idf_not_found(self, monkeypatch):
        """has_idf returns False when idf.py not in PATH."""
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        found, msg = has_idf()
        assert not found
        assert "idf.py not found in PATH" in msg

    def test_has_idf_found(self, monkeypatch):
        """has_idf returns True when idf.py is in PATH."""
        class MockResult:
            returncode = 0
            stdout = "ESP-IDF v5.1"
            stderr = ""

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/local/bin/idf.py")
        monkeypatch.setattr("subprocess.run", lambda *a, **k: MockResult())

        found, msg = has_idf()
        assert found
        assert "idf.py" in msg
        assert "ESP-IDF v5.1" in msg

    def test_has_west_not_found(self, monkeypatch):
        """has_west returns False when west not in PATH."""
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        found, msg = has_west()
        assert not found
        assert "west not found in PATH" in msg

    def test_has_west_found(self, monkeypatch):
        """has_west returns True when west is in PATH."""
        class MockResult:
            returncode = 0
            stdout = "Zephyr version 3.5"
            stderr = ""

        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/west")
        monkeypatch.setattr("subprocess.run", lambda *a, **k: MockResult())

        found, msg = has_west()
        assert found
        assert "west" in msg
        assert "Zephyr version 3.5" in msg
