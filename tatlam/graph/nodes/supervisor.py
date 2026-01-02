"""
tatlam/graph/nodes/supervisor.py - The Supervisor (Mission Control)

The Supervisor orchestrates the entire workflow:
- Decides when to generate more scenarios
- Routes between Writer (for more/repairs) and Archivist (for saving)
- Prevents infinite loops
- Logs progress and metrics

This is the "brain" that drives the graph's conditional edges.
"""
from __future__ import annotations

import logging
from typing import Literal

from tatlam.graph.state import SwarmState, ScenarioStatus, WorkflowPhase

logger = logging.getLogger(__name__)


def supervisor_node(state: SwarmState) -> SwarmState:
    """
    Supervisor Node: Orchestrate the workflow.

    This node:
    1. Logs current progress
    2. Checks if we've reached target count
    3. Checks for scenarios that need repair
    4. Prepares state for next iteration

    Note: The actual routing decision is made by should_continue()

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState
    """
    approved_count = len(state.approved_scenarios)
    rejected_count = len(state.rejected_scenarios)
    pending_count = len(state.pending_scenarios)

    logger.info(
        "Supervisor: iteration=%d, approved=%d/%d, rejected=%d, pending=%d",
        state.iteration, approved_count, state.target_count,
        rejected_count, pending_count
    )

    # Check for scenarios that can be repaired (rejected but not exhausted retries)
    repairable = [
        c for c in state.candidates
        if c.status == ScenarioStatus.REJECTED
        and c.attempt_count <= state.max_retries_per_scenario
    ]

    if repairable:
        logger.info("Supervisor: %d scenarios can be repaired", len(repairable))
        state.metrics.total_repaired += len(repairable)

    # Log summary
    summary = state.get_summary()
    logger.debug("State summary: %s", summary)

    return state


def should_continue(state: SwarmState) -> Literal["writer", "archivist", "end"]:
    """
    Routing function for the LangGraph conditional edge.

    This function is called by the graph to determine the next node.

    Decision Logic:
    1. If we have enough approved scenarios → archivist
    2. If we've exceeded max iterations → archivist (with what we have)
    3. If there are repairable scenarios → writer (repair mode)
    4. If we need more scenarios → writer
    5. Otherwise → end (shouldn't happen)

    Args:
        state: Current SwarmState

    Returns:
        Next node name: "writer", "archivist", or "end"
    """
    approved_count = len(state.approved_scenarios)

    # Success: we have enough
    if approved_count >= state.target_count:
        logger.info("Target reached (%d/%d). Routing to archivist.", approved_count, state.target_count)
        return "archivist"

    # Safety: max iterations reached
    if state.iteration >= state.max_iterations:
        logger.warning(
            "Max iterations reached (%d). Routing to archivist with %d scenarios.",
            state.max_iterations, approved_count
        )
        if approved_count > 0:
            return "archivist"
        else:
            logger.error("No scenarios approved after max iterations. Ending.")
            state.log_phase_change(WorkflowPhase.ERROR)
            return "end"

    # Check for repairable scenarios
    repairable = [
        c for c in state.candidates
        if c.status == ScenarioStatus.REJECTED
        and c.attempt_count <= state.max_retries_per_scenario
    ]

    # If we have repairable scenarios, go to writer with repair mode
    if repairable:
        logger.info("Routing to writer for repair (%d scenarios)", len(repairable))
        return "writer"

    # Need more scenarios
    if state.needs_more:
        logger.info("Need more scenarios (%d/%d). Routing to writer.", approved_count, state.target_count)
        return "writer"

    # Fallback: should not happen
    logger.warning("Unexpected state. Routing to end.")
    return "end"


def init_supervisor(state: SwarmState) -> SwarmState:
    """
    Initialize the supervisor at the start of the workflow.

    This node:
    1. Validates inputs
    2. Initializes metrics
    3. Logs the mission scope

    Args:
        state: Initial SwarmState

    Returns:
        Initialized SwarmState
    """
    logger.info("=" * 50)
    logger.info("Mission Control Initialized")
    logger.info("=" * 50)
    logger.info("Bundle ID: %s", state.bundle_id)
    logger.info("Category: %s", state.category)
    logger.info("Target Count: %d", state.target_count)
    logger.info("Score Threshold: %.1f", state.score_threshold)
    logger.info("Max Retries: %d", state.max_retries_per_scenario)
    logger.info("Max Iterations: %d", state.max_iterations)
    logger.info("=" * 50)

    # Validate inputs
    if not state.category:
        state.add_error("Category is required")
        state.log_phase_change(WorkflowPhase.ERROR)
        return state

    if state.target_count < 1:
        state.add_error("Target count must be at least 1")
        state.log_phase_change(WorkflowPhase.ERROR)
        return state

    state.log_phase_change(WorkflowPhase.INIT)

    return state


__all__ = ["supervisor_node", "should_continue", "init_supervisor"]
