#!/usr/bin/env python3
"""
tatlam/cli/run_swarm.py - CLI Entry Point for LangGraph Swarm

This script replaces run_batch.py with the new multi-agent system.
It provides a clean CLI interface for batch scenario generation.

Usage:
    python -m tatlam.cli.run_swarm --category "חפץ חשוד ומטען" --count 5
    python -m tatlam.cli.run_swarm --category "אדם חשוד" --count 10 --threshold 80

Features:
    - Progress logging with structured output
    - Category validation
    - Configurable parameters
    - Error handling with detailed reports
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_valid_categories() -> list[str]:
    """Get list of valid category names."""
    from tatlam.core.categories import CATS
    return [meta.get("title", "") for meta in CATS.values() if meta.get("title")]


def validate_category(category: str) -> str:
    """Validate and normalize category name."""
    from tatlam.core.categories import category_to_slug, CATS

    slug = category_to_slug(category)
    if slug is None:
        valid = get_valid_categories()
        raise ValueError(
            f"Invalid category: '{category}'. Valid categories:\n" +
            "\n".join(f"  - {c}" for c in valid)
        )

    # Return the canonical Hebrew name
    meta = CATS.get(slug, {})
    return meta.get("title", category)


def run_sync(args: argparse.Namespace) -> int:
    """Run synchronous generation."""
    from tatlam.graph.workflow import run_scenario_generation

    logger = logging.getLogger(__name__)

    logger.info("Starting swarm generation (sync mode)")
    logger.info("Category: %s", args.category)
    logger.info("Target count: %d", args.count)
    logger.info("Score threshold: %.1f", args.threshold)

    try:
        result = run_scenario_generation(
            category=args.category,
            target_count=args.count,
            score_threshold=args.threshold,
            max_iterations=args.max_iterations,
            batch_size=args.batch_size,
        )
    except Exception as e:
        logger.error("Generation failed: %s", e)
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Bundle ID: {result.bundle_id}")
    print(f"Category: {result.category}")
    print(f"Approved: {len(result.approved_scenarios)}")
    print(f"Rejected: {len(result.rejected_scenarios)}")
    print(f"Iterations: {result.iteration}")

    if result.metrics:
        print(f"\nMetrics:")
        print(f"  Average Score: {result.metrics.average_score:.1f}")
        print(f"  Highest Score: {result.metrics.highest_score:.1f}")
        print(f"  Duplicates Skipped: {result.metrics.total_duplicates_skipped}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors[:5]:
            print(f"  - {err}")

    print("\nApproved Scenarios:")
    for sc in result.approved_scenarios:
        print(f"  - {sc.title} (score: {sc.score:.1f})")

    print("=" * 60)

    return 0 if result.approved_scenarios else 1


async def run_async(args: argparse.Namespace) -> int:
    """Run asynchronous generation."""
    from tatlam.graph.workflow import run_scenario_generation_async

    logger = logging.getLogger(__name__)

    logger.info("Starting swarm generation (async mode)")
    logger.info("Category: %s", args.category)
    logger.info("Target count: %d", args.count)

    try:
        result = await run_scenario_generation_async(
            category=args.category,
            target_count=args.count,
            score_threshold=args.threshold,
            max_iterations=args.max_iterations,
            batch_size=args.batch_size,
        )
    except Exception as e:
        logger.error("Async generation failed: %s", e)
        return 1

    # Print summary (same as sync)
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE (ASYNC)")
    print("=" * 60)
    print(f"Bundle ID: {result.bundle_id}")
    print(f"Approved: {len(result.approved_scenarios)}")
    print("=" * 60)

    return 0 if result.approved_scenarios else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate security scenarios using LangGraph multi-agent swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --category "חפץ חשוד ומטען" --count 5
    %(prog)s --category "אדם חשוד" --count 10 --threshold 80
    %(prog)s --category "רכב חשוד" --async --verbose

Valid Categories:
    - חפץ חשוד ומטען (Suspicious Object)
    - אדם חשוד (Suspicious Person)
    - רכב חשוד (Suspicious Vehicle)
    - איום אווירי (Aerial Threat)
    - הפרת סדר (Public Disturbance)
    - חירום (Emergency)
        """,
    )

    parser.add_argument(
        "--category", "-c",
        required=True,
        help="Scenario category (Hebrew name)",
    )

    parser.add_argument(
        "--count", "-n",
        type=int,
        default=5,
        help="Number of scenarios to generate (default: 5)",
    )

    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=70.0,
        help="Minimum score to approve scenario (default: 70.0)",
    )

    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=5,
        help="Maximum generation iterations (default: 5)",
    )

    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=8,
        help="Candidates per generation cycle (default: 8)",
    )

    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use async execution",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without running",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Validate category
    try:
        args.category = validate_category(args.category)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Dry run
    if args.dry_run:
        print("DRY RUN - Would generate:")
        print(f"  Category: {args.category}")
        print(f"  Count: {args.count}")
        print(f"  Threshold: {args.threshold}")
        print(f"  Max Iterations: {args.max_iterations}")
        print(f"  Batch Size: {args.batch_size}")
        print(f"  Async: {args.use_async}")
        return 0

    # Run
    if args.use_async:
        return asyncio.run(run_async(args))
    else:
        return run_sync(args)


if __name__ == "__main__":
    sys.exit(main())
