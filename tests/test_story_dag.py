"""Tests for Story DAG."""

import pytest
from scripts.orchestrator.story_dag import StoryDAG


class TestStoryDAG:
    """Test StoryDAG class."""

    def test_add_story(self):
        """Test adding stories to DAG."""
        dag = StoryDAG()
        dag.add_story("S1", {"priority": "P1"}, depends_on=[])
        assert "S1" in dag.nodes

    def test_ready_stories_no_deps(self):
        """Test ready stories without dependencies."""
        dag = StoryDAG()
        dag.add_story("S1", {"priority": "P1"}, depends_on=[])
        dag.add_story("S2", {"priority": "P1"}, depends_on=[])

        ready = dag.get_ready_stories(set(), set(), set())
        assert set(ready) == {"S1", "S2"}

    def test_ready_stories_with_deps(self):
        """Test ready stories with dependencies."""
        dag = StoryDAG()
        dag.add_story("S1", {"priority": "P1"}, depends_on=[])
        dag.add_story("S2", {"priority": "P1"}, depends_on=["S1"])

        # S1 ready, S2 waiting
        ready = dag.get_ready_stories(set(), set(), set())
        assert ready == ["S1"]

        # After S1 done, S2 ready
        ready = dag.get_ready_stories({"S1"}, set(), set())
        assert ready == ["S2"]

    def test_blocked_stories(self):
        """Test blocked stories from failed dependencies."""
        dag = StoryDAG()
        dag.add_story("S1", {}, depends_on=[])
        dag.add_story("S2", {}, depends_on=["S1"])
        dag.add_story("S3", {}, depends_on=["S2"])

        blocked = dag.get_blocked_stories({"S1"})
        assert blocked == {"S2", "S3"}

    def test_parallel_batch(self):
        """Test parallel batch selection."""
        dag = StoryDAG()
        dag.add_story("S1", {"epic": "E1", "priority": "P1"}, depends_on=[])
        dag.add_story("S2", {"epic": "E2", "priority": "P1"}, depends_on=[])
        dag.add_story("S3", {"epic": "E3", "priority": "P1"}, depends_on=[])

        ready = ["S1", "S2", "S3"]
        batch = dag.get_parallel_batch(ready, max_parallelism=2)
        assert len(batch) == 2

    def test_topological_sort(self):
        """Test topological sort."""
        dag = StoryDAG()
        dag.add_story("S1", {}, depends_on=[])
        dag.add_story("S2", {}, depends_on=["S1"])
        dag.add_story("S3", {}, depends_on=["S1"])
        dag.add_story("S4", {}, depends_on=["S2", "S3"])

        order = dag.topological_sort()
        assert order[0] == "S1"
        assert order.index("S2") < order.index("S4")
        assert order.index("S3") < order.index("S4")
