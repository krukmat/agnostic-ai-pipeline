from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _run_cli(args: list[str], env: dict | None = None) -> str:
    cmd = [sys.executable, "-m", "drivers.registry", *args]
    run_env = env.copy() if env else os.environ.copy()
    # Ensure repo root is on PYTHONPATH so drivers.registry is importable
    run_env["PYTHONPATH"] = str(ROOT)
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=run_env)
    assert res.returncode == 0, res.stderr
    return res.stdout


def test_list_has_known_categories():
    out = _run_cli(["list"])
    assert "backend:" in out
    assert "frontend:" in out
    assert "embedded:" in out


def test_plan_with_mock_zephyr_detection(tmp_path: Path, monkeypatch):
    # Create a mock 'west' on PATH
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    west = fake_bin / "west"
    west.write_text("#!/usr/bin/env bash\necho 'west 1.0.0'\n", encoding="utf-8")
    west.chmod(stat.S_IRWXU)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH','')}"

    # Write a temporary config enabling embedded zephyr and templates disabled
    cfg = {
        "drivers": {"enabled": True, "embedded": {"run_test": True}, "templates": {"apply": False}},
        "project": {"targets": {"embedded": "zephyr_c"}},
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

    out = _run_cli(["plan", "--config", str(cfg_path)], env=env)
    data = yaml.safe_load(out)
    assert data["drivers.enabled"] is True
    assert data["plan"]["embedded"]["id"] == "zephyr_c"
    assert data["plan"]["embedded"]["detection"]["ok"] is True
    assert data["plan"]["embedded"]["would_run"]["test"] is True
