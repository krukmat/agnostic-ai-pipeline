"""Unit tests for run_dev.py refactored helpers (Task 1.3).

Tests pure functions with mocked dependencies, no LLM/file I/O required.
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_dev import (
    _load_config,
    _resolve_targets,
    _scaffold_templates,
    _embedded_detection,
    _write_dev_summary,
)


class TestLoadConfig:
    """Test _load_config() helper."""

    @patch("common.load_config")
    def test_load_config_returns_tuple(self, mock_load):
        """_load_config returns (cfg, drv_cfg) tuple."""
        mock_load.return_value = {
            "drivers": {"enabled": True},
            "project": {"targets": {"backend": "fastapi"}},
        }
        cfg, drv_cfg = _load_config()
        assert isinstance(cfg, dict)
        assert isinstance(drv_cfg, dict)
        assert drv_cfg.get("enabled") is True

    @patch("common.load_config")
    def test_load_config_handles_missing_drivers(self, mock_load):
        """_load_config safely handles missing drivers section."""
        mock_load.return_value = {"project": {"targets": {}}}
        cfg, drv_cfg = _load_config()
        assert isinstance(cfg, dict)
        assert isinstance(drv_cfg, dict)
        assert drv_cfg.get("enabled") is None


class TestResolveTargets:
    """Test _resolve_targets() helper."""

    def test_resolve_targets_extracts_dict(self):
        """_resolve_targets returns targets dict from config."""
        cfg = {
            "project": {
                "targets": {"backend": "fastapi", "frontend": "next_js"}
            }
        }
        targets = _resolve_targets(cfg)
        assert targets == {"backend": "fastapi", "frontend": "next_js"}

    def test_resolve_targets_handles_missing_project(self):
        """_resolve_targets safely handles missing project section."""
        cfg = {}
        targets = _resolve_targets(cfg)
        assert targets == {}

    def test_resolve_targets_handles_missing_targets(self):
        """_resolve_targets safely handles missing targets."""
        cfg = {"project": {}}
        targets = _resolve_targets(cfg)
        assert targets == {}


class TestScaffoldTemplates:
    """Test _scaffold_templates() helper."""

    @patch("scripts.run_dev.load_driver")
    @patch("scripts.run_dev.logger")
    def test_scaffold_templates_skips_none_driver(self, mock_logger, mock_load):
        """_scaffold_templates skips when sel is 'none'."""
        _scaffold_templates("backend", "none", True)
        mock_load.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch("scripts.run_dev.load_driver")
    @patch("scripts.run_dev.logger")
    def test_scaffold_templates_skips_empty_driver(self, mock_logger, mock_load):
        """_scaffold_templates skips when sel is empty."""
        _scaffold_templates("backend", "", True)
        mock_load.assert_not_called()

    @patch("scripts.run_dev.logger")
    def test_scaffold_templates_disabled_logs_skip(self, mock_logger):
        """_scaffold_templates logs SKIP when tpl_apply is False."""
        _scaffold_templates("backend", "fastapi", False)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "SKIP" in call_args

    @patch("scripts.run_dev.load_driver")
    @patch("scripts.run_dev.logger")
    def test_scaffold_templates_load_error_logged(self, mock_logger, mock_load):
        """_scaffold_templates logs warning on load error."""
        mock_load.side_effect = Exception("Load failed")
        _scaffold_templates("backend", "fastapi", True)
        mock_logger.warning.assert_called_once()


class TestEmbeddedDetection:
    """Test _embedded_detection() helper."""

    @patch("scripts.run_dev.load_driver")
    def test_embedded_detection_skips_none(self, mock_load):
        """_embedded_detection skips when embedded is 'none'."""
        drv_cfg = {}
        targets = {"embedded": "none"}
        _embedded_detection(drv_cfg, targets)
        mock_load.assert_not_called()

    @patch("scripts.run_dev.load_driver")
    def test_embedded_detection_skips_missing(self, mock_load):
        """_embedded_detection skips when embedded target not set."""
        drv_cfg = {}
        targets = {}
        _embedded_detection(drv_cfg, targets)
        mock_load.assert_not_called()

    @patch("scripts.run_dev.has_idf")
    @patch("scripts.run_dev.load_driver")
    @patch("scripts.run_dev.logger")
    def test_embedded_detection_esp_idf_found(self, mock_logger, mock_load, mock_idf):
        """_embedded_detection detects ESP-IDF and logs result."""
        # Mock embedded driver
        mock_drv = MagicMock()
        mock_drv.framework = "esp-idf"
        mock_drv.id = "esp32c3_riscv"
        mock_load.return_value = mock_drv

        # Mock idf detection
        mock_idf.return_value = (True, "idf.py found")

        drv_cfg = {"embedded": {"run_build": False, "run_test": False}}
        targets = {"embedded": "esp32c3_riscv"}

        _embedded_detection(drv_cfg, targets)

        # Verify logger was called
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("ESP‑IDF" in call for call in info_calls)


class TestWriteDevSummary:
    """Test _write_dev_summary() pure helper."""

    def test_write_dev_summary_creates_file(self):
        """_write_dev_summary writes dev_summary.json to run_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            drivers_info = {
                "backend": {
                    "area": "backend",
                    "id": "fastapi",
                    "tools_present": {"pytest": True},
                    "commands": {"test": {"attempted": True, "rc": 0}},
                }
            }

            _write_dev_summary(drivers_info, run_dir)

            # Verify file was created
            summary_file = run_dir / "dev_summary.json"
            assert summary_file.exists()

            # Verify content
            import json
            content = json.loads(summary_file.read_text())
            assert content["version"] == 1
            assert len(content["drivers"]) == 1
            assert content["drivers"][0]["id"] == "fastapi"

    def test_write_dev_summary_with_multiple_areas(self):
        """_write_dev_summary aggregates multiple driver areas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            drivers_info = {
                "backend": {
                    "area": "backend",
                    "id": "fastapi",
                    "tools_present": {},
                    "commands": {},
                },
                "frontend": {
                    "area": "web",
                    "id": "next_js",
                    "tools_present": {},
                    "commands": {},
                },
            }

            _write_dev_summary(drivers_info, run_dir)

            import json
            summary_file = run_dir / "dev_summary.json"
            content = json.loads(summary_file.read_text())
            assert len(content["drivers"]) == 2

    def test_write_dev_summary_handles_missing_areas(self):
        """_write_dev_summary skips missing driver areas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            drivers_info = {}

            _write_dev_summary(drivers_info, run_dir)

            import json
            summary_file = run_dir / "dev_summary.json"
            content = json.loads(summary_file.read_text())
            assert content["drivers"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
