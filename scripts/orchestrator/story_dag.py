"""
Story Dependency Graph (DAG).

Manages story dependencies, parallel execution, and topological sorting.
"""

from collections import defaultdict, deque
from typing import Dict, List, Set
from logger import logger


class StoryDAG:
    """
    Directed Acyclic Graph for story dependencies.
    Supports dependency tracking, topological sorting, and parallel batch selection.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)

    def add_story(self, story_id: str, metadata: Dict, depends_on: List[str] = None) -> None:
        """Add story to graph."""
        self.nodes[story_id] = metadata
        if depends_on:
            for dep in depends_on:
                self.edges[story_id].append(dep)
                self.reverse_edges[dep].append(story_id)
        logger.debug(f"[dag] Added story {story_id} with {len(depends_on or [])} dependencies")

    def get_ready_stories(self, done_stories: Set[str], failed_stories: Set[str], doing_stories: Set[str]) -> List[str]:
        """Return stories that are ready to execute."""
        ready = []

        for story_id in self.nodes.keys():
            if story_id in done_stories or story_id in failed_stories or story_id in doing_stories:
                continue

            deps = self.edges.get(story_id, [])
            if all(dep in done_stories for dep in deps):
                ready.append(story_id)

        ready.sort(key=lambda sid: (self.nodes[sid].get("priority", "P9"), sid))
        logger.debug(f"[dag] Found {len(ready)} ready stories")
        return ready

    def get_blocked_stories(self, failed_stories: Set[str]) -> Set[str]:
        """Return stories blocked by failed dependencies (transitively)."""
        blocked = set()
        queue = deque(failed_stories)

        while queue:
            failed_story = queue.popleft()
            for dependent in self.reverse_edges.get(failed_story, []):
                if dependent not in blocked:
                    blocked.add(dependent)
                    queue.append(dependent)

        logger.debug(f"[dag] Found {len(blocked)} blocked stories")
        return blocked

    def get_parallel_batch(self, ready_stories: List[str], max_parallelism: int = 3) -> List[str]:
        """Select stories for parallel execution (group by epic)."""
        if not ready_stories:
            return []

        by_epic: Dict[str, List[str]] = defaultdict(list)
        for sid in ready_stories:
            epic = self.nodes[sid].get("epic", "")
            by_epic[epic].append(sid)

        batch = []
        for stories in by_epic.values():
            if len(batch) >= max_parallelism:
                break
            batch.append(stories[0])

        logger.info(f"[dag] Selected batch of {len(batch)} stories for parallel execution")
        return batch

    def topological_sort(self) -> List[str]:
        """Return stories in topological order (dependencies first)."""
        # Build in_degree: count how many dependencies each story has
        in_degree = {node: 0 for node in self.nodes}

        # For each story, for each of its dependencies, increment the dependency's in_degree
        for story_id, deps in self.edges.items():
            in_degree[story_id] = len(deps)  # This story depends on N others

        # Start with stories that have no dependencies
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        sorted_order = []

        while queue:
            node = queue.popleft()
            sorted_order.append(node)

            # For each story that depends on this node
            for dependent in self.reverse_edges.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(sorted_order) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return sorted_order
