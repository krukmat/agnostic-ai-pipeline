from __future__ import annotations

from pathlib import Path
from typing import Optional

from scripts.utils.runner import run_driver_cmd
from logger import logger
from common import ROOT


class DriverCommand:
    """Adapter to standardize driver command execution and logging."""

    def __init__(self, area: str, driver_id: str, cmd_name: str, command: str, log_dir: Path):
        self.area = area
        self.driver_id = driver_id
        self.cmd_name = cmd_name
        self.command = command
        self.log_dir = log_dir

    def execute(self) -> int:
        if not self.command or not isinstance(self.command, str):
            logger.debug(f"[driver] SKIP {self.area}/{self.driver_id}/{self.cmd_name}: empty command")
            return 0
        log_name = f"{self.area}_{self.driver_id}_{self.cmd_name}.log"
        logf = self.log_dir / log_name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return run_driver_cmd(self.command, Path(log_name).stem, ROOT, logf, logger, role=self.area.upper())
