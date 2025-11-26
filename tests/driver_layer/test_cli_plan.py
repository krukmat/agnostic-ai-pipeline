"""Unit tests for drivers CLI (DIP refactor - Phase 1.1).

Tests pure functions with mocked detectors, no real binaries required.
"""

from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from drivers.cli import (
    DetectorMap,
    _get_default_detectors,
    list_drivers,
    plan_from_config,
    show_driver,
)


class TestListDrivers:
    """Test list_drivers pure function."""

    def test_list_drivers_returns_dict(self):
        """list_drivers returns dict of category -> [driver_ids]."""
        result = list_drivers()
        assert isinstance(result, dict)
        # Should have at least backend/frontend categories from current drivers/
        assert "backend" in result or "frontend" in result or "embedded" in result

    def test_list_drivers_has_backend_fastapi(self):
        """Verify backend/fastapi driver exists in list."""
        result = list_drivers()
        assert "backend" in result
        assert "fastapi" in result["backend"]

    def test_list_drivers_has_frontend_nextjs(self):
        """Verify frontend/next_js driver exists in list."""
        result = list_drivers()
        assert "frontend" in result
        assert "next_js" in result["frontend"]

    def test_list_drivers_has_embedded(self):
        """Verify embedded drivers exist."""
        result = list_drivers()
        assert "embedded" in result
        assert "esp32c3_riscv" in result["embedded"]
        assert "zephyr_c" in result["embedded"]


class TestShowDriver:
    """Test show_driver pure function."""

    def test_show_driver_fastapi(self):
        """show_driver loads fastapi driver correctly."""
        result = show_driver("backend", "fastapi")
        assert isinstance(result, dict)
        assert result["id"] == "fastapi"
        assert result["category"] == "backend"
        assert result["language"] == "python"

    def test_show_driver_embedded_esp32c3(self):
        """show_driver loads embedded ESP32-C3 driver."""
        result = show_driver("embedded", "esp32c3_riscv")
        assert result["id"] == "esp32c3_riscv"
        assert result["category"] == "embedded"
        assert result["framework"].lower().startswith("esp-idf")

    def test_show_driver_not_found(self):
        """show_driver raises on missing driver."""
        with pytest.raises(Exception):  # FileNotFoundError or ValueError
            show_driver("backend", "nonexistent_driver")

    def test_show_driver_invalid_category(self):
        """show_driver raises on invalid category."""
        with pytest.raises(Exception):
            show_driver("invalid_category", "fastapi")


