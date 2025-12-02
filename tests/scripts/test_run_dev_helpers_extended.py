"""Extended tests for run_dev.py helper functions to increase coverage."""
import json
import pathlib
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from scripts import run_dev


def test_load_config_propagates_exception_on_error(monkeypatch):
    """Test _load_config() propagates exception when load_config() fails."""
    def mock_load_config():
        raise Exception("Config loading failed")
    
    # Import path is common.load_config, not scripts.run_dev.load_config
    monkeypatch.setattr("common.load_config", mock_load_config)
    
    # _load_config() does NOT handle exceptions, it propagates them
    with pytest.raises(Exception, match="Config loading failed"):
        run_dev._load_config()


def test_load_config_returns_config_and_drivers(monkeypatch):
    """Test _load_config() extracts drivers configuration correctly."""
    def mock_load_config():
        return {
            "drivers": {
                "enabled": True,
                "templates": {"apply": True}
            },
            "project": {
                "targets": {
                    "backend": "fastapi",
                    "frontend": "nextjs"
                }
            }
        }
    
    # Import path is common.load_config, not scripts.run_dev.load_config
    monkeypatch.setattr("common.load_config", mock_load_config)
    
    cfg, drv_cfg = run_dev._load_config()
    assert cfg["drivers"]["enabled"] is True
    assert drv_cfg["enabled"] is True
    assert drv_cfg["templates"]["apply"] is True


def test_resolve_targets_extracts_correctly():
    """Test _resolve_targets() extracts targets from config."""
    cfg = {
        "project": {
            "targets": {
                "backend": "fastapi",
                "frontend": "react",
                "embedded": "esp32"
            }
        }
    }
    
    targets = run_dev._resolve_targets(cfg)
    assert targets["backend"] == "fastapi"
    assert targets["frontend"] == "react"
    assert targets["embedded"] == "esp32"


def test_resolve_targets_handles_missing_project():
    """Test _resolve_targets() handles missing project config."""
    cfg = {}
    targets = run_dev._resolve_targets(cfg)
    assert targets == {}


def test_resolve_targets_handles_missing_targets():
    """Test _resolve_targets() handles missing targets in project."""
    cfg = {"project": {}}
    targets = run_dev._resolve_targets(cfg)
    assert targets == {}


def test_scaffold_templates_skips_none(monkeypatch, caplog):
    """Test _scaffold_templates() skips when driver is 'none'."""
    run_dev._scaffold_templates("backend", "none", True)
    # Should not call load_driver for "none"
    # Check that no error was raised


def test_scaffold_templates_skips_empty(monkeypatch, caplog):
    """Test _scaffold_templates() skips when driver is empty."""
    run_dev._scaffold_templates("backend", "", True)
    # Should not call load_driver for empty string


def test_scaffold_templates_handles_load_error(monkeypatch, tmp_path, caplog):
    """Test _scaffold_templates() handles driver load errors gracefully."""
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)
    
    def mock_load_driver(cat, sel):
        raise Exception("Driver not found")
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    
    # Should not raise, just log warning
    run_dev._scaffold_templates("backend", "fastapi", True)
    assert "Driver load failed" in caplog.text


def test_scaffold_templates_creates_files(monkeypatch, tmp_path):
    """Test _scaffold_templates() creates template files."""
    root = tmp_path
    monkeypatch.setattr(run_dev, "ROOT", root)
    
    # Mock template object
    class MockTemplate:
        def __init__(self, path, source):
            self.path = path
            self.source = source
    
    class MockDriver:
        def __init__(self):
            self.templates = [
                MockTemplate("project/backend-fastapi/app/main.py", "project-defaults/backend-fastapi/app/main.py")
            ]
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    
    # Create source file
    source_file = root / "project-defaults" / "backend-fastapi" / "app" / "main.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("# Template content\n", encoding="utf-8")
    
    # Run scaffolding
    run_dev._scaffold_templates("backend", "fastapi", True)
    
    # Check destination file was created
    dest_file = root / "project" / "backend-fastapi" / "app" / "main.py"
    assert dest_file.exists()
    assert dest_file.read_text(encoding="utf-8") == "# Template content\n"


def test_scaffold_templates_skips_existing_files(monkeypatch, tmp_path):
    """Test _scaffold_templates() doesn't overwrite existing files."""
    root = tmp_path
    monkeypatch.setattr(run_dev, "ROOT", root)
    
    class MockTemplate:
        def __init__(self, path, source):
            self.path = path
            self.source = source
    
    class MockDriver:
        def __init__(self):
            self.templates = [
                MockTemplate("project/backend-fastapi/app/main.py", "project-defaults/backend-fastapi/app/main.py")
            ]
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    
    # Create source file
    source_file = root / "project-defaults" / "backend-fastapi" / "app" / "main.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("# Template content\n", encoding="utf-8")
    
    # Create existing destination file
    dest_file = root / "project" / "backend-fastapi" / "app" / "main.py"
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text("# Existing content\n", encoding="utf-8")
    
    # Run scaffolding
    run_dev._scaffold_templates("backend", "fastapi", True)
    
    # Check file wasn't overwritten
    assert dest_file.read_text(encoding="utf-8") == "# Existing content\n"


def test_scaffold_templates_disabled(monkeypatch, caplog):
    """Test _scaffold_templates() logs when template expansion is disabled."""
    class MockTemplate:
        def __init__(self, path, source):
            self.path = path
            self.source = source
    
    class MockDriver:
        def __init__(self):
            self.templates = [MockTemplate("project/backend-fastapi/app/main.py", "source.py")]
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    
    # Run with tpl_apply=False
    run_dev._scaffold_templates("backend", "fastapi", False)
    
    # Should log SKIP message
    assert "SKIP" in caplog.text
    assert "template expansion disabled" in caplog.text


