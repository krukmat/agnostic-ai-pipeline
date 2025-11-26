from __future__ import annotations

from pathlib import Path
import json
import yaml
import pytest

from drivers.validator import validate_driver_dict
from drivers.loader import load_driver, validate_all


ROOT = Path(__file__).resolve().parents[2]


def test_validate_driver_dict_valid_fastapi():
    yml = ROOT / "drivers" / "backend" / "fastapi.yaml"
    data = yaml.safe_load(yml.read_text(encoding="utf-8"))
    validate_driver_dict(data)  # should not raise


def test_validate_driver_dict_invalid_id_pattern():
    bad = {
        "id": "FastAPI",  # uppercase not allowed
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
    }
    with pytest.raises(ValueError):
        validate_driver_dict(bad)


def test_validate_driver_dict_rejects_chaining_operators():
    bad = {
        "id": "next_js",
        "category": "frontend",
        "language": "javascript",
        "framework": "next_js",
        "build": {"command": "npm ci && npm test"},
    }
    with pytest.raises(ValueError):
        validate_driver_dict(bad)


def test_load_driver_fastapi_and_templates():
    drv = load_driver("backend", "fastapi")
    assert drv.id == "fastapi"
    assert drv.category == "backend"
    # templates is a list of dataclasses with path/source
    assert isinstance(drv.templates, list)
    assert all(hasattr(t, "path") and hasattr(t, "source") for t in drv.templates)


def test_validate_all_returns_zero():
    assert validate_all() == 0


# ========== Task 1.6: Negative tests for validator.py coverage ==========


def test_validate_missing_required_id():
    """Line 16: missing 'id' key."""
    bad = {"category": "backend", "language": "python", "framework": "fastapi"}
    with pytest.raises(ValueError, match="missing required key 'id'"):
        validate_driver_dict(bad)


def test_validate_wrong_type_id():
    """Line 18: 'id' is not a string."""
    bad = {"id": 123, "category": "backend", "language": "python", "framework": "fastapi"}
    with pytest.raises(ValueError, match="key 'id' must be"):
        validate_driver_dict(bad)


def test_validate_invalid_category():
    """Line 33: category not in VALID_CATEGORIES."""
    bad = {"id": "foo", "category": "invalid_cat", "language": "python", "framework": "fastapi"}
    with pytest.raises(ValueError, match="invalid category"):
        validate_driver_dict(bad)


def test_validate_templates_not_list():
    """Line 40: templates is not a list."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "templates": "not_a_list",
    }
    with pytest.raises(ValueError, match="templates must be a list"):
        validate_driver_dict(bad)


def test_validate_template_missing_path():
    """Line 43: template dict missing 'path' or 'source'."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "templates": [{"path": "foo.txt"}],  # missing source
    }
    with pytest.raises(ValueError, match="each template must be a dict with 'path' and 'source'"):
        validate_driver_dict(bad)


def test_validate_build_not_dict():
    """Line 49: build is not a dict with 'command'."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "build": "not_a_dict",
    }
    with pytest.raises(ValueError, match="build must be a dict with 'command': str"):
        validate_driver_dict(bad)


def test_validate_build_empty_command():
    """Line 51: build.command is empty string."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "build": {"command": "   "},
    }
    with pytest.raises(ValueError, match="build.command must be a non-empty string"):
        validate_driver_dict(bad)


def test_validate_artifact_paths_not_list():
    """Line 56: artifact_paths is not a list."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "artifact_paths": "not_a_list",
    }
    with pytest.raises(ValueError, match="artifact_paths must be a list"):
        validate_driver_dict(bad)


def test_validate_embedded_board_not_string():
    """Line 61: embedded.board is not a string."""
    bad = {
        "id": "foo",
        "category": "embedded",
        "language": "c",
        "framework": "esp-idf",
        "board": 123,
    }
    with pytest.raises(ValueError, match="embedded.board must be a string"):
        validate_driver_dict(bad)


def test_validate_embedded_flash_command_not_string():
    """Line 63: embedded.flash_command is not a string."""
    bad = {
        "id": "foo",
        "category": "embedded",
        "language": "c",
        "framework": "esp-idf",
        "flash_command": ["not", "string"],
    }
    with pytest.raises(ValueError, match="embedded.flash_command must be a string"):
        validate_driver_dict(bad)


def test_validate_embedded_monitor_command_not_string():
    """Line 65: embedded.monitor_command is not a string."""
    bad = {
        "id": "foo",
        "category": "embedded",
        "language": "c",
        "framework": "esp-idf",
        "monitor_command": None,
    }
    with pytest.raises(ValueError, match="embedded.monitor_command must be a string"):
        validate_driver_dict(bad)


def test_validate_gpu_arch_not_string():
    """Line 71: gpu.gpu_arch is not a string."""
    bad = {
        "id": "foo",
        "category": "gpu",
        "language": "cuda",
        "framework": "cuda",
        "gpu_arch": 123,
    }
    with pytest.raises(ValueError, match="gpu.gpu_arch must be a string"):
        validate_driver_dict(bad)


def test_validate_gpu_arch_invalid_format():
    """Line 73: gpu_arch doesn't start with sm_ or gfx."""
    bad = {
        "id": "foo",
        "category": "gpu",
        "language": "cuda",
        "framework": "cuda",
        "gpu_arch": "invalid_arch",
    }
    with pytest.raises(ValueError, match="gpu.gpu_arch seems invalid"):
        validate_driver_dict(bad)


def test_validate_command_with_newline():
    """Line 87: command contains newline."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "test": {"command": "pytest\nnpm test"},
    }
    with pytest.raises(ValueError, match="must be a single line"):
        validate_driver_dict(bad)


def test_validate_command_invalid_first_token():
    """Line 95: command starts with invalid token."""
    bad = {
        "id": "foo",
        "category": "backend",
        "language": "python",
        "framework": "fastapi",
        "test": {"command": "$INVALID pytest"},
    }
    with pytest.raises(ValueError, match="starts with an invalid token"):
        validate_driver_dict(bad)

