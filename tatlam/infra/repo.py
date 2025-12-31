"""Repository layer for scenario data access.

This module provides SQLAlchemy ORM-based data access patterns.
All public functions return dictionaries for backward compatibility with existing code.

The migration to SQLAlchemy provides:
- Type-safe ORM models
- Automatic connection pooling
- WAL mode for better concurrency
- Cleaner transaction management
"""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from typing import Any, Generator

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from tatlam.infra.db import get_session
from tatlam.infra.models import Scenario
from tatlam.settings import get_settings

# Get settings for module-level constants
_settings = get_settings()
REQUIRE_APPROVED_ONLY = _settings.REQUIRE_APPROVED_ONLY
TABLE_NAME = _settings.TABLE_NAME

# Cache for column existence checks
_column_cache: dict[tuple[str, str], bool] = {}


def db_has_column(table: str, col: str) -> bool:
    """Check if a column exists in a table.

    Results are cached for performance since schema doesn't change at runtime.
    """
    cache_key = (table, col)
    if cache_key in _column_cache:
        return _column_cache[cache_key]

    # For the Scenario model, we know the columns from the ORM definition
    if table == TABLE_NAME:
        # Get column names from the ORM model
        result = hasattr(Scenario, col)
        _column_cache[cache_key] = result
        return result

    # Fallback for unknown tables - assume column exists
    return True


_HAS_STATUS = db_has_column(TABLE_NAME, "status")


def _normalize_text(text: Any) -> str:
    """Normalize text to Unicode NFC form for consistent Hebrew storage.

    NFC normalization ensures Hebrew characters with diacritics are stored
    in their canonical composed form, preventing byte-level mismatches
    between visually identical strings.
    """
    if text is None:
        return ""
    s = str(text)
    return unicodedata.normalize("NFC", s)


JSON_FIELDS: list[str] = [
    "steps",
    "required_response",
    "debrief_points",
    "comms",
    "decision_points",
    "escalation_conditions",
    "lessons_learned",
    "variations",
    "validation",
]


def _parse_json_field(val: Any) -> list[Any] | dict[str, Any]:
    """Parse a JSON string field to Python object."""
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str) and not val.strip():
        return []
    try:
        loaded = json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(loaded, (list, dict)):
        return loaded
    return []


def normalize_row(row: Any) -> dict[str, Any]:
    """Normalize a row (from SQLAlchemy) to a dictionary.

    Handles Scenario ORM instances and dict-like objects.
    JSON fields are automatically parsed.
    """
    # Handle SQLAlchemy Scenario model
    if isinstance(row, Scenario):
        return row.to_dict()

    # Handle sqlite3.Row or dict-like objects
    if hasattr(row, "keys"):
        r: dict[str, Any] = {k: row[k] for k in row.keys()}
    else:
        r = dict(row)

    # Normalize JSON-like text fields
    for key in JSON_FIELDS:
        r[key] = _parse_json_field(r.get(key))
    return r


def is_approved_row(row: dict[str, Any]) -> bool:
    """Check if a row is approved based on status/approved_by fields."""
    if not REQUIRE_APPROVED_ONLY:
        return True
    if _HAS_STATUS:
        return (row.get("status") or "").strip().lower() == "approved"
    ab = (row.get("approved_by") or "").strip().lower()
    return ab in {"admin", "human", "approved", "manager"}


def fetch_all_basic_categories() -> list[dict[str, Any]]:
    """Fetch basic category info for all scenarios.

    Returns only essential fields for category listing/filtering.
    """
    with get_session() as session:
        stmt = select(
            Scenario.id,
            Scenario.title,
            Scenario.category,
            Scenario.status,
            Scenario.approved_by,
            Scenario.created_at,
        ).order_by(Scenario.created_at.desc(), Scenario.id.desc())

        results = session.execute(stmt).fetchall()
        rows = [
            {
                "id": r.id,
                "title": r.title,
                "category": r.category,
                "status": r.status,
                "approved_by": r.approved_by,
                "created_at": r.created_at,
            }
            for r in results
        ]

    return [r for r in rows if is_approved_row(r)]


def fetch_all(limit: int | None = None, offset: int | None = None) -> list[dict[str, Any]]:
    """Fetch all scenarios with optional pagination.

    Parameters
    ----------
    limit : int | None
        Maximum number of results to return.
    offset : int | None
        Number of results to skip.

    Returns
    -------
    list[dict[str, Any]]
        List of scenario dictionaries.
    """
    with get_session() as session:
        stmt = select(Scenario).order_by(Scenario.created_at.desc(), Scenario.id.desc())

        if limit is not None and offset is not None:
            stmt = stmt.limit(limit).offset(offset)

        scenarios = session.scalars(stmt).all()
        rows = [s.to_dict() for s in scenarios]

    return [r for r in rows if is_approved_row(r)]


