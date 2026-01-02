"""
tatlam/graph - LangGraph Multi-Agent System for Scenario Generation

This package implements a robust, observable multi-agent workflow using LangGraph.
It replaces the monolithic run_batch.py with a modular, testable architecture.

Architecture:
    Supervisor (Mission Control) → Writer → Clerk → Deduplicator → Judge → Archivist

Key Features:
    - Cyclic quality loop with feedback-driven regeneration
    - Early deduplication to prevent duplicate scenarios
    - Structured state management with full observability
    - Seamless integration with existing TrinityBrain

Usage:
    from tatlam.graph import create_scenario_graph, SwarmState

    # Create the graph
    graph = create_scenario_graph()

    # Run a batch
    initial_state = SwarmState(
        category="חפץ חשוד ומטען",
        target_count=5,
    )
    result = graph.invoke(initial_state)
"""

from __future__ import annotations

from tatlam.graph.state import ScenarioCandidate, SwarmMetrics, SwarmState
from tatlam.graph.workflow import create_scenario_graph

__all__ = [
    "SwarmState",
    "ScenarioCandidate",
    "SwarmMetrics",
    "create_scenario_graph",
]
