"""
Heuristic-based story complexity analyzer.

Analyzes story descriptions and acceptance criteria to automatically
classify complexity as simple, medium, or complex without using LLM.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# Keyword dictionaries for complexity classification
SIMPLE_KEYWORDS = [
    'crud', 'get', 'post', 'put', 'delete', 'list', 'view', 'display',
    'show', 'basic', 'simple', 'endpoint', 'health', 'status', 'ping',
    'read', 'write', 'create', 'update', 'fetch', 'retrieve'
]

MEDIUM_KEYWORDS = [
    'api', 'integration', 'auth', 'authentication', 'authorization',
    'validation', 'state', 'cache', 'caching', 'queue', 'async',
    'webhook', 'notification', 'email', 'search', 'filter', 'pagination',
    'session', 'cookie', 'jwt', 'oauth', 'middleware', 'proxy'
]

COMPLEX_KEYWORDS = [
    'distributed', 'microservice', 'architecture', 'migration', 'refactor',
    'security', 'encryption', 'scalability', 'multi-tenant', 'consensus',
    'orchestration', 'saga', 'event-sourcing', 'cqrs', 'sharding',
    'replication', 'partition', 'load-balance', 'failover', 'redundancy'
]

DEPTH_INDICATORS = {
    'database': 5,
    'schema': 5,
    'migration': 10,
    'transaction': 5,
    'lock': 5,
    'index': 3,
    'optimization': 5,
    'performance': 5,
    'algorithm': 10,
    'concurrent': 10,
    'thread': 8,
    'process': 5,
    'benchmark': 5,
    'profiling': 5,
    'monitoring': 3,
    'observability': 5,
    'tracing': 5,
    'circuit-breaker': 8,
    'retry': 3,
    'backoff': 3,
    'idempotent': 5,
    'eventual-consistency': 8,
}


def analyze_story_complexity(story: Dict[str, Any], verbose: bool = False) -> str:
    """
    Analyzes a story and returns complexity: simple | medium | complex
    based on heuristics (no LLM required).

    Scoring system (0-100):
    - Keywords (40 points max): Presence of simple/medium/complex keywords
    - Acceptance criteria count (30 points max): More criteria = more complex
    - Description length (15 points max): Longer descriptions = more complex
    - Technical depth (15 points max): Database, concurrency, performance terms

    Thresholds:
    - 0-34: simple
    - 35-64: medium
    - 65-100: complex

    Args:
        story: Story dict with 'description' and 'acceptance' fields
        verbose: If True, logs detailed scoring breakdown

    Returns:
        Complexity level: 'simple', 'medium', or 'complex'
    """
    description = story.get('description', '').lower()
    acceptance = story.get('acceptance', [])
    story_id = story.get('id', '?')

    score = 0
    breakdown = {}

    # 1. KEYWORDS DETECTION (40 points maximum)
    keyword_score = 0
    matched_keywords = []

    if any(kw in description for kw in COMPLEX_KEYWORDS):
        keyword_score = 40
        matched_keywords = [kw for kw in COMPLEX_KEYWORDS if kw in description]
    elif any(kw in description for kw in MEDIUM_KEYWORDS):
        keyword_score = 25
        matched_keywords = [kw for kw in MEDIUM_KEYWORDS if kw in description]
    elif any(kw in description for kw in SIMPLE_KEYWORDS):
        keyword_score = 10
        matched_keywords = [kw for kw in SIMPLE_KEYWORDS if kw in description]
    else:
        keyword_score = 20  # default when no keywords match

    score += keyword_score
    breakdown['keywords'] = {
        'score': keyword_score,
        'matched': matched_keywords[:3]  # Show first 3 matches
    }

    # 2. ACCEPTANCE CRITERIA COUNT (30 points maximum)
    criteria_count = len(acceptance)
    if criteria_count <= 2:
        criteria_score = 10
    elif criteria_count <= 4:
        criteria_score = 20
    else:
        criteria_score = 30

    score += criteria_score
    breakdown['acceptance_criteria'] = {
        'score': criteria_score,
        'count': criteria_count
    }

    # 3. DESCRIPTION LENGTH (15 points maximum)
    desc_words = len(description.split())
    if desc_words < 20:
        length_score = 5
    elif desc_words < 50:
        length_score = 10
    else:
        length_score = 15

    score += length_score
    breakdown['description_length'] = {
        'score': length_score,
        'words': desc_words
    }

    # 4. TECHNICAL DEPTH INDICATORS (15 points maximum)
    depth_score = 0
    matched_indicators = []

    for keyword, points in DEPTH_INDICATORS.items():
        if keyword in description:
            depth_score += points
            matched_indicators.append(keyword)

    depth_score = min(depth_score, 15)  # Cap at 15
    score += depth_score
    breakdown['technical_depth'] = {
        'score': depth_score,
        'indicators': matched_indicators[:3]  # Show first 3
    }

    # 5. CLASSIFICATION
    if score < 35:
        complexity = 'simple'
    elif score < 65:
        complexity = 'medium'
    else:
        complexity = 'complex'

    # Logging
    if verbose:
        logger.info(f"[complexity_analyzer] Story {story_id} → {complexity} (score={score}/100)")
        logger.debug(f"  Keywords: {breakdown['keywords']}")
        logger.debug(f"  Acceptance: {breakdown['acceptance_criteria']}")
        logger.debug(f"  Length: {breakdown['description_length']}")
        logger.debug(f"  Depth: {breakdown['technical_depth']}")

    return complexity


def analyze_stories_batch(stories: List[Dict[str, Any]], verbose: bool = False) -> Dict[str, str]:
    """
    Analyze multiple stories in batch.

    Args:
        stories: List of story dicts
        verbose: If True, logs detailed scoring for each story

    Returns:
        Dict mapping story_id -> complexity
    """
    results = {}
    for story in stories:
        story_id = story.get('id', '?')
        complexity = analyze_story_complexity(story, verbose=verbose)
        results[story_id] = complexity

    return results


def get_complexity_distribution(stories: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get distribution of complexity levels across stories.

    Args:
        stories: List of story dicts

    Returns:
        Dict with counts: {'simple': N, 'medium': N, 'complex': N}
    """
    distribution = {'simple': 0, 'medium': 0, 'complex': 0}

    for story in stories:
        complexity = analyze_story_complexity(story)
        distribution[complexity] += 1

    return distribution
