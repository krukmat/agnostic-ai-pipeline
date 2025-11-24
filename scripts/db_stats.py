"""
Fase 5: CLI de observabilidad para la base de datos.

Provee estadísticas sobre proyectos, iteraciones, stories y uso de modelos.

Usage:
    python scripts/db_stats.py                    # Resumen general
    python scripts/db_stats.py --project NAME     # Stats de un proyecto
    python scripts/db_stats.py --models           # Stats por modelo
    python scripts/db_stats.py --costs            # Resumen de costos
    python scripts/db_stats.py --json             # Output JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.db.storage import get_db, is_db_enabled
from src.db.repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    EventLogRepository,
)
from logger import logger


def get_overview_stats(db) -> Dict[str, Any]:
    """Get high-level overview statistics."""
    projects = ProjectRepository(db)
    iterations = IterationRepository(db)

    all_projects = projects.list_all()

    # Count iterations
    total_iterations = db.fetchone("SELECT COUNT(*) as cnt FROM iterations")["cnt"]

    # Count stories
    total_stories = db.fetchone("SELECT COUNT(*) as cnt FROM stories")["cnt"]

    # Story status breakdown
    status_counts = db.fetchall("""
        SELECT status, COUNT(*) as cnt
        FROM stories
        GROUP BY status
    """)

    # Count attempts
    total_attempts = db.fetchone("SELECT COUNT(*) as cnt FROM story_attempts")["cnt"]

    # Success rate
    success_attempts = db.fetchone(
        "SELECT COUNT(*) as cnt FROM story_attempts WHERE status = 'success'"
    )["cnt"]

    success_rate = (success_attempts / total_attempts * 100) if total_attempts > 0 else 0

    return {
        "projects": len(all_projects),
        "iterations": total_iterations,
        "stories": {
            "total": total_stories,
            "by_status": {row["status"]: row["cnt"] for row in status_counts},
        },
        "attempts": {
            "total": total_attempts,
            "successful": success_attempts,
            "success_rate": round(success_rate, 2),
        },
    }


def get_project_stats(db, project_name: str) -> Optional[Dict[str, Any]]:
    """Get statistics for a specific project."""
    projects = ProjectRepository(db)
    project = projects.get_by_name(project_name)

    if not project:
        return None

    project_id = project["id"]

    # Get iterations
    iterations = db.fetchall(
        "SELECT * FROM iterations WHERE project_id = ? ORDER BY started_at DESC",
        (project_id,)
    )

    # Get stories across all iterations
    stories = db.fetchall("""
        SELECT s.* FROM stories s
        JOIN iterations i ON s.iteration_id = i.id
        WHERE i.project_id = ?
    """, (project_id,))

    # Status breakdown
    status_counts = {}
    for s in stories:
        status = s["status"] or "todo"
        status_counts[status] = status_counts.get(status, 0) + 1

    # Get attempts
    attempts = db.fetchall("""
        SELECT sa.* FROM story_attempts sa
        JOIN stories s ON sa.story_id = s.id
        JOIN iterations i ON s.iteration_id = i.id
        WHERE i.project_id = ?
    """, (project_id,))

    # Attempts by role
    attempts_by_role = {}
    for a in attempts:
        role = a["role"]
        attempts_by_role[role] = attempts_by_role.get(role, 0) + 1

    return {
        "project": {
            "id": project_id,
            "name": project["name"],
            "concept": project["concept"][:100] + "..." if len(project["concept"]) > 100 else project["concept"],
            "status": project["status"],
            "created_at": project["created_at"],
        },
        "iterations": len(iterations),
        "stories": {
            "total": len(stories),
            "by_status": status_counts,
        },
        "attempts": {
            "total": len(attempts),
            "by_role": attempts_by_role,
        },
    }


def get_model_stats(db) -> List[Dict[str, Any]]:
    """Get statistics by provider/model."""
    rows = db.fetchall("""
        SELECT
            provider,
            model,
            role,
            COUNT(*) as total_attempts,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
            AVG(duration_ms) as avg_duration_ms,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(cost_usd) as total_cost_usd
        FROM story_attempts
        GROUP BY provider, model, role
        ORDER BY total_attempts DESC
    """)

    result = []
    for row in rows:
        total = row["total_attempts"]
        successes = row["successes"] or 0
        success_rate = (successes / total * 100) if total > 0 else 0

        result.append({
            "provider": row["provider"],
            "model": row["model"],
            "role": row["role"],
            "attempts": total,
            "successes": successes,
            "errors": row["errors"] or 0,
            "success_rate": round(success_rate, 2),
            "avg_duration_ms": round(row["avg_duration_ms"] or 0, 0),
            "tokens_in": row["total_tokens_in"] or 0,
            "tokens_out": row["total_tokens_out"] or 0,
            "cost_usd": round(row["total_cost_usd"] or 0, 4),
        })

    return result


def get_cost_summary(db) -> Dict[str, Any]:
    """Get cost summary across all attempts."""
    # Overall costs
    overall = db.fetchone("""
        SELECT
            COUNT(*) as total_attempts,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(cost_usd) as total_cost_usd
        FROM story_attempts
    """)

    # Costs by provider
    by_provider = db.fetchall("""
        SELECT
            provider,
            SUM(tokens_in) as tokens_in,
            SUM(tokens_out) as tokens_out,
            SUM(cost_usd) as cost_usd
        FROM story_attempts
        GROUP BY provider
        ORDER BY cost_usd DESC
    """)

    # Costs by role
    by_role = db.fetchall("""
        SELECT
            role,
            SUM(tokens_in) as tokens_in,
            SUM(tokens_out) as tokens_out,
            SUM(cost_usd) as cost_usd
        FROM story_attempts
        GROUP BY role
        ORDER BY cost_usd DESC
    """)

    return {
        "total": {
            "attempts": overall["total_attempts"],
            "tokens_in": overall["total_tokens_in"] or 0,
            "tokens_out": overall["total_tokens_out"] or 0,
            "cost_usd": round(overall["total_cost_usd"] or 0, 4),
        },
        "by_provider": [
            {
                "provider": row["provider"],
                "tokens_in": row["tokens_in"] or 0,
                "tokens_out": row["tokens_out"] or 0,
                "cost_usd": round(row["cost_usd"] or 0, 4),
            }
            for row in by_provider
        ],
        "by_role": [
            {
                "role": row["role"],
                "tokens_in": row["tokens_in"] or 0,
                "tokens_out": row["tokens_out"] or 0,
                "cost_usd": round(row["cost_usd"] or 0, 4),
            }
            for row in by_role
        ],
    }


def get_recent_events(db, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent events from event log."""
    events = EventLogRepository(db)
    recent = events.list_recent(limit=limit)

    return [
        {
            "timestamp": row["timestamp"],
            "event_type": row["event_type"],
            "role": row["role"],
            "severity": row["severity"],
            "message": row["message"][:100] if row["message"] else None,
        }
        for row in recent
    ]


