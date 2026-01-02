"""
tatlam/graph/workflow.py - LangGraph Workflow Construction

This module builds the LangGraph StateGraph that orchestrates
the multi-agent scenario generation workflow.

Workflow (Scout-Curator Pipeline):
    init → scout → curator → writer → clerk → deduplicator → judge → supervisor
                                                                        ↓
                                                                ┌───────┴────────┐
                                                                ↓                ↓
                                                             writer           archivist
                                                          (repair mode)         ↓
                                                                               END

Key Features:
- Scout generates ideas with Local LLM (quantity)
- Curator filters with Cloud LLM (quality)
- Writer expands selected seeds into full scenarios
- Quality loop with repair cycles
- Early termination on success
"""
from __future__ import annotations

import logging
from typing import Any

from tatlam.graph.state import SwarmState, WorkflowPhase
from tatlam.graph.nodes.scout import scout_node
from tatlam.graph.nodes.curator import curator_node
from tatlam.graph.nodes.writer import writer_node
from tatlam.graph.nodes.clerk import clerk_node
from tatlam.graph.nodes.deduplicator import deduplicator_node
from tatlam.graph.nodes.judge import judge_node
from tatlam.graph.nodes.supervisor import supervisor_node, should_continue, init_supervisor
from tatlam.graph.nodes.archivist import archivist_node

logger = logging.getLogger(__name__)


def create_scenario_graph() -> Any:
    """
    Create the LangGraph StateGraph for scenario generation.

    The graph implements the Scout-Curator pipeline:
    1. Scout generates many idea seeds (Local LLM)
    2. Curator filters to best seeds (Cloud LLM)
    3. Writer expands seeds into full scenarios (Cloud LLM)
    4. Clerk formats to JSON
    5. Deduplicator removes duplicates
    6. Judge evaluates quality
    7. Supervisor decides: more/repair → Writer, done → Archivist

    Returns:
        Compiled LangGraph StateGraph

    Raises:
        ImportError: If langgraph is not installed
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        logger.error("langgraph not installed. Install with: pip install langgraph")
        raise ImportError(
            "langgraph is required for the graph workflow. "
            "Install with: pip install langgraph"
        )

    # Create the graph
    graph = StateGraph(SwarmState)

    # Add nodes
    graph.add_node("init", init_supervisor)
    graph.add_node("scout", scout_node)
    graph.add_node("curator", curator_node)
    graph.add_node("writer", writer_node)
    graph.add_node("clerk", clerk_node)
    graph.add_node("deduplicator", deduplicator_node)
    graph.add_node("judge", judge_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("archivist", archivist_node)

    # Add edges
    # Start → Init
    graph.set_entry_point("init")

    # Init → Scout → Curator → Writer (Scout-Curator Pipeline)
    graph.add_edge("init", "scout")
    graph.add_edge("scout", "curator")
    graph.add_edge("curator", "writer")

    # Linear flow: Writer → Clerk → Deduplicator → Judge → Supervisor
    graph.add_edge("writer", "clerk")
    graph.add_edge("clerk", "deduplicator")
    graph.add_edge("deduplicator", "judge")
    graph.add_edge("judge", "supervisor")

    # Conditional routing from Supervisor
    # Note: Repairs go directly to writer (bypassing scout/curator)
    graph.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "writer": "writer",      # Need more / repair (skip scout for repairs)
            "archivist": "archivist",  # Done, save to DB
            "end": END,              # Error or complete
        }
    )

    # Archivist → END
    graph.add_edge("archivist", END)

    # Compile and return
    compiled = graph.compile()

    logger.info("Scenario graph compiled successfully (Scout-Curator pipeline)")

    return compiled


def run_scenario_generation(
    category: str,
    target_count: int = 5,
    score_threshold: float = 70.0,
    max_iterations: int = 5,
    batch_size: int = 8,
) -> SwarmState:
    """
    Run the scenario generation workflow.

    This is the main entry point for generating scenarios.
    It creates the graph, initializes state, and runs the workflow.

    Args:
        category: The scenario category (e.g., "חפץ חשוד ומטען")
        target_count: Number of scenarios to generate
        score_threshold: Minimum score to approve (0-100)
        max_iterations: Maximum generation cycles
        batch_size: Candidates per generation cycle

    Returns:
        Final SwarmState with all results

    Example:
        from tatlam.graph import run_scenario_generation

        result = run_scenario_generation(
            category="חפץ חשוד ומטען",
            target_count=5,
        )

        print(f"Generated {len(result.approved_scenarios)} scenarios")
        for sc in result.approved_scenarios:
            print(f"  - {sc.title}")
    """
    # Create graph
    graph = create_scenario_graph()

    # Initialize state
    initial_state = SwarmState(
        category=category,
        target_count=target_count,
        score_threshold=score_threshold,
        max_iterations=max_iterations,
        batch_size=batch_size,
    )

    logger.info("Starting scenario generation for category: %s", category)

    # Run the graph
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error("Workflow failed: %s", e)
        initial_state.add_error(f"Workflow failed: {e}")
        initial_state.log_phase_change(WorkflowPhase.ERROR)
        return initial_state

    return final_state


async def run_scenario_generation_async(
    category: str,
    target_count: int = 5,
    score_threshold: float = 70.0,
    max_iterations: int = 5,
    batch_size: int = 8,
) -> SwarmState:
    """
    Async version of run_scenario_generation.

    Uses LangGraph's async capabilities for better performance
    when running multiple workflows concurrently.

    Args:
        Same as run_scenario_generation

    Returns:
        Final SwarmState with all results
    """
    # Create graph
    graph = create_scenario_graph()

    # Initialize state
    initial_state = SwarmState(
        category=category,
        target_count=target_count,
        score_threshold=score_threshold,
        max_iterations=max_iterations,
        batch_size=batch_size,
    )

    logger.info("Starting async scenario generation for category: %s", category)

    # Run the graph async
    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Async workflow failed: %s", e)
        initial_state.add_error(f"Async workflow failed: {e}")
        initial_state.log_phase_change(WorkflowPhase.ERROR)
        return initial_state

    return final_state


__all__ = [
    "create_scenario_graph",
    "run_scenario_generation",
    "run_scenario_generation_async",
]
