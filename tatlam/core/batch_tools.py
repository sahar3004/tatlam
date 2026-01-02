"""Batch processing tools extracted from run_batch.py.

This module contains reusable logic for batch operations, enabling the decomposition
of the monolithic run_batch.py script. It serves as a bridge for legacy dependencies.
"""
from __future__ import annotations

import json
import logging
import os
import re
import asyncio
from typing import Any

import numpy as np
from sqlalchemy import select
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from openai import BadRequestError

from tatlam.settings import get_settings
from tatlam.core.llm_factory import client_cloud
from tatlam.core.utils import strip_markdown_and_parse_json
from tatlam.infra.db import get_session, init_db_sqlalchemy
from tatlam.infra.models import ScenarioEmbedding
from tatlam.core.validators import build_validator_prompt
from tatlam.infra.repo import insert_scenario, save_embedding

LOGGER = logging.getLogger(__name__)

_settings = get_settings()
DB_PATH = _settings.DB_PATH
EMBED_MODEL = _settings.EMBED_MODEL
VALIDATOR_MODEL = _settings.VALIDATOR_MODEL
SIM_THRESHOLD = _settings.SIM_THRESHOLD
CHECKER_MODEL = os.getenv("CHECKER_MODEL", "")

def ensure_db() -> None:
    """Ensure the database schema exists."""
    init_db_sqlalchemy()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(LOGGER, logging.WARNING),
    reraise=True,
)
def chat_create_safe(client, **kwargs):
    """
    Robust wrapper around client.chat.completions.create with professional retry logic.
    """
    payload = dict(kwargs)
    try:
        return client.chat.completions.create(**payload)
    except BadRequestError as err:
        # Special handling: if temperature is invalid, drop it and retry
        if "temperature" in str(err) and "temperature" in payload:
            LOGGER.debug("Dropping temperature parameter after BadRequestError")
            payload.pop("temperature", None)
            return client.chat.completions.create(**payload)
        raise

def embed_text(text: str) -> np.ndarray | None:
    try:
        cloud = client_cloud()
        r = cloud.embeddings.create(model=EMBED_MODEL, input=text)
        return np.array(r.data[0].embedding, dtype=np.float32)
    except Exception as e:
        LOGGER.warning("embed_text failed: %s", e)
        return None

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def load_all_embeddings():
    """Load all embeddings from DB used for duplicate detection."""
    titles, vecs = [], []
    try:
        with get_session() as session:
            stmt = select(ScenarioEmbedding.title, ScenarioEmbedding.vector_json)
            for title, vjson in session.execute(stmt):
                if not title or not vjson:
                    continue
                try:
                    vec = np.array(json.loads(vjson), dtype=np.float32)
                    if vec.size:
                        titles.append(title)
                        vecs.append(vec)
                except Exception as exc:
                    LOGGER.debug("embedding parse failed for %s: %s", title, exc)
    except Exception as exc:
        LOGGER.warning("Failed to load embeddings: %s", exc)
        return [], []
        
    return titles, vecs

def is_duplicate_title(title: str, titles, vecs, threshold: float | None = None):
    """
    מחזיר (is_duplicate: bool, v: np.ndarray | None)
    """
    v = embed_text(title)
    if v is None:
        return False, None
    valid_vecs = [w for w in vecs if isinstance(w, np.ndarray) and getattr(w, "size", 0) > 0]
    if not valid_vecs:
        return False, v
    if threshold is None:
        threshold = SIM_THRESHOLD
    
    sims = [cosine(v, w) for w in valid_vecs]
    best = max(sims) if sims else -1.0
    return (best >= threshold), v

def minimal_title_fix(old_title: str) -> str:
    """
    מקבל כותרת קיימת ומבקש מהמודל להחזיר כותרת דומה אך ייחודית.
    """
    cloud = client_cloud()
    r = chat_create_safe(
        cloud,
        model=CHECKER_MODEL or _settings.GEN_MODEL,  # Fallback if CHECKER_MODEL not set
        messages=[
            {
                "role": "system",
                "content": "שנה רק את שדה title כדי למנוע דמיון לשמות קיימים; החזר JSON תקין בלבד בפורמט {'title':'...'} ללא טקסט נוסף.",
            },
            {
                "role": "user",
                "content": json.dumps({"title": old_title}, ensure_ascii=False),
            },
        ],
        response_format={"type": "json_object"},
    )
    text = (r.choices[0].message.content or "").strip()
    data = strip_markdown_and_parse_json(text)
    if data and isinstance(data, dict):
        new_title = (data.get("title") or "").strip()
        if new_title:
            return new_title
    LOGGER.debug("minimal_title_fix failed to parse JSON response, using old_title")
    return old_title

def dedup_and_embed_titles(bundle: dict):
    mem_titles, mem_vecs = load_all_embeddings()
    for sc in bundle.get("scenarios", []):
        title = (sc.get("title") or "").strip()
        if not title:
            title = f"תרחיש ללא כותרת {datetime.now().strftime('%H%M%S')}"
            sc["title"] = title
        is_dup, v = is_duplicate_title(title, mem_titles, mem_vecs)
        if is_dup:
            new_title = minimal_title_fix(title)
            sc["title"] = new_title
            v = embed_text(new_title)
        if v is None or getattr(v, "size", 0) == 0:
            v = embed_text(sc["title"])  # ניסיון נוסף
        mem_titles.append(sc["title"])
        if v is not None and getattr(v, "size", 0) > 0:
            mem_vecs.append(v)
            save_embedding(sc["title"], v)
        else:
            mem_vecs.append(None)
    return bundle

def check_and_repair(bundle: dict) -> dict:
    """
    ולידציה/תיקון בענן, מחזיר תמיד dict; אם נכשל – מחזיר את bundle המקורי.
    """
    prompt = build_validator_prompt(bundle)
    cloud = client_cloud()
    try:
        resp = chat_create_safe(
            cloud,
            model=VALIDATOR_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON; no prose."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as e:
        LOGGER.warning("validator call failed (%s); using original bundle", e)
        return bundle
    text = (resp.choices[0].message.content or "").strip()
    # Use robust JSON parser to handle markdown code blocks
    fixed = strip_markdown_and_parse_json(text)
    if fixed and isinstance(fixed, dict):
        return fixed
    LOGGER.warning("Validator returned non-JSON; using original bundle")
    return bundle

def insert_bundle_to_db(bundle: dict, owner: str = "web", approved_by: str = "") -> dict:
    """Insert all scenarios from a bundle into the database (Refactored)."""
    pending = not bool(approved_by)
    inserted = 0

    for sc in bundle.get("scenarios", []):
        sc.setdefault("bundle_id", bundle.get("bundle_id", ""))
        try:
            insert_scenario(sc, owner=owner, pending=pending)
            inserted += 1
        except ValueError as e:
            LOGGER.warning("Failed to insert scenario '%s': %s", sc.get("title", ""), e)

    LOGGER.info('נשמרו %d תטל"מים לבסיס הנתונים: %s', inserted, DB_PATH)
    return bundle
