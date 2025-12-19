#!/usr/bin/env python3
"""Database reindexing script for Tatlam.

This script ensures all required indexes exist on the scenarios table.
It's safe to run multiple times (idempotent).

Usage:
    python scripts/reindex_db.py

Indexes created:
    - ix_scenarios_category (for category filtering)
    - ix_scenarios_threat_level (for prioritization)
    - ix_scenarios_status (for approval filtering)
    - ix_scenarios_created_at (for sorting by date)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect

from tatlam.infra.db import get_engine
from tatlam.infra.models import Base, Scenario


def get_existing_indexes(engine) -> set[str]:
    """Get names of existing indexes on the scenarios table."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("scenarios")
    return {idx["name"] for idx in indexes if idx["name"]}


def create_indexes(engine) -> list[str]:
    """Create missing indexes on the scenarios table.

    Returns list of created index names.
    """
    created = []
    existing = get_existing_indexes(engine)

    # Define indexes that should exist
    required_indexes = {
        "ix_scenarios_category": "CREATE INDEX IF NOT EXISTS ix_scenarios_category ON scenarios (category)",
        "ix_scenarios_threat_level": "CREATE INDEX IF NOT EXISTS ix_scenarios_threat_level ON scenarios (threat_level)",
        "ix_scenarios_status": "CREATE INDEX IF NOT EXISTS ix_scenarios_status ON scenarios (status)",
        "ix_scenarios_created_at": "CREATE INDEX IF NOT EXISTS ix_scenarios_created_at ON scenarios (created_at)",
    }

    with engine.connect() as conn:
        for idx_name, create_sql in required_indexes.items():
            if idx_name not in existing:
                print(f"Creating index: {idx_name}")
                conn.execute(text(create_sql))
                created.append(idx_name)
            else:
                print(f"Index already exists: {idx_name}")
        conn.commit()

    return created


def verify_indexes(engine) -> bool:
    """Verify all required indexes exist."""
    existing = get_existing_indexes(engine)
    required = {
        "ix_scenarios_category",
        "ix_scenarios_threat_level",
        "ix_scenarios_status",
        "ix_scenarios_created_at",
    }

    missing = required - existing
    if missing:
        print(f"Missing indexes: {missing}")
        return False

    print("All required indexes are present")
    return True


def main():
    """Main entry point."""
    print("=" * 60)
    print("Tatlam Database Reindexing Script")
    print("=" * 60)

    engine = get_engine()

    # Check if table exists
    inspector = inspect(engine)
    if "scenarios" not in inspector.get_table_names():
        print("Error: 'scenarios' table does not exist!")
        print("Run the application first to create the schema.")
        return 1

    print(f"\nDatabase: {engine.url}")
    print("\nChecking and creating indexes...")

    created = create_indexes(engine)

    if created:
        print(f"\nCreated {len(created)} new indexes: {created}")
    else:
        print("\nNo new indexes needed to be created.")

    print("\nVerifying indexes...")
    if verify_indexes(engine):
        print("\n✔ Database indexing complete!")
        return 0
    else:
        print("\n✘ Some indexes are missing!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
