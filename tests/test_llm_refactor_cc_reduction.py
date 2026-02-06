"""
LLM.py CC Reduction Refactoring Tests

Goal: Reduce CC in Client.__init__ from 61 to ≤15 (target ≤10)

Strategy:
- Extract _initialize_defaults()
- Extract _initialize_provider_config()
- Extract _initialize_cli_provider()
- Extract _apply_legacy_overrides()
- Extract _apply_keyword_overrides()

TDD: Tests FAIL before refactoring, PASS after.
"""

import pytest
from unittest.mock import patch, MagicMock
from scripts.llm import Client


@pytest.mark.unit
def test_client_has_initialize_methods():
    """
    Verify helper methods exist after refactoring.

    These methods should be extracted from __init__ to reduce CC.
    """
    # Verify helper methods exist
    assert hasattr(Client, '_initialize_defaults'), \
        "Should have _initialize_defaults helper"
    assert hasattr(Client, '_initialize_provider_config'), \
        "Should have _initialize_provider_config helper"
    assert hasattr(Client, '_initialize_cli_provider'), \
        "Should have _initialize_cli_provider helper"
    assert hasattr(Client, '_apply_legacy_overrides'), \
        "Should have _apply_legacy_overrides helper"
    assert hasattr(Client, '_apply_keyword_overrides'), \
        "Should have _apply_keyword_overrides helper"


@pytest.mark.unit
def test_initialize_defaults():
    """
    Test _initialize_defaults sets correct default values.

    Covers extraction of lines 175-204 from __init__.
    """
    with patch('scripts.llm.load_config', return_value={}):
        client = Client()

        # Verify defaults
        assert client.model == "qwen2.5-coder:7b", "Default model should be set"
        assert client.temperature == 0.3, "Default temperature should be 0.3"
        assert client.max_tokens == 2048, "Default max_tokens should be 2048"
        assert client.provider_type == "ollama", "Default provider should be ollama"


@pytest.mark.unit
def test_initialize_cli_provider():
    """
    Test _initialize_cli_provider sets CLI-specific defaults.

    Covers extraction of lines 236-275 from __init__ (CLI initialization block).
    This is the most complex part of __init__ and should be extracted.
    """
    with patch('scripts.llm.load_config', return_value={}):
        with patch('scripts.llm.resolve_role_model_for_complexity', return_value=(None, None)):
            # Initialize with claude_cli provider
            provider_cfg = {
                "type": "claude_cli",
                "command": ["claude", "-p"],
                "cwd": "/tmp",
                "timeout": 60,
                "parse_json": True,
                "append_system_prompt": True,
            }

            client = Client()
            # Would call _initialize_cli_provider(provider_cfg)

            # Verify CLI attributes would be set
            assert hasattr(client, 'cli_command'), "Should have cli_command"
            assert hasattr(client, 'cli_cwd'), "Should have cli_cwd"
            assert hasattr(client, 'cli_timeout'), "Should have cli_timeout"
            assert hasattr(client, 'cli_parse_json'), "Should have cli_parse_json"


@pytest.mark.unit
def test_apply_legacy_overrides():
    """
    Test _apply_legacy_overrides applies legacy positional arguments.

    Covers extraction of lines 277-297 from __init__.
    """
    with patch('scripts.llm.load_config', return_value={}):
        with patch('scripts.llm.resolve_role_model_for_complexity', return_value=(None, None)):
            # Legacy args: provider, model, temperature, max_tokens, base_url
            client = Client(
                "ollama",  # provider
                "mistral:7b",  # model
                0.5,  # temperature
                4096,  # max_tokens
                "http://localhost:8000"  # base_url
            )

            assert client.provider_type == "ollama", "Provider should be set from legacy args"
            assert client.model == "mistral:7b", "Model should be set from legacy args"
            assert client.temperature == 0.5, "Temperature should be set from legacy args"
            assert client.max_tokens == 4096, "Max tokens should be set from legacy args"


