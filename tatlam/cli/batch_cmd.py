"""CLI command handler for batch scenario generation.

This module provides the command-line interface for the batch processing system.
Extracted from run_batch.py as part of Phase 2 architecture refactoring.
"""

from __future__ import annotations

import argparse
import os
import sys

from tatlam import configure_logging


def main() -> None:
    """Main entry point for batch command."""
    # Configure logging first
    configure_logging()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TATLAM Batch Scenario Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --category "פיגועים פשוטים"
  %(prog)s --category "חפץ חשוד ומטען" --owner Admin --async

Environment Variables:
  CANDIDATE_COUNT  Number of scenarios to generate (default: 8)
  KEEP_TOP_K       Number of top scenarios to keep (default: 5)
  GOLD_SCOPE       Scope for gold examples: category|all (default: category)
        """,
    )
    parser.add_argument(
        "--category",
        required=True,
        help="קטגוריה לייצור תטל״מים (חובה)",
    )
    parser.add_argument(
        "--owner",
        default="Sahar",
        help="שם הבעלים של התטל״מים (ברירת מחדל: Sahar)",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="השתמש בעיבוד async (מהיר יותר על M4 Pro)",
    )

    args = parser.parse_args()

    # Import here to avoid circular dependencies and keep startup fast
    # Import new workflow logic
    import asyncio

    from tatlam.graph.workflow import run_scenario_generation, run_scenario_generation_async

    # Execute batch processing
    try:
        # Default parameters for legacy batch command
        count = int(os.getenv("CANDIDATE_COUNT", "8"))

        if args.use_async:
            result_obj = asyncio.run(
                run_scenario_generation_async(category=args.category, target_count=count)
            )
        else:
            result_obj = run_scenario_generation(category=args.category, target_count=count)

        # Convert internal result object to dict-like logic if needed,
        # or just use attributes. The legacy code expects a dict with 'bundle_id'.
        # But run_scenario_generation returns a dataclass/pydantic object.
        bundle_id = result_obj.bundle_id
        scenario_count = len(result_obj.approved_scenarios)

        # Success

        print(f"\n✅ Batch complete: {bundle_id}")
        print(f"   Generated {scenario_count} scenarios")
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
