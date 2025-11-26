"""Unit tests for run_qa.py refactored helpers (Task 1.4).

Tests pure functions with mocked dependencies, no actual test execution required.
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock, mock_open

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_qa import (
    _load_qa_config,
    _build_qa_summary,
)


class TestLoadQAConfig:
    """Test _load_qa_config() helper."""

    @patch("builtins.open", new_callable=mock_open, read_data="drivers:\n  enabled: true\nproject:\n  targets:\n    backend: fastapi\n")
    def test_load_qa_config_returns_tuple(self, mock_file):
        """_load_qa_config returns (cfg, drv_cfg, targets) tuple."""
        cfg, drv_cfg, targets = _load_qa_config()
        assert isinstance(cfg, dict)
        assert isinstance(drv_cfg, dict)
        assert isinstance(targets, dict)
        assert drv_cfg.get("enabled") is True
        assert targets.get("backend") == "fastapi"

    @patch("builtins.open", new_callable=mock_open, read_data="project:\n  targets:\n    backend: fastapi\n")
    def test_load_qa_config_handles_missing_drivers(self, mock_file):
        """_load_qa_config safely handles missing drivers section."""
        cfg, drv_cfg, targets = _load_qa_config()
        assert isinstance(cfg, dict)
        assert isinstance(drv_cfg, dict)
        assert drv_cfg.get("enabled") is None

    @patch("builtins.open", side_effect=FileNotFoundError("config.yaml not found"))
    def test_load_qa_config_handles_missing_file(self, mock_file):
        """_load_qa_config safely handles missing config.yaml."""
        cfg, drv_cfg, targets = _load_qa_config()
        assert cfg == {}
        assert drv_cfg == {}
        assert targets == {}

    @patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml: content:")
    def test_load_qa_config_handles_invalid_yaml(self, mock_file):
        """_load_qa_config safely handles invalid YAML."""
        cfg, drv_cfg, targets = _load_qa_config()
        # Should return empty dicts on parse failure
        assert isinstance(cfg, dict)
        assert isinstance(drv_cfg, dict)
        assert isinstance(targets, dict)


class TestBuildQASummary:
    """Test _build_qa_summary() pure helper."""

    def test_build_qa_summary_creates_dict(self):
        """_build_qa_summary returns well-formed summary dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=0,
                run_backend_tests=True,
                run_web_tests=True,
                collection_errors_present=False
            )

            assert qa_summary["version"] == 1
            assert "timestamp" in qa_summary
            assert "areas" in qa_summary
            assert "backend" in qa_summary["areas"]
            assert "web" in qa_summary["areas"]
            assert "embedded" in qa_summary["areas"]

    def test_build_qa_summary_backend_pass(self):
        """_build_qa_summary marks backend as run_pass when rc=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=None,
                run_backend_tests=True,
                run_web_tests=False,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            assert backend["executed"] is True
            assert backend["rc"] == 0
            assert backend["status"] == "run_pass"
            assert backend["reason"] is None

    def test_build_qa_summary_backend_fail(self):
        """_build_qa_summary marks backend as run_fail when rc!=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=1,
                web_rc=None,
                run_backend_tests=True,
                run_web_tests=False,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            assert backend["executed"] is True
            assert backend["rc"] == 1
            assert backend["status"] == "run_fail"
            assert "failed" in backend["reason"]

    def test_build_qa_summary_tool_missing(self):
        """_build_qa_summary marks area as skip_tool_missing when rc=127."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=127,
                web_rc=None,
                run_backend_tests=True,
                run_web_tests=False,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            assert backend["rc"] == 127
            assert backend["status"] == "skip_tool_missing"

    def test_build_qa_summary_collection_errors(self):
        """_build_qa_summary marks areas with error_collection when collection errors present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=1,
                web_rc=None,
                run_backend_tests=True,
                run_web_tests=False,
                collection_errors_present=True  # Collection errors detected
            )

            backend = qa_summary["areas"]["backend"]
            assert backend["rc"] == 4  # Normalized to 4 for collection errors
            assert backend["status"] == "error_collection"

    def test_build_qa_summary_skip_no_tests(self):
        """_build_qa_summary marks area as skip_no_tests when not executed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=0,
                run_backend_tests=False,  # Not executed
                run_web_tests=False,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            assert backend["executed"] is False
            assert backend["status"] == "skip_no_tests"

    def test_build_qa_summary_logs_aggregation(self):
        """_build_qa_summary aggregates log files from story_art_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)
            # Create dummy log files
            (story_art_dir / "backend_fastapi_test.log").write_text("test output")
            (story_art_dir / "frontend_next_js_test.log").write_text("test output")

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=0,
                run_backend_tests=True,
                run_web_tests=True,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            web = qa_summary["areas"]["web"]

            assert len(backend["logs"]) > 0
            assert any("backend_" in log for log in backend["logs"])
            assert len(web["logs"]) > 0
            assert any("frontend_" in log for log in web["logs"])

    def test_build_qa_summary_tools_detection(self):
        """_build_qa_summary detects pytest and jest availability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=0,
                run_backend_tests=True,
                run_web_tests=True,
                collection_errors_present=False
            )

            backend = qa_summary["areas"]["backend"]
            web = qa_summary["areas"]["web"]

            assert "pytest" in backend["tools_present"]
            assert isinstance(backend["tools_present"]["pytest"], bool)
            assert "jest" in web["tools_present"]
            assert isinstance(web["tools_present"]["jest"], bool)


class TestQARefactorIntegration:
    """Integration tests for refactored QA helpers."""

    def test_load_config_and_build_summary_integration(self):
        """Test that config loading and summary building work together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            story_art_dir = Path(tmpdir)

            # Mock config loading
            with patch("builtins.open", new_callable=mock_open, read_data="drivers:\n  enabled: true\n"):
                cfg, drv_cfg, targets = _load_qa_config()

            # Build summary with loaded config
            qa_summary = _build_qa_summary(
                story_art_dir=story_art_dir,
                be_rc=0,
                web_rc=0,
                run_backend_tests=bool(drv_cfg.get("enabled")),
                run_web_tests=bool(drv_cfg.get("enabled")),
                collection_errors_present=False
            )

            assert qa_summary["version"] == 1
            assert "areas" in qa_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