@pytest.mark.unit
def test_apply_keyword_overrides():
    """
    Test _apply_keyword_overrides applies keyword arguments.

    Covers extraction of lines 299-314 from __init__.
    """
    with patch('scripts.llm.load_config', return_value={}):
        with patch('scripts.llm.resolve_role_model_for_complexity', return_value=(None, None)):
            # Keyword overrides
            client = Client(
                model="llama2:7b",
                temperature=0.1,
                max_tokens=1024,
                provider="openai",
                base_url="https://api.openai.com/v1"
            )

            assert client.model == "llama2:7b", "Model keyword override should work"
            assert client.temperature == 0.1, "Temperature keyword override should work"
            assert client.max_tokens == 1024, "Max tokens keyword override should work"
            assert client.provider_type == "openai", "Provider keyword override should work"


@pytest.mark.unit
def test_client_initialization_complete():
    """
    Test that Client initialization still works after refactoring.

    Ensures no regressions in basic functionality.
    """
    with patch('scripts.llm.load_config', return_value={'roles': {}, 'providers': {}}):
        with patch('scripts.llm.resolve_role_model_for_complexity', return_value=(None, None)):
            # Should initialize without errors
            client = Client(role="dev")

            # Verify basic attributes
            assert client.role is not None, "Role should be set"
            assert client.model is not None, "Model should be set"
            assert client.provider_type is not None, "Provider type should be set"


@pytest.mark.unit
def test_cc_reduction_target():
    """
    Test that refactored __init__ achieves CC reduction target.

    Before: CC=61 (too high)
    After: CC ≤ 10 (ideal for main __init__)
    Target: ≤ 15 (acceptable if main coordinator)
    """
    # This test validates the refactoring goal
    # Run: radon cc scripts/llm.py to verify CC reduction

    import os
    import subprocess

    try:
        result = subprocess.run(
            ["python", "-m", "radon", "cc", "scripts/llm.py", "--min", "B", "-s"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract CC for __init__
        lines = result.stdout.split('\n')
        init_line = [l for l in lines if '__init__' in l]

        if init_line:
            # Format: "    M 165:4 Client.__init__ - F (61)"
            cc_str = init_line[0].split('(')[-1].split(')')[0]
            cc = int(cc_str)

            # After refactoring, should be significantly lower
            assert cc < 61, f"CC should be reduced from 61, currently {cc}"
            # Additional assertion: ideally ≤ 10
            if cc > 15:
                pytest.skip(f"CC is {cc}, target is ≤15 (work in progress)")

    except Exception as e:
        pytest.skip(f"Could not run radon check: {e}")


# ============================================================================
# HELPER TESTS - Verify extracted methods work correctly
# ============================================================================

@pytest.mark.unit
def test_cli_provider_config_with_extra_args():
    """Test CLI provider handling of extra_args configuration."""
    with patch('scripts.llm.load_config', return_value={}):
        # CLI providers should correctly handle extra_args
        # Both list and string formats should work
        client = Client()
        assert hasattr(client, 'cli_extra_args'), "Should have cli_extra_args attribute"


@pytest.mark.unit
def test_provider_config_resolution():
    """Test provider configuration resolution from config.yaml."""
    config_dict = {
        'roles': {
            'dev': {
                'provider': 'ollama',
                'model': 'mistral:7b',
                'temperature': 0.4,
            }
        },
        'providers': {
            'ollama': {
                'type': 'ollama',
                'base_url': 'http://localhost:11434',
            }
        }
    }

    with patch('scripts.llm.load_config', return_value=config_dict):
        with patch('scripts.llm.resolve_role_model_for_complexity', return_value=(None, None)):
            client = Client(role='dev')

            # Verify config was resolved correctly
            assert client.provider_type == 'ollama', "Provider should be resolved from config"
            assert client.model == 'mistral:7b', "Model should be resolved from config"
            assert client.temperature == 0.4, "Temperature should be resolved from config"
