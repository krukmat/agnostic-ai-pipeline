"""Tests for Task 6: Configuration YAML Schema

Tests validate that config.yaml loads correctly with all required sections,
fields, and proper defaults.

TDD approach - tests written first.
"""
import tempfile
from pathlib import Path
import yaml
import pytest


@pytest.fixture
def config_file():
    """Load the actual config.yaml file."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        pytest.skip("config.yaml not found")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


@pytest.fixture
def sample_config():
    """Sample config for testing."""
    return {
        "pipeline": {
            "retry_policies": {
                "dev": {
                    "max_attempts": 3,
                    "backoff": "exponential",
                    "circuit_breaker": {
                        "threshold": 5,
                        "window": 600
                    }
                }
            },
            "resource_policies": {
                "max_parallel_stories": 3,
                "max_concurrent_dev": 2,
                "dev_timeout": 600
            }
        },
        "coherence": {
            "enabled": True,
            "min_coverage": 0.95
        }
    }


# ==============================================================================
# TEST SUITE 1: Config File Loads
# ==============================================================================

class TestConfigFileLoads:
    """Test that config.yaml loads successfully."""

    def test_config_file_exists(self):
        """config.yaml file exists."""
        config_path = Path("config.yaml")
        assert config_path.exists(), "config.yaml must exist"

    def test_config_file_is_valid_yaml(self):
        """config.yaml is valid YAML."""
        config_path = Path("config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict), "config.yaml must parse to dict"
        assert len(config) > 0, "config.yaml must not be empty"

    def test_config_loads_without_errors(self, config_file):
        """config.yaml loads without errors."""
        assert config_file is not None
        assert isinstance(config_file, dict)


# ==============================================================================
# TEST SUITE 2: Required Sections Present
# ==============================================================================

class TestRequiredSections:
    """Test that all required configuration sections exist."""

    def test_pipeline_section_exists(self, config_file):
        """pipeline section exists."""
        assert "pipeline" in config_file, "Missing 'pipeline' section"

    def test_coherence_section_exists(self, config_file):
        """coherence section exists."""
        assert "coherence" in config_file, "Missing 'coherence' section"

    def test_cot_tracking_section_exists(self, config_file):
        """cot_tracking section exists."""
        assert "cot_tracking" in config_file, "Missing 'cot_tracking' section"

    def test_orchestration_section_exists(self, config_file):
        """orchestration section exists."""
        assert "orchestration" in config_file, "Missing 'orchestration' section"


# ==============================================================================
# TEST SUITE 3: Retry Policies
# ==============================================================================

class TestRetryPolicies:
    """Test retry policies configuration."""

    def test_retry_policies_exist(self, config_file):
        """Retry policies section exists."""
        pipeline = config_file.get("pipeline", {})
        assert "retry_policies" in pipeline, "Missing 'retry_policies'"

    def test_dev_retry_policy_exists(self, config_file):
        """Dev retry policy exists."""
        policies = config_file.get("pipeline", {}).get("retry_policies", {})
        assert "dev" in policies, "Missing dev retry policy"

    def test_dev_retry_has_max_attempts(self, config_file):
        """Dev retry policy has max_attempts."""
        policies = config_file.get("pipeline", {}).get("retry_policies", {})
        dev_policy = policies.get("dev", {})
        assert "max_attempts" in dev_policy, "Dev policy missing max_attempts"
        assert isinstance(dev_policy["max_attempts"], int)
        assert dev_policy["max_attempts"] > 0

    def test_dev_retry_has_backoff(self, config_file):
        """Dev retry policy has backoff strategy."""
        policies = config_file.get("pipeline", {}).get("retry_policies", {})
        dev_policy = policies.get("dev", {})
        assert "backoff" in dev_policy, "Dev policy missing backoff"
        assert dev_policy["backoff"] in ["exponential", "linear", "none"]

    def test_architect_retry_policy_exists(self, config_file):
        """Architect retry policy exists."""
        policies = config_file.get("pipeline", {}).get("retry_policies", {})
        assert "architect" in policies, "Missing architect retry policy"

    def test_qa_retry_policy_exists(self, config_file):
        """QA retry policy exists."""
        policies = config_file.get("pipeline", {}).get("retry_policies", {})
        assert "qa" in policies, "Missing qa retry policy"


# ==============================================================================
# TEST SUITE 4: Escalation Policies
# ==============================================================================

class TestEscalationPolicies:
    """Test escalation policies configuration."""

    def test_escalation_policies_exist(self, config_file):
        """Escalation policies section exists."""
        pipeline = config_file.get("pipeline", {})
        assert "escalation_policies" in pipeline, "Missing escalation_policies"

    def test_escalation_policies_is_list(self, config_file):
        """Escalation policies is a list."""
        policies = config_file.get("pipeline", {}).get("escalation_policies", [])
        assert isinstance(policies, list), "escalation_policies must be list"

    def test_escalation_policies_have_conditions(self, config_file):
        """Escalation policies have conditions."""
        policies = config_file.get("pipeline", {}).get("escalation_policies", [])

        if policies:  # If policies defined
            for policy in policies:
                assert "condition" in policy, f"Policy missing condition: {policy}"
                assert isinstance(policy["condition"], str)

    def test_escalation_policies_have_actions(self, config_file):
        """Escalation policies have actions."""
        policies = config_file.get("pipeline", {}).get("escalation_policies", [])

        if policies:  # If policies defined
            for policy in policies:
                assert "action" in policy, f"Policy missing action: {policy}"
                assert isinstance(policy["action"], str)


# ==============================================================================
# TEST SUITE 5: Resource Policies
# ==============================================================================

class TestResourcePolicies:
    """Test resource policies configuration."""

    def test_resource_policies_exist(self, config_file):
        """Resource policies section exists."""
        pipeline = config_file.get("pipeline", {})
        assert "resource_policies" in pipeline, "Missing resource_policies"

    def test_max_parallel_stories_exists(self, config_file):
        """max_parallel_stories exists."""
        policies = config_file.get("pipeline", {}).get("resource_policies", {})
        assert "max_parallel_stories" in policies, "Missing max_parallel_stories"
        assert isinstance(policies["max_parallel_stories"], int)
        assert policies["max_parallel_stories"] > 0

    def test_max_concurrent_dev_exists(self, config_file):
        """max_concurrent_dev exists."""
        policies = config_file.get("pipeline", {}).get("resource_policies", {})
        assert "max_concurrent_dev" in policies, "Missing max_concurrent_dev"
        assert isinstance(policies["max_concurrent_dev"], int)

    def test_max_concurrent_qa_exists(self, config_file):
        """max_concurrent_qa exists."""
        policies = config_file.get("pipeline", {}).get("resource_policies", {})
        assert "max_concurrent_qa" in policies, "Missing max_concurrent_qa"
        assert isinstance(policies["max_concurrent_qa"], int)

    def test_dev_timeout_exists(self, config_file):
        """dev_timeout exists."""
        policies = config_file.get("pipeline", {}).get("resource_policies", {})
        assert "dev_timeout" in policies, "Missing dev_timeout"
        assert isinstance(policies["dev_timeout"], int)
        assert policies["dev_timeout"] > 0

    def test_qa_timeout_exists(self, config_file):
        """qa_timeout exists."""
        policies = config_file.get("pipeline", {}).get("resource_policies", {})
        assert "qa_timeout" in policies, "Missing qa_timeout"
        assert isinstance(policies["qa_timeout"], int)
        assert policies["qa_timeout"] > 0


# ==============================================================================
# TEST SUITE 6: Priority Policies
# ==============================================================================

class TestPriorityPolicies:
    """Test priority policies configuration."""

    def test_priority_policies_exist(self, config_file):
        """Priority policies section exists."""
        pipeline = config_file.get("pipeline", {})
        assert "priority_policies" in pipeline, "Missing priority_policies"

    def test_priority_policies_is_list(self, config_file):
        """Priority policies is a list."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])
        assert isinstance(policies, list), "priority_policies must be list"

    def test_p0_priority_exists(self, config_file):
        """P0 priority policy exists."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])
        priorities = [p.get("priority") for p in policies]
        assert "P0" in priorities, "Missing P0 priority"

    def test_p1_priority_exists(self, config_file):
        """P1 priority policy exists."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])
        priorities = [p.get("priority") for p in policies]
        assert "P1" in priorities, "Missing P1 priority"

    def test_p2_priority_exists(self, config_file):
        """P2 priority policy exists."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])
        priorities = [p.get("priority") for p in policies]
        assert "P2" in priorities, "Missing P2 priority"

    def test_priority_has_max_retries(self, config_file):
        """Priority policies have max_retries."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])

        for policy in policies:
            assert "max_retries" in policy, f"Missing max_retries in {policy}"
            assert isinstance(policy["max_retries"], int)

    def test_priority_has_timeout_multiplier(self, config_file):
        """Priority policies have timeout_multiplier."""
        policies = config_file.get("pipeline", {}).get("priority_policies", [])

        for policy in policies:
            assert "timeout_multiplier" in policy, f"Missing timeout_multiplier in {policy}"
            assert isinstance(policy["timeout_multiplier"], (int, float))