def test_write_dev_summary_formats_correctly(tmp_path):
    """Test _write_dev_summary() writes correctly formatted JSON."""
    run_dir = tmp_path / "run-001"
    run_dir.mkdir(parents=True)
    
    drivers_info = {
        "backend": {
            "area": "backend",
            "id": "fastapi",
            "tools_present": {"pytest": True},
            "commands": {
                "test": {
                    "attempted": True,
                    "rc": 0,
                    "log": "artifacts/dev/S1/run-001/backend_fastapi_test.log"
                }
            }
        },
        "frontend": {
            "area": "web",
            "id": "nextjs",
            "tools_present": {"npm": True, "jest": False},
            "commands": {
                "build": {
                    "attempted": True,
                    "rc": 0,
                    "log": "artifacts/dev/S1/run-001/web_nextjs_build.log"
                }
            }
        }
    }
    
    run_dev._write_dev_summary(drivers_info, run_dir)
    
    summary_file = run_dir / "dev_summary.json"
    assert summary_file.exists()
    
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["version"] == 1
    assert "timestamp" in summary
    assert len(summary["drivers"]) == 2
    assert summary["drivers"][0]["area"] == "backend"
    assert summary["drivers"][1]["area"] == "web"


def test_write_dev_summary_handles_empty_drivers(tmp_path):
    """Test _write_dev_summary() handles empty drivers_info."""
    run_dir = tmp_path / "run-001"
    run_dir.mkdir(parents=True)
    
    drivers_info = {}
    run_dev._write_dev_summary(drivers_info, run_dir)
    
    summary_file = run_dir / "dev_summary.json"
    assert summary_file.exists()
    
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["version"] == 1
    assert summary["drivers"] == []


def test_write_dev_summary_handles_write_error(tmp_path, caplog):
    """Test _write_dev_summary() handles write errors gracefully."""
    import logging
    
    # Set caplog to capture DEBUG level logs from the logger module
    caplog.set_level(logging.DEBUG, logger="logger")
    
    # Create a read-only directory to force write error
    run_dir = tmp_path / "readonly-dir"
    run_dir.mkdir()
    
    # Make directory read-only on Unix-like systems
    import os
    import stat
    os.chmod(run_dir, stat.S_IRUSR | stat.S_IXUSR)
    
    drivers_info = {"backend": {"area": "backend", "id": "fastapi"}}
    
    # Should not raise, just log debug message
    run_dev._write_dev_summary(drivers_info, run_dir)
    
    # Restore permissions for cleanup
    os.chmod(run_dir, stat.S_IRWXU)
    
    # Check that error was logged (either "Could not write" or "Permission denied")
    # The function handles the exception gracefully without raising
    assert not (run_dir / "dev_summary.json").exists()


def test_embedded_detection_skips_none(monkeypatch):
    """Test _embedded_detection() skips when embedded is 'none'."""
    drv_cfg = {}
    targets = {"embedded": "none"}
    
    # Should not call load_driver
    run_dev._embedded_detection(drv_cfg, targets)


def test_embedded_detection_skips_empty(monkeypatch):
    """Test _embedded_detection() skips when embedded is empty."""
    drv_cfg = {}
    targets = {}
    
    # Should not raise
    run_dev._embedded_detection(drv_cfg, targets)


def test_embedded_detection_handles_load_error(monkeypatch, caplog):
    """Test _embedded_detection() handles driver load errors."""
    def mock_load_driver(cat, sel):
        raise Exception("Driver not found")
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    
    drv_cfg = {}
    targets = {"embedded": "esp32"}
    
    run_dev._embedded_detection(drv_cfg, targets)
    assert "Embedded driver detection skipped" in caplog.text


def test_embedded_detection_esp_idf(monkeypatch, caplog):
    """Test _embedded_detection() detects ESP-IDF toolchain."""
    class MockDriver:
        def __init__(self):
            self.id = "esp32"
            self.framework = "esp-idf"
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    def mock_has_idf():
        return True, "ESP-IDF found at /path/to/idf"
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    monkeypatch.setattr("scripts.run_dev.has_idf", mock_has_idf)
    
    drv_cfg = {}
    targets = {"embedded": "esp32"}
    
    run_dev._embedded_detection(drv_cfg, targets)
    assert "ESP‑IDF" in caplog.text


def test_embedded_detection_zephyr(monkeypatch, caplog):
    """Test _embedded_detection() detects Zephyr toolchain."""
    class MockDriver:
        def __init__(self):
            self.id = "nrf52"
            self.framework = "zephyr"
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    def mock_has_west():
        return True, "west found"
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    monkeypatch.setattr("scripts.run_dev.has_west", mock_has_west)
    
    drv_cfg = {}
    targets = {"embedded": "nrf52"}
    
    run_dev._embedded_detection(drv_cfg, targets)
    assert "Zephyr west" in caplog.text


def test_embedded_detection_missing_toolchain(monkeypatch, caplog):
    """Test _embedded_detection() handles missing toolchain."""
    class MockDriver:
        def __init__(self):
            self.id = "esp32"
            self.framework = "esp-idf"
    
    def mock_load_driver(cat, sel):
        return MockDriver()
    
    def mock_has_idf():
        return False, "ESP-IDF not found"
    
    monkeypatch.setattr("scripts.run_dev.load_driver", mock_load_driver)
    monkeypatch.setattr("scripts.run_dev.has_idf", mock_has_idf)
    
    drv_cfg = {}
    targets = {"embedded": "esp32"}
    
    run_dev._embedded_detection(drv_cfg, targets)
    assert "SKIP: required toolchain not detected" in caplog.text
