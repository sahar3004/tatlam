"""
tatlam/graph/nodes - LangGraph Node Implementations

Each node is a pure function that:
1. Takes SwarmState as input
2. Performs a single, focused task
3. Returns updated SwarmState

Nodes:
- writer: Generates scenario candidates using local LLM
- clerk: Validates and formats JSON structure
- deduplicator: Checks for duplicate titles
- judge: Evaluates quality and doctrine compliance
- archivist: Saves approved scenarios to database
- supervisor: Orchestrates the workflow
"""

from __future__ import annotations

from tatlam.graph.nodes.archivist import archivist_node
from tatlam.graph.nodes.clerk import clerk_node
from tatlam.graph.nodes.deduplicator import deduplicator_node
from tatlam.graph.nodes.judge import judge_node
from tatlam.graph.nodes.supervisor import should_continue, supervisor_node
from tatlam.graph.nodes.writer import writer_node

__all__ = [
    "writer_node",
    "clerk_node",
    "deduplicator_node",
    "judge_node",
    "archivist_node",
    "supervisor_node",
    "should_continue",
]