# ==============================================================================
# TEST SUITE 7: Coherence Configuration
# ==============================================================================

class TestCoherenceConfig:
    """Test coherence configuration."""

    def test_coherence_enabled_exists(self, config_file):
        """coherence.enabled exists."""
        coherence = config_file.get("coherence", {})
        assert "enabled" in coherence, "Missing coherence.enabled"
        assert isinstance(coherence["enabled"], bool)

    def test_coherence_checkpoints_exist(self, config_file):
        """coherence checkpoints exist."""
        coherence = config_file.get("coherence", {})
        assert "checkpoints" in coherence, "Missing coherence.checkpoints"

    def test_post_requirements_checkpoint(self, config_file):
        """post_requirements checkpoint exists."""
        checkpoints = config_file.get("coherence", {}).get("checkpoints", {})
        assert "post_requirements" in checkpoints, "Missing post_requirements checkpoint"

    def test_post_planning_checkpoint(self, config_file):
        """post_planning checkpoint exists."""
        checkpoints = config_file.get("coherence", {}).get("checkpoints", {})
        assert "post_planning" in checkpoints, "Missing post_planning checkpoint"

    def test_post_integration_checkpoint(self, config_file):
        """post_integration checkpoint exists."""
        checkpoints = config_file.get("coherence", {}).get("checkpoints", {})
        assert "post_integration" in checkpoints, "Missing post_integration checkpoint"

    def test_min_coverage_exists(self, config_file):
        """min_coverage exists."""
        coherence = config_file.get("coherence", {})
        assert "min_coverage" in coherence, "Missing min_coverage"
        assert isinstance(coherence["min_coverage"], (int, float))
        assert 0 <= coherence["min_coverage"] <= 1

    def test_min_similarity_exists(self, config_file):
        """min_similarity exists."""
        coherence = config_file.get("coherence", {})
        assert "min_similarity" in coherence, "Missing min_similarity"
        assert isinstance(coherence["min_similarity"], (int, float))

    def test_llm_enabled_exists(self, config_file):
        """llm_enabled exists."""
        coherence = config_file.get("coherence", {})
        assert "llm_enabled" in coherence, "Missing llm_enabled"
        assert isinstance(coherence["llm_enabled"], bool)


