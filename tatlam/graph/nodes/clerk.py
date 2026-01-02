"""
tatlam/graph/nodes/clerk.py - The Clerk (Formatter) Node

The Clerk validates and transforms raw LLM output into structured JSON.
It uses the cloud LLM to enforce JSON structure and leverages existing
coerce_bundle_shape for normalization.

Key Features:
- Parses markdown/text to JSON using cloud LLM
- Validates against SCENARIO_BUNDLE_SCHEMA
- Coerces fields to correct types
- Handles multi-scenario bundles
"""

from __future__ import annotations

import logging
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tatlam.core.bundles import coerce_bundle_shape
from tatlam.core.utils import strip_markdown_and_parse_json
from tatlam.graph.state import ScenarioCandidate, ScenarioStatus, SwarmState, WorkflowPhase
from tatlam.settings import get_settings

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _refine_to_json(client: Any, model: str, draft_text: str) -> str:
    """Call cloud LLM to convert draft text to JSON."""
    from tatlam.core.doctrine import get_system_prompt

    system_prompt = get_system_prompt("clerk")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": draft_text},
        ],
        response_format={"type": "json_object"},
    )
    return (response.choices[0].message.content or "").strip()


def _parse_and_validate(text: str, state: SwarmState) -> list[dict[str, Any]]:
    """
    Parse JSON text and validate structure.

    Returns:
        List of validated scenario dictionaries
    """
    # Try to parse JSON
    data = strip_markdown_and_parse_json(text)

    if data is None:
        logger.warning("Failed to parse JSON from text")
        return []

    # Normalize to bundle format
    if isinstance(data, dict) and "scenarios" in data:
        bundle = {"bundle_id": state.bundle_id, "scenarios": data.get("scenarios", [])}
    elif isinstance(data, list):
        bundle = {"bundle_id": state.bundle_id, "scenarios": data}
    elif isinstance(data, dict):
        # Single scenario
        bundle = {"bundle_id": state.bundle_id, "scenarios": [data]}
    else:
        logger.warning("Unexpected data type: %s", type(data))
        return []

    # Apply type coercion
    bundle = coerce_bundle_shape(bundle)

    scenarios = bundle.get("scenarios", [])

    # Filter out invalid scenarios
    valid_scenarios = []
    for sc in scenarios:
        if not sc.get("title"):
            logger.debug("Skipping scenario without title")
            continue
        if not sc.get("category"):
            sc["category"] = state.category  # Default to state category
        valid_scenarios.append(sc)

    return valid_scenarios


def clerk_node(state: SwarmState) -> SwarmState:
    """
    Clerk Node: Validate and format raw drafts into structured JSON.

    This node:
    1. Finds raw draft candidates from the Writer
    2. Calls cloud LLM to convert to JSON
    3. Validates and coerces the structure
    4. Creates individual ScenarioCandidates for each scenario
    5. Removes the raw draft candidates

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState with formatted candidates
    """
    state.log_phase_change(WorkflowPhase.FORMATTING)

    # Find raw drafts to process
    raw_candidates = [
        c
        for c in state.candidates
        if c.data.get("_is_raw_draft") and c.status == ScenarioStatus.DRAFT
    ]

    if not raw_candidates:
        logger.info("Clerk: No raw drafts to process")
        return state

    logger.info("Clerk processing %d raw drafts", len(raw_candidates))

    # Get cloud client for JSON refinement
    from tatlam.core.llm_factory import ConfigurationError, client_cloud

    cloud_client = None
    try:
        cloud_client = client_cloud()
    except (ConfigurationError, Exception) as e:
        logger.error("Cloud client unavailable for Clerk: %s", e)
        state.add_error(f"Clerk failed: cloud client unavailable. {e}")
        return state

    settings = get_settings()
    new_candidates: list[ScenarioCandidate] = []

    for raw_candidate in raw_candidates:
        draft_text = raw_candidate.data.get("_raw_text", "")
        if not draft_text:
            continue

        # Step 1: Refine to JSON using cloud LLM
        refined_text = ""
        try:
            refined_text = _refine_to_json(cloud_client, settings.GEN_MODEL, draft_text)
        except Exception as e:
            logger.warning("JSON refinement failed: %s", e)
            state.metrics.llm_errors += 1

            # Try one more time with different prompt
            try:
                refined_text = _refine_to_json(
                    cloud_client,
                    settings.GEN_MODEL,
                    f"הפוך את הטקסט הבא ל-JSON חוקי עם scenarios: [...]\n\n{draft_text}",
                )
            except Exception as e2:
                logger.error("Second refinement attempt failed: %s", e2)
                state.metrics.parse_errors += 1
                state.add_error(f"Clerk JSON refinement failed: {e2}")
                continue

        # Step 2: Parse and validate
        scenarios = _parse_and_validate(refined_text, state)

        if not scenarios:
            # Fallback: try parsing the original draft
            scenarios = _parse_and_validate(draft_text, state)

        if not scenarios:
            logger.warning("Clerk: No valid scenarios extracted from draft")
            state.metrics.parse_errors += 1
            continue

        # Step 3: Create individual candidates
        for sc in scenarios:
            # Ensure bundle_id is set
            sc["bundle_id"] = state.bundle_id

            candidate = ScenarioCandidate(
                data=sc,
                status=ScenarioStatus.FORMATTED,
            )
            new_candidates.append(candidate)
            logger.debug("Clerk formatted: %s", candidate.title)

        # Mark raw candidate as processed (we'll remove it)
        raw_candidate.status = ScenarioStatus.ARCHIVED

    # Remove raw drafts and add formatted candidates
    state.candidates = [c for c in state.candidates if not c.data.get("_is_raw_draft")]
    state.candidates.extend(new_candidates)

    logger.info(
        "Clerk completed: created %d formatted candidates from raw drafts", len(new_candidates)
    )

    return state


__all__ = ["clerk_node"]
