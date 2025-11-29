import os
import pytest


@pytest.mark.skip(reason="Full BA→PO→Architect→Dev→QA e2e requires local/mocked models; skipped by default.")
def test_orchestrator_e2e_placeholder():
    assert True