# ==============================================================================
# TEST SUITE 8: CoT Tracking Configuration
# ==============================================================================

class TestCoTTrackingConfig:
    """Test CoT tracking configuration."""

    def test_cot_enabled_exists(self, config_file):
        """cot_tracking.enabled exists."""
        cot = config_file.get("cot_tracking", {})
        assert "enabled" in cot, "Missing cot_tracking.enabled"
        assert isinstance(cot["enabled"], bool)

    def test_cot_layer_aware_exists(self, config_file):
        """cot_tracking.layer_aware exists."""
        cot = config_file.get("cot_tracking", {})
        assert "layer_aware" in cot, "Missing cot_tracking.layer_aware"
        assert isinstance(cot["layer_aware"], bool)

    def test_cot_export_formats_exist(self, config_file):
        """cot_tracking.export_formats exists."""
        cot = config_file.get("cot_tracking", {})
        assert "export_formats" in cot, "Missing cot_tracking.export_formats"
        assert isinstance(cot["export_formats"], list)

    def test_cot_output_dir_exists(self, config_file):
        """cot_tracking.output_dir exists."""
        cot = config_file.get("cot_tracking", {})
        assert "output_dir" in cot, "Missing cot_tracking.output_dir"
        assert isinstance(cot["output_dir"], str)


