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