def fetch_count(where_sql: str = "", params: tuple[Any, ...] = ()) -> int:
    """Count scenarios matching optional filter criteria.

    Note: The `where_sql` and `params` arguments are legacy artifacts and are ignored
    in this implementation.

    Parameters
    ----------
    where_sql : str
        Ignored.
    params : tuple[Any, ...]
        Ignored.

    Returns
    -------
    int
        Count of matching scenarios.
    """
    with get_session() as session:
        stmt = select(func.count()).select_from(Scenario)

        if REQUIRE_APPROVED_ONLY and _HAS_STATUS:
            stmt = stmt.where(Scenario.status == "approved")

        result = session.execute(stmt).scalar()
        return int(result or 0)


def fetch_one(sid: int) -> dict[str, Any]:
    """Fetch a single scenario by ID.

    Parameters
    ----------
    sid : int
        The scenario ID to fetch.

    Returns
    -------
    dict[str, Any]
        The scenario dictionary.

    Raises
    ------
    LookupError
        If the scenario is not found.
    """
    with get_session() as session:
        scenario = session.get(Scenario, sid)
        if not scenario:
            raise LookupError("not_found")
        return scenario.to_dict()


def fetch_by_category_slug(
    slug: str, limit: int | None = None, offset: int | None = None
) -> list[dict[str, Any]]:
    """Return approved rows for a given category slug with optional paging.

    Note: Business logic validation (slug validation) should be done at the
    service/controller layer. This repository layer only performs data access.

    Parameters
    ----------
    slug : str
        The category slug to filter by (no validation performed).
    limit : int | None
        Maximum number of results.
    offset : int | None
        Number of results to skip.

    Returns
    -------
    list[dict[str, Any]]
        List of scenario dictionaries matching the slug.
    """
    # Import category_to_slug lazily to avoid circular dependency
    from tatlam.core.categories import category_to_slug

    all_rows = fetch_all()
    filtered = [r for r in all_rows if category_to_slug(r.get("category", "")) == slug]
    if limit is not None and offset is not None:
        return filtered[offset : offset + limit]
    return filtered


def fetch_count_by_slug(slug: str) -> int:
    """Count approved rows for a given category slug.

    Note: No validation performed - business logic should validate slug
    at the service/controller layer.
    """
    # Import category_to_slug lazily to avoid circular dependency
    from tatlam.core.categories import category_to_slug

    rows = fetch_all_basic_categories()
    return sum(1 for r in rows if category_to_slug(r.get("category", "")) == slug)


def insert_scenario(data: dict[str, Any], owner: str = "web", pending: bool = True) -> int:
    """Insert a new scenario into the database.

    Note: Business logic validation (category validation) should be done at the
    service/controller layer. This repository layer only validates data constraints.

    Parameters
    ----------
    data : dict[str, Any]
        Scenario fields. Must include at least "title" and "category". Optional
        JSON-like fields (lists) will be serialized.
    owner : str, default "web"
        Logical owner/creator to store in the DB.
    pending : bool, default True
        If True, the row will be inserted with status="pending".

    Returns
    -------
    int
        The row id of the inserted scenario.

    Raises
    ------
    ValueError
        If required fields are missing or on uniqueness violation.
    """
    title = _normalize_text(data.get("title") or "").strip()
    category = _normalize_text(data.get("category") or "").strip()

    if not title:
        raise ValueError("title is required")
    if not category:
        raise ValueError("category is required")

    # Create the Scenario ORM instance
    scenario = Scenario(
        bundle_id=_normalize_text(data.get("bundle_id", "")),
        external_id=_normalize_text(data.get("external_id", "")),
        title=title,
        category=category,
        threat_level=_normalize_text(data.get("threat_level", "")),
        likelihood=_normalize_text(data.get("likelihood", "")),
        complexity=_normalize_text(data.get("complexity", "")),
        location=_normalize_text(data.get("location", "")),
        background=_normalize_text(data.get("background", "")),
        steps=json.dumps(data.get("steps", []), ensure_ascii=False),
        required_response=json.dumps(data.get("required_response", []), ensure_ascii=False),
        debrief_points=json.dumps(data.get("debrief_points", []), ensure_ascii=False),
        operational_background=_normalize_text(data.get("operational_background", "")),
        media_link=data.get("media_link", ""),  # URLs don't need NFC normalization
        mask_usage=_normalize_text(data.get("mask_usage", "")) or None,
        authority_notes=_normalize_text(data.get("authority_notes", "")),
        cctv_usage=_normalize_text(data.get("cctv_usage", "")),
        comms=json.dumps(data.get("comms", []), ensure_ascii=False),
        decision_points=json.dumps(data.get("decision_points", []), ensure_ascii=False),
        escalation_conditions=json.dumps(data.get("escalation_conditions", []), ensure_ascii=False),
        end_state_success=_normalize_text(data.get("end_state_success", "")),
        end_state_failure=_normalize_text(data.get("end_state_failure", "")),
        lessons_learned=json.dumps(data.get("lessons_learned", []), ensure_ascii=False),
        variations=json.dumps(data.get("variations", []), ensure_ascii=False),
        validation=json.dumps(data.get("validation", []), ensure_ascii=False),
        owner=owner,
        approved_by="",
        status="pending" if pending else "approved",
        created_at=datetime.now().isoformat(),
    )

    try:
        with get_session() as session:
            session.add(scenario)
            session.flush()  # Get the ID before commit
            new_id = scenario.id
    except IntegrityError as e:
        # UNIQUE(title) violation
        raise ValueError("scenario already exists") from e

    return new_id