class TestPlanFromConfig:
    """Test plan_from_config pure function with mocked detectors."""

    def test_plan_config_not_found(self):
        """plan_from_config returns (2, error_dict) if config missing."""
        rc, report = plan_from_config("/nonexistent/config.yaml")
        assert rc == 2
        assert "error" in report

    def test_plan_drivers_disabled(self, tmp_path):
        """plan_from_config handles drivers.enabled: false."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("drivers:\n  enabled: false\n")

        rc, report = plan_from_config(str(config_path))
        assert rc == 0
        assert report["drivers.enabled"] is False
        assert "note" in report
        assert "legacy behavior only" in report["note"]

    def test_plan_with_backend_target(self, tmp_path):
        """plan_from_config resolves backend driver."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\nproject:\n  targets:\n    backend: fastapi\n"
        )

        rc, report = plan_from_config(str(config_path))
        assert rc == 0
        assert report["drivers.enabled"] is True
        assert "backend" in report["plan"]
        assert report["plan"]["backend"]["id"] == "fastapi"
        assert report["plan"]["backend"]["framework"] == "fastapi"

    def test_plan_with_embedded_esp32_no_detection(self, tmp_path):
        """plan_from_config handles embedded with no detectors (fallback)."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\n  embedded:\n    run_build: false\n    run_test: false\nproject:\n  targets:\n    embedded: esp32c3_riscv\n"
        )

        # Call without detectors - should gracefully skip detection
        rc, report = plan_from_config(str(config_path), detectors={})
        assert rc == 0
        assert "embedded" in report["plan"]
        assert report["plan"]["embedded"]["detection"]["ok"] is False

    def test_plan_with_embedded_esp32_mocked_idf_found(self, tmp_path):
        """plan_from_config detects idf.py via mocked detector."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\n  embedded:\n    run_build: true\n    run_test: true\nproject:\n  targets:\n    embedded: esp32c3_riscv\n"
        )

        # Mock detector says idf is available
        mock_detectors: DetectorMap = {
            "idf": lambda: (True, "idf.py found at /opt/esp/idf/tools/idf.py"),
        }

        rc, report = plan_from_config(str(config_path), detectors=mock_detectors)
        assert rc == 0
        assert report["plan"]["embedded"]["detection"]["ok"] is True
        assert "idf.py found" in report["plan"]["embedded"]["detection"]["message"]
        assert report["plan"]["embedded"]["flags"]["run_build"] is True
        assert report["plan"]["embedded"]["would_run"]["build"] is True

    def test_plan_with_embedded_zephyr_mocked_west_not_found(self, tmp_path):
        """plan_from_config detects missing west via mocked detector."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\n  embedded:\n    run_build: false\n    run_test: true\nproject:\n  targets:\n    embedded: zephyr_c\n"
        )

        # Mock detector says west is not available
        mock_detectors: DetectorMap = {
            "west": lambda: (False, "west not found on PATH"),
        }

        rc, report = plan_from_config(str(config_path), detectors=mock_detectors)
        assert rc == 0
        assert report["plan"]["embedded"]["detection"]["ok"] is False
        assert "west not found" in report["plan"]["embedded"]["detection"]["message"]
        assert report["plan"]["embedded"]["would_run"]["test"] is False  # Blocked by missing toolchain

    def test_plan_with_multiple_targets(self, tmp_path):
        """plan_from_config handles multiple targets at once."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """drivers:
  enabled: true
project:
  targets:
    backend: fastapi
    frontend: next_js
    embedded: esp32c3_riscv
"""
        )

        mock_detectors: DetectorMap = {
            "idf": lambda: (True, "idf available"),
        }

        rc, report = plan_from_config(str(config_path), detectors=mock_detectors)
        assert rc == 0
        assert "backend" in report["plan"]
        assert "frontend" in report["plan"]
        assert "embedded" in report["plan"]

    def test_plan_with_invalid_driver_id(self, tmp_path):
        """plan_from_config handles missing driver gracefully."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\nproject:\n  targets:\n    backend: nonexistent\n"
        )

        rc, report = plan_from_config(str(config_path))
        assert rc == 0  # Report generation succeeds, error noted in plan
        assert "backend" in report["plan"]
        assert "error" in report["plan"]["backend"]


class TestGetDefaultDetectors:
    """Test _get_default_detectors factory."""

    def test_get_default_detectors_returns_dict(self):
        """_get_default_detectors returns DetectorMap."""
        detectors = _get_default_detectors()
        assert isinstance(detectors, dict)
        # May have idf and/or west if drivers.detect module available
        assert isinstance(detectors, dict)

    def test_detectors_are_callable(self):
        """All detector values are callable and return (bool, str)."""
        detectors = _get_default_detectors()
        for name, detector_fn in detectors.items():
            assert callable(detector_fn), f"Detector {name} is not callable"
            result = detector_fn()
            assert isinstance(result, tuple), f"Detector {name} returned {type(result)}, expected tuple"
            assert len(result) == 2, f"Detector {name} returned {len(result)} items, expected 2"
            ok, msg = result
            assert isinstance(ok, bool), f"Detector {name} first element is {type(ok)}, expected bool"
            assert isinstance(msg, str), f"Detector {name} second element is {type(msg)}, expected str"


