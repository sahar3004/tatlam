"""CLI command handler for batch scenario generation.

This module provides the command-line interface for the batch processing system.
Extracted from run_batch.py as part of Phase 2 architecture refactoring.
"""
from __future__ import annotations

import argparse
import sys

from tatlam import configure_logging
from tatlam.core.batch_logic import run_batch, run_batch_async


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

    # Execute batch processing
    try:
        if args.use_async:
            result = run_batch_async(args.category, owner=args.owner)
        else:
            result = run_batch(args.category, owner=args.owner)

        # Success
        bundle_id = result.get("bundle_id", "unknown")
        scenario_count = len(result.get("scenarios", []))
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