# ==============================================================================
# TEST SUITE 9: LLM Fallback Configuration
# ==============================================================================

class TestLLMFallbackConfig:
    """Test LLM fallback configuration."""

    def test_llm_fallback_section_exists(self, config_file):
        """orchestration.llm_fallback section exists."""
        orch = config_file.get("orchestration", {})
        assert "llm_fallback" in orch, "Missing orchestration.llm_fallback"

    def test_llm_fallback_enabled_exists(self, config_file):
        """llm_fallback.enabled exists."""
        llm = config_file.get("orchestration", {}).get("llm_fallback", {})
        assert "enabled" in llm, "Missing llm_fallback.enabled"
        assert isinstance(llm["enabled"], bool)

    def test_llm_fallback_use_for_exists(self, config_file):
        """llm_fallback.use_for exists."""
        llm = config_file.get("orchestration", {}).get("llm_fallback", {})
        assert "use_for" in llm, "Missing llm_fallback.use_for"
        assert isinstance(llm["use_for"], list)

    def test_llm_fallback_llm_role_exists(self, config_file):
        """llm_fallback.llm_role exists."""
        llm = config_file.get("orchestration", {}).get("llm_fallback", {})
        assert "llm_role" in llm, "Missing llm_fallback.llm_role"
        assert isinstance(llm["llm_role"], str)

    def test_llm_fallback_max_tokens_exists(self, config_file):
        """llm_fallback.max_tokens exists."""
        llm = config_file.get("orchestration", {}).get("llm_fallback", {})
        assert "max_tokens" in llm, "Missing llm_fallback.max_tokens"
        assert isinstance(llm["max_tokens"], int)

    def test_llm_fallback_temperature_exists(self, config_file):
        """llm_fallback.temperature exists."""
        llm = config_file.get("orchestration", {}).get("llm_fallback", {})
        assert "temperature" in llm, "Missing llm_fallback.temperature"
        assert isinstance(llm["temperature"], (int, float))
        assert 0 <= llm["temperature"] <= 1


# ==============================================================================
# TEST SUITE 10: End-to-End Configuration
# ==============================================================================

class TestConfigE2E:
    """End-to-end configuration tests."""

    def test_config_structure_complete(self, config_file):
        """Complete configuration structure exists."""
        # Count sections
        expected_sections = [
            "pipeline",
            "coherence",
            "cot_tracking",
            "orchestration"
        ]

        for section in expected_sections:
            assert section in config_file, f"Missing section: {section}"

    def test_config_is_well_formed(self, config_file):
        """Configuration is well-formed."""
        # All values should be dict, list, or primitives
        for key, value in config_file.items():
            assert isinstance(value, (dict, list, str, int, float, bool, type(None))), \
                f"Invalid type in {key}: {type(value)}"

    def test_config_can_be_serialized(self, config_file):
        """Configuration can be serialized back to YAML."""
        yaml_str = yaml.dump(config_file)
        assert yaml_str is not None
        assert len(yaml_str) > 0

        # Can re-parse
        reparsed = yaml.safe_load(yaml_str)
        assert reparsed is not None
