"""Pytest configuration and shared fixtures.

Task: RUN_ARCHITECT_TEST_COVERAGE_PLAN - Fase 1, Tarea 1.2
"""
import sys
from pathlib import Path

# Add project root to path for imports
ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# Import fixtures to make them available to all tests
pytest_plugins = ["tests.fixtures.architect_responses"]
