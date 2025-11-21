import types

import dspy_baseline.metrics.architect_metrics as metrics


def _prediction(stories, epics, architecture):
    pred = types.SimpleNamespace()
    pred.stories_yaml = metrics.yaml.safe_dump(stories)
    pred.epics_yaml = metrics.yaml.safe_dump(epics)
    pred.architecture_yaml = metrics.yaml.safe_dump(architecture)
    return pred


def test_architect_metric_v2_perfect_sample():
    stories = [
        {
            "id": "S1",
            "epic": "E1",
            "title": "Login story",
            "description": "As a user I can login with email and password.",
            "acceptance": [
                "Given a registered user When they submit valid credentials Then grant access",
                "Given invalid credentials When they submit Then show error",
                "Given a locked account When they login Then ask to reset password",
            ],
            "priority": "P1",
            "estimate": "M",
            "depends_on": [],
        },
        {
            "id": "S2",
            "epic": "E1",
            "title": "Logout story",
            "description": "As a user I can logout from any device.",
            "acceptance": [
                "Given an authenticated user When they click logout Then terminate the session",
                "Given multiple sessions When logging out Then invalidate all tokens",
                "Given inactivity When timeout occurs Then logout automatically",
            ],
            "priority": "High",
            "estimate": "S",
            "depends_on": ["S1"],
        },
    ]
    epics = [
        {"id": "E1", "name": "Auth epic", "description": "Auth work", "stories": ["S1", "S2"]}
    ]
    architecture = {
        "backend": {"framework": "FastAPI"},
        "frontend": {"framework": "Next.js"},
    }
    pred = _prediction(stories, epics, architecture)
    score = metrics.architect_metric_v2(None, pred)
    assert score == 1.0


def test_architect_metric_v2_partial_credit():
    stories = [
        {
            "id": "S10",
            "epic": "E1",
            "title": "Story missing acceptance",
            "description": "Short desc",
            "acceptance": ["Given one bullet When run Then ok"],
            "priority": "medium",
            "estimate": "XS",
            "depends_on": ["S99"],
        }
    ]
    epics = [{"id": "E1", "stories": ["S10", "S2"]}]
    architecture = {"backend": {"framework": "FastAPI"}, "frontend": {"framework": "Next.js"}}
    pred = _prediction(stories, epics, architecture)
    score = metrics.architect_metric_v2(None, pred)
    assert 0 < score < 1.0


def test_dependency_cycle_penalizes_but_not_zero():
    stories = [
        {
            "id": "S1",
            "epic": "E1",
            "title": "A",
            "description": "desc A long enough text to count",
            "acceptance": [
                "Given A When B Then C",
                "Given D When E Then F",
                "Given G When H Then I",
            ],
            "priority": "P2",
            "estimate": "M",
            "depends_on": ["S2"],
        },
        {
            "id": "S2",
            "epic": "E1",
            "title": "B",
            "description": "desc B long enough text to count as valid",
            "acceptance": [
                "Given J When K Then L",
                "Given M When N Then O",
                "Given P When Q Then R",
            ],
            "priority": "P3",
            "estimate": "L",
            "depends_on": ["S1"],
        },
    ]
    epics = [{"id": "E1", "stories": ["S1", "S2"]}]
    architecture = {"backend": {"framework": "FastAPI"}, "frontend": {"framework": "Next.js"}}
    pred = _prediction(stories, epics, architecture)
    score = metrics.architect_metric_v2(None, pred)
    assert 0 < score < 1.0
