"""
tatlam/graph/nodes/deduplicator.py - The Deduplicator Node

The Deduplicator checks for duplicate scenarios early in the pipeline,
before wasting resources on Judge evaluation.

Key Features:
- Uses embeddings for semantic similarity
- Leverages existing load_all_embeddings from run_batch.py
- Marks duplicates for regeneration
- Logs dedup statistics
"""
from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np

from tatlam.graph.state import SwarmState, ScenarioCandidate, ScenarioStatus, WorkflowPhase
from tatlam.settings import get_settings

logger = logging.getLogger(__name__)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _embed_text(text: str) -> np.ndarray | None:
    """Embed text using the cloud OpenAI embeddings API."""
    from tatlam.core.llm_factory import client_cloud, ConfigurationError

    settings = get_settings()

    try:
        cloud = client_cloud()
        response = cloud.embeddings.create(
            model=settings.EMBED_MODEL,
            input=text
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except (ConfigurationError, Exception) as e:
        logger.warning("Failed to embed text: %s", e)
        return None


def _load_existing_embeddings() -> tuple[list[str], list[np.ndarray]]:
    """Load all existing embeddings from the database."""
    from tatlam.infra.db import get_session
    from tatlam.infra.models import ScenarioEmbedding
    from sqlalchemy import select

    titles: list[str] = []
    vectors: list[np.ndarray] = []

    try:
        with get_session() as session:
            stmt = select(ScenarioEmbedding.title, ScenarioEmbedding.vector_json)
            for title, vjson in session.execute(stmt):
                if not title or not vjson:
                    continue
                try:
                    vec = np.array(json.loads(vjson), dtype=np.float32)
                    if vec.size > 0:
                        titles.append(title)
                        vectors.append(vec)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug("Failed to parse embedding for %s: %s", title, e)
    except Exception as e:
        logger.warning("Failed to load embeddings: %s", e)

    return titles, vectors


def _is_duplicate(
    title: str,
    background: str,
    existing_titles: list[str],
    existing_vectors: list[np.ndarray],
    batch_vectors: list[tuple[str, np.ndarray]],
    threshold: float,
) -> tuple[bool, np.ndarray | None]:
    """
    Check if a scenario is a duplicate.

    Args:
        title: Scenario title
        background: Scenario background text
        existing_titles: Titles from database
        existing_vectors: Embeddings from database
        batch_vectors: Vectors from current batch (for cross-checking)
        threshold: Similarity threshold

    Returns:
        (is_duplicate, embedding)
    """
    # Create embedding
    text = f"{title}\n{background}".strip()
    vec = _embed_text(text)

    if vec is None:
        return False, None

    # Check against database
    for existing_vec in existing_vectors:
        sim = _cosine_similarity(vec, existing_vec)
        if sim >= threshold:
            logger.debug("Duplicate found (DB): similarity=%.3f >= %.3f", sim, threshold)
            return True, vec

    # Check against current batch
    for _, batch_vec in batch_vectors:
        sim = _cosine_similarity(vec, batch_vec)
        if sim >= threshold:
            logger.debug("Duplicate found (batch): similarity=%.3f >= %.3f", sim, threshold)
            return True, vec

    return False, vec


def deduplicator_node(state: SwarmState) -> SwarmState:
    """
    Deduplicator Node: Check for duplicate scenarios.

    This node:
    1. Loads existing embeddings from the database
    2. Checks each formatted candidate for duplicates
    3. Marks duplicates as REJECTED with critique
    4. Marks unique scenarios as UNIQUE
    5. Stores embeddings for later archiving

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState with dedup results
    """
    state.log_phase_change(WorkflowPhase.DEDUPLICATING)

    # Find formatted candidates to check
    candidates_to_check = [
        c for c in state.candidates
        if c.status == ScenarioStatus.FORMATTED
    ]

    if not candidates_to_check:
        logger.info("Deduplicator: No formatted candidates to check")
        return state

    logger.info("Deduplicator checking %d candidates", len(candidates_to_check))

    # Load existing embeddings
    existing_titles, existing_vectors = _load_existing_embeddings()
    logger.debug("Loaded %d existing embeddings from DB", len(existing_titles))

    # Also consider already-approved scenarios in this batch
    batch_vectors: list[tuple[str, np.ndarray]] = []

    duplicates_found = 0
    unique_found = 0

    for candidate in candidates_to_check:
        title = candidate.title
        background = candidate.data.get("background", "")

        is_dup, vec = _is_duplicate(
            title,
            background,
            existing_titles,
            existing_vectors,
            batch_vectors,
            state.diversity_threshold,
        )

        if is_dup:
            candidate.status = ScenarioStatus.REJECTED
            candidate.critique = "כותרת/תוכן דומים מדי לתרחיש קיים"
            duplicates_found += 1
            state.metrics.total_duplicates_skipped += 1
            logger.debug("Marked as duplicate: %s", title)
        else:
            candidate.status = ScenarioStatus.UNIQUE
            unique_found += 1

            # Store embedding for cross-checking in batch
            if vec is not None:
                batch_vectors.append((title, vec))
                # Store embedding in candidate data for Archivist
                candidate.data["_embedding"] = vec.tolist()

    logger.info(
        "Deduplicator completed: %d unique, %d duplicates",
        unique_found, duplicates_found
    )

    return state


__all__ = ["deduplicator_node"]
