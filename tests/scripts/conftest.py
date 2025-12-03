import asyncio
import pytest
import os


@pytest.fixture
def llm_response_complete():
    return """PRD:
```yaml
title: Test Product
```
ARCHITECTURE:
```yaml
type: Microservices
```
EPICS:
```yaml
- id: E1
  title: Auth
```
STORIES:
```yaml
- id: S1
  title: User Registration
  status: todo
```
TASKS:
```csv
id,task
T1,Do thing
```"""


@pytest.fixture
def llm_response_partial_stories_only():
    return """STORIES:
```yaml
- id: S1
  title: Basic Feature
  status: todo
```"""


@pytest.fixture
def llm_response_missing_prd():
    return """ARCHITECTURE:
```yaml
type: Microservices
```
STORIES:
```yaml
- id: S1
  title: Story
  status: todo
```"""


@pytest.fixture
def llm_response_missing_architecture():
    return """PRD:
```yaml
title: Test Product
```
STORIES:
```yaml
- id: S1
  title: Story
  status: todo
```"""


@pytest.fixture
def llm_response_missing_tasks():
    return """PRD:
```yaml
title: Test Product
```
ARCHITECTURE:
```yaml
type: Microservices
```
STORIES:
```yaml
- id: S1
  title: Story
  status: todo
```"""


@pytest.fixture
def llm_response_malformed_yaml():
    return "PRD: ```yaml not-really-yaml"


@pytest.fixture
def mock_client_factory():
    class MockClient:
        def __init__(self, responses):
            self._responses = list(responses)
            self.call_count = 0

        async def chat(self, system=None, user=None):
            self.call_count += 1
            if self._responses:
                return self._responses.pop(0)
            return ""

    def factory(responses):
        return MockClient(responses)

    return factory


@pytest.fixture(autouse=True)
def pipeline_guard_bypass(monkeypatch, request):
    """
    Disable pipeline guard for most tests to avoid dependency on PO/stories fixtures.
    Tests that target the guard itself can opt out by name.
    """
    if "pipeline_guard" in request.node.nodeid:
        return
    monkeypatch.setenv("PIPELINE_GUARD_BYPASS", "1")
