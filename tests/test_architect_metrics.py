from types import SimpleNamespace

from dspy_baseline.metrics.architect_metrics import architect_metric


VALID_STORIES = """
- id: S1
  epic: E1
  title: API endpoints
  description: Implement REST API to fetch parking availability.
  acceptance:
    - GET endpoint returns JSON
  priority: P1
  estimate: M
  status: todo
- id: S2
  epic: E1
  title: Auth
  description: Provide OAuth2 login with MFA support for staff.
  acceptance:
    - Users can login with OAuth2
  priority: P2
  estimate: M
  status: todo
  depends_on:
    - S1
"""

VALID_EPICS = """
- id: E1
  name: Backend
  description: Backend services
  priority: P1
  stories:
    - S1
    - S2
"""

VALID_ARCHITECTURE = """
backend:
  framework: FastAPI
  database: PostgreSQL
frontend:
  framework: React
  styling: Tailwind
"""


def test_architect_metric_high_score():
    prediction = SimpleNamespace(
        stories_yaml=VALID_STORIES,
        epics_yaml=VALID_EPICS,
        architecture_yaml=VALID_ARCHITECTURE,
    )
    score = architect_metric(None, prediction)
    assert score > 0.8


def test_architect_metric_low_score_on_cycles_and_missing_fields():
    invalid_stories = """
- id: bad
  epic: 
  title: 
  description: 
  acceptance: []
  priority: 
  estimate: 
  status: 
  depends_on: [S99]
- id: S1
  epic: E9
  title: Story ok
  description: short desc
  acceptance: []
  priority: X
  estimate: ???
  status: todo
  depends_on: [bad]
"""
    invalid_epics = """
- id: E9
  name: 
  description: 
  priority: P1
  stories: [bad]
"""
    invalid_architecture = "backend: FastAPI"

    prediction = SimpleNamespace(
        stories_yaml=invalid_stories,
        epics_yaml=invalid_epics,
        architecture_yaml=invalid_architecture,
    )
    score = architect_metric(None, prediction)
    assert score < 0.4