def yield_all_titles_with_embeddings(
    batch_size: int = 1000,
) -> Generator[tuple[str, str], None, None]:
    """
    Generator that yields scenario titles with embeddings in batches.

    Phase 2 Optimization: Prevents loading all embeddings into RAM.
    Uses SQLAlchemy's yield_per() for memory-efficient iteration.

    Args:
        batch_size: Number of rows to fetch per batch

    Yields:
        Tuple of (title, vector_json_string)

    Usage:
        for title, vector_json in yield_all_titles_with_embeddings():
            vec = np.array(json.loads(vector_json))
            # Process vector...
    """
    from tatlam.infra.models import ScenarioEmbedding

    with get_session() as session:
        # Use yield_per for memory-efficient batching
        stmt = select(
            ScenarioEmbedding.title, ScenarioEmbedding.vector_json
        ).execution_options(yield_per=batch_size)

        for row in session.execute(stmt):
            title, vector_json = row
            if title and vector_json:
                yield (title, vector_json)


class ScenarioRepository:
    """Concrete repository implementation for scenario data access.

    This class wraps the module-level functions and implements the
    RepositoryInterface protocol, enabling dependency injection
    in business logic components.

    Usage:
        repo = ScenarioRepository()
        scenarios = repo.fetch_all(limit=10)

        # Or inject into components:
        brain = TrinityBrain(repository=repo)
    """

    def fetch_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all scenarios from the database."""
        return fetch_all(limit=limit, offset=offset)

    def yield_titles_with_embeddings(
        self, batch_size: int = 1000
    ) -> Generator[tuple[str, str], None, None]:
        """
        Yield scenario titles with embeddings in batches.

        Phase 2 Optimization: Memory-efficient iterator.
        """
        return yield_all_titles_with_embeddings(batch_size=batch_size)

    def fetch_one(self, sid: int) -> dict[str, Any]:
        """Fetch a single scenario by ID."""
        return fetch_one(sid)

    def fetch_count(
        self, where_sql: str = "", params: tuple[Any, ...] = ()
    ) -> int:
        """Count scenarios matching optional filter criteria."""
        return fetch_count(where_sql=where_sql, params=params)

    def insert_scenario(
        self, data: dict[str, Any], owner: str = "web", pending: bool = True
    ) -> int:
        """Insert a new scenario into the database."""
        return insert_scenario(data=data, owner=owner, pending=pending)

    def fetch_by_category_slug(
        self, slug: str, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch scenarios by category slug."""
        return fetch_by_category_slug(slug=slug, limit=limit, offset=offset)


# Default repository instance for convenience
_default_repository: ScenarioRepository | None = None


def get_repository() -> ScenarioRepository:
    """Get the default repository instance (singleton pattern).

    Returns
    -------
    ScenarioRepository
        The default repository instance.
    """
    global _default_repository
    if _default_repository is None:
        _default_repository = ScenarioRepository()
    return _default_repository


__all__ = [
    "normalize_row",
    "fetch_all_basic_categories",
    "fetch_all",
    "fetch_count",
    "fetch_one",
    "fetch_by_category_slug",
    "fetch_count_by_slug",
    "insert_scenario",
    "ScenarioRepository",
    "get_repository",
    "JSON_FIELDS",
    "is_approved_row",
    "db_has_column",
    "_normalize_text",
]