def print_overview(stats: Dict[str, Any]) -> None:
    """Print overview stats in human-readable format."""
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS OVERVIEW")
    print("=" * 60)

    print(f"\nProjects: {stats['projects']}")
    print(f"Iterations: {stats['iterations']}")

    print(f"\nStories: {stats['stories']['total']}")
    for status, count in stats['stories']['by_status'].items():
        print(f"  - {status}: {count}")

    print(f"\nAttempts: {stats['attempts']['total']}")
    print(f"  - Successful: {stats['attempts']['successful']}")
    print(f"  - Success Rate: {stats['attempts']['success_rate']}%")

    print("\n" + "=" * 60)


def print_model_stats(models: List[Dict[str, Any]]) -> None:
    """Print model stats in table format."""
    print("\n" + "=" * 80)
    print("MODEL STATISTICS")
    print("=" * 80)

    if not models:
        print("No model data available.")
        return

    # Header
    print(f"{'Provider':<15} {'Model':<25} {'Role':<10} {'Attempts':<10} {'Success%':<10} {'Avg(ms)':<10}")
    print("-" * 80)

    for m in models:
        print(f"{m['provider']:<15} {m['model'][:24]:<25} {m['role']:<10} {m['attempts']:<10} {m['success_rate']:<10} {m['avg_duration_ms']:<10.0f}")

    print("=" * 80)


def print_costs(costs: Dict[str, Any]) -> None:
    """Print cost summary."""
    print("\n" + "=" * 60)
    print("COST SUMMARY")
    print("=" * 60)

    total = costs['total']
    print(f"\nTotal Attempts: {total['attempts']}")
    print(f"Total Tokens In: {total['tokens_in']:,}")
    print(f"Total Tokens Out: {total['tokens_out']:,}")
    print(f"Total Cost: ${total['cost_usd']:.4f}")

    if costs['by_provider']:
        print("\nBy Provider:")
        for p in costs['by_provider']:
            print(f"  {p['provider']}: ${p['cost_usd']:.4f} ({p['tokens_in']:,} in, {p['tokens_out']:,} out)")

    if costs['by_role']:
        print("\nBy Role:")
        for r in costs['by_role']:
            print(f"  {r['role']}: ${r['cost_usd']:.4f} ({r['tokens_in']:,} in, {r['tokens_out']:,} out)")

    print("\n" + "=" * 60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database statistics and observability CLI"
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Show stats for specific project"
    )
    parser.add_argument(
        "--models", "-m",
        action="store_true",
        help="Show model statistics"
    )
    parser.add_argument(
        "--costs", "-c",
        action="store_true",
        help="Show cost summary"
    )
    parser.add_argument(
        "--events", "-e",
        type=int,
        nargs="?",
        const=20,
        help="Show recent events (default: 20)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Check if DB is enabled
    if not is_db_enabled():
        logger.error("[STATS] Database is not enabled. Set database.enabled: true in config.yaml")
        sys.exit(1)

    db = get_db()

    # Collect requested data
    result = {}

    if args.project:
        stats = get_project_stats(db, args.project)
        if not stats:
            logger.error(f"[STATS] Project not found: {args.project}")
            sys.exit(1)
        result["project_stats"] = stats
    elif args.models:
        result["model_stats"] = get_model_stats(db)
    elif args.costs:
        result["cost_summary"] = get_cost_summary(db)
    elif args.events:
        result["recent_events"] = get_recent_events(db, args.events)
    else:
        result["overview"] = get_overview_stats(db)

    # Output
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "overview" in result:
            print_overview(result["overview"])
        if "project_stats" in result:
            stats = result["project_stats"]
            print(f"\nProject: {stats['project']['name']}")
            print(f"Concept: {stats['project']['concept']}")
            print(f"Status: {stats['project']['status']}")
            print(f"Iterations: {stats['iterations']}")
            print(f"Stories: {stats['stories']['total']}")
            for status, count in stats['stories']['by_status'].items():
                print(f"  - {status}: {count}")
            print(f"Attempts: {stats['attempts']['total']}")
            for role, count in stats['attempts']['by_role'].items():
                print(f"  - {role}: {count}")
        if "model_stats" in result:
            print_model_stats(result["model_stats"])
        if "cost_summary" in result:
            print_costs(result["cost_summary"])
        if "recent_events" in result:
            print("\nRecent Events:")
            for e in result["recent_events"]:
                print(f"  [{e['timestamp']}] {e['event_type']} ({e['role']}) - {e['message']}")


if __name__ == "__main__":
    main()
