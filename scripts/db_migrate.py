#!/usr/bin/env python3
"""Database migration CLI - creates schema and manages migrations."""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.storage import get_db, reset_db
from src.db.schema import create_schema, get_schema_version, SCHEMA_VERSION


def main():
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/pipeline.db"),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate schema (drops existing)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check schema version without migrating",
    )

    args = parser.parse_args()

    # Reset singleton if custom path
    reset_db()
    db = get_db(args.db_path)

    current_version = get_schema_version(db)

    if args.check:
        print(f"Current schema version: {current_version}")
        print(f"Target schema version: {SCHEMA_VERSION}")
        if current_version < SCHEMA_VERSION:
            print("Migration needed")
            sys.exit(1)
        print("Schema is up to date")
        sys.exit(0)

    if args.force and args.db_path.exists():
        print(f"Removing existing database: {args.db_path}")
        db.close()
        reset_db()
        args.db_path.unlink()
        db = get_db(args.db_path)

    print(f"Database: {args.db_path}")
    print(f"Current version: {current_version}")
    print(f"Target version: {SCHEMA_VERSION}")

    if current_version >= SCHEMA_VERSION:
        print("Schema is already up to date")
        return

    print("Creating schema...")
    create_schema(db)

    new_version = get_schema_version(db)
    print(f"Schema migrated to version {new_version}")

    # Verify tables
    tables = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    print(f"Tables created: {[t['name'] for t in tables]}")


if __name__ == "__main__":
    main()