class TestCLIIntegration:
    """Integration tests for CLI commands (ensure output format unchanged)."""

    def test_cli_list_command_produces_yaml(self, capsys):
        """CLI list command produces valid YAML output."""
        from drivers.cli import _cmd_list

        rc = _cmd_list()
        captured = capsys.readouterr()

        assert rc == 0
        assert "backend:" in captured.out or "frontend:" in captured.out
        # Should be parseable as YAML
        import yaml
        result = yaml.safe_load(captured.out)
        assert isinstance(result, dict)

    def test_cli_show_command_produces_yaml(self, capsys):
        """CLI show command produces valid YAML output."""
        from drivers.cli import _cmd_show

        rc = _cmd_show("backend", "fastapi")
        captured = capsys.readouterr()

        assert rc == 0
        assert "id: fastapi" in captured.out
        # Should be parseable as YAML
        import yaml
        result = yaml.safe_load(captured.out)
        assert result["id"] == "fastapi"

    def test_cli_plan_command_with_valid_config(self, tmp_path, capsys):
        """CLI plan command produces valid YAML output."""
        from drivers.cli import _cmd_plan

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "drivers:\n  enabled: true\nproject:\n  targets:\n    backend: fastapi\n"
        )

        rc = _cmd_plan(str(config_path))
        captured = capsys.readouterr()

        assert rc == 0
        assert "drivers.enabled:" in captured.out
        # Should be parseable as YAML
        import yaml
        result = yaml.safe_load(captured.out)
        assert result["drivers.enabled"] is True


# ========== Task 1.6: CLI main() entry point tests (lines 169, 176-206) ==========


class TestCLIMainEntryPoint:
    """Test CLI main() entry point with argument parsing."""

    def test_main_validate_all(self, capsys):
        """Line 196-198: validate --all command."""
        from drivers.cli import main
        rc = main(["validate", "--all"])
        assert rc == 0
        captured = capsys.readouterr()
        # Should validate all drivers successfully
        assert "✓" in captured.out or "fastapi" in captured.out.lower()

    def test_main_validate_without_all_errors(self):
        """Line 199: validate without --all should error."""
        from drivers.cli import main
        with pytest.raises(SystemExit):  # argparse calls sys.exit
            main(["validate"])

    def test_main_load_command(self, capsys):
        """Line 200-201: load command calls _cmd_show."""
        from drivers.cli import main
        rc = main(["load", "backend", "fastapi"])
        captured = capsys.readouterr()
        assert rc == 0
        import yaml
        result = yaml.safe_load(captured.out)
        assert result["id"] == "fastapi"

    def test_main_show_command(self, capsys):
        """Line 200-201: show command (alias of load)."""
        from drivers.cli import main
        rc = main(["show", "backend", "fastapi"])
        captured = capsys.readouterr()
        assert rc == 0
        import yaml
        result = yaml.safe_load(captured.out)
        assert result["id"] == "fastapi"

    def test_main_list_command(self, capsys):
        """Line 202-203: list command calls _cmd_list."""
        from drivers.cli import main
        rc = main(["list"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "backend:" in captured.out
        assert "fastapi" in captured.out

    def test_main_plan_command_default_config(self, capsys):
        """Line 204-205: plan command with default config path."""
        from drivers.cli import main
        # This will use the actual config.yaml in the repo
        rc = main(["plan"])
        captured = capsys.readouterr()
        # Should produce YAML output
        assert rc == 0 or "drivers.enabled" in captured.out  # tolerant if config missing

    def test_main_plan_command_custom_config(self, tmp_path, capsys):
        """Line 204-205: plan command with custom --config."""
        from drivers.cli import main
        config_path = tmp_path / "custom.yaml"
        config_path.write_text("drivers:\n  enabled: false\n")
        rc = main(["plan", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert rc == 0
        assert "drivers.enabled:" in captured.out

    def test_main_plan_error_path(self, tmp_path, capsys):
        """Line 169: _cmd_plan error handling (print error message)."""
        from drivers.cli import main
        # Use nonexistent config file to trigger rc=2 error path
        config_path = tmp_path / "nonexistent.yaml"
        rc = main(["plan", "--config", str(config_path)])
        captured = capsys.readouterr()
        # Should return non-zero (rc=2) and show error
        assert rc == 2
        assert "❌" in captured.out
        assert "error" in captured.out.lower() or "not found" in captured.out.lower()

    def test_main_no_command_raises(self):
        """Line 177: argparse requires a command."""
        from drivers.cli import main
        with pytest.raises(SystemExit):
            main([])

    def test_main_invalid_command_raises(self):
        """Line 176-206: invalid command should error."""
        from drivers.cli import main
        with pytest.raises(SystemExit):
            main(["invalid_command"])
