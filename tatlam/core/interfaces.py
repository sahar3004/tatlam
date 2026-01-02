"""
Abstract interfaces for tatlam/core.

This module defines abstract base classes (protocols) that establish contracts
for data persistence operations. By depending on interfaces rather than concrete
implementations, the core business logic adheres to the Dependency Inversion
Principle, making it easier to test and extend.

Usage:
    from tatlam.core.interfaces import RepositoryInterface

    class MyRepository(RepositoryInterface):
        def fetch_all(self, limit=None, offset=None):
            ...

Design Principles:
    - Core business logic depends on abstractions (interfaces), not concretions
    - Infrastructure implementations (repo.py, db.py) implement these interfaces
    - Dependency injection allows swapping implementations for testing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RepositoryInterface(Protocol):
    """Protocol defining the contract for scenario data access.

    Any class implementing this interface can be used as a repository
    in the core business logic, enabling dependency injection and
    simplified testing.
    """

    def fetch_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all scenarios from the data store.

        Parameters
        ----------
        limit : int | None, optional
            Maximum number of scenarios to return.
        offset : int | None, optional
            Number of scenarios to skip (for pagination).

        Returns
        -------
        list[dict[str, Any]]
            List of scenario dictionaries with normalized JSON fields.
        """
        ...

    def fetch_one(self, sid: int) -> dict[str, Any]:
        """Fetch a single scenario by ID.

        Parameters
        ----------
        sid : int
            The scenario ID.

        Returns
        -------
        dict[str, Any]
            The scenario dictionary.

        Raises
        ------
        LookupError
            If the scenario is not found.
        """
        ...

    def fetch_count(self, where_sql: str = "", params: tuple[Any, ...] = ()) -> int:
        """Count scenarios matching optional filter criteria.

        Parameters
        ----------
        where_sql : str, optional
            SQL WHERE clause (without the WHERE keyword for simple cases).
        params : tuple[Any, ...], optional
            Parameters for the WHERE clause.

        Returns
        -------
        int
            Number of matching scenarios.
        """
        ...

    def insert_scenario(
        self, data: dict[str, Any], owner: str = "web", pending: bool = True
    ) -> int:
        """Insert a new scenario into the data store.

        Parameters
        ----------
        data : dict[str, Any]
            Scenario fields. Must include at least "title" and "category".
        owner : str, default "web"
            Logical owner/creator identifier.
        pending : bool, default True
            Whether to mark the scenario as pending approval.

        Returns
        -------
        int
            The ID of the inserted scenario.

        Raises
        ------
        ValueError
            If required fields are missing or validation fails.
        """
        ...

    def fetch_by_category_slug(
        self, slug: str, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch scenarios by category slug.

        Parameters
        ----------
        slug : str
            The category slug (e.g., "piguim-peshutim").
        limit : int | None, optional
            Maximum number of scenarios to return.
        offset : int | None, optional
            Number of scenarios to skip (for pagination).

        Returns
        -------
        list[dict[str, Any]]
            List of matching scenario dictionaries.

        Raises
        ------
        LookupError
            If the slug is unknown.
        """
        ...


class AbstractRepository(ABC):
    """Abstract base class for repository implementations.

    Provides a more strict contract than the Protocol above, useful when
    you want to ensure method implementation at class definition time.
    """

    @abstractmethod
    def fetch_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all scenarios from the data store."""
        pass

    @abstractmethod
    def fetch_one(self, sid: int) -> dict[str, Any]:
        """Fetch a single scenario by ID."""
        pass

    @abstractmethod
    def fetch_count(self, where_sql: str = "", params: tuple[Any, ...] = ()) -> int:
        """Count scenarios matching optional filter criteria."""
        pass

    @abstractmethod
    def insert_scenario(
        self, data: dict[str, Any], owner: str = "web", pending: bool = True
    ) -> int:
        """Insert a new scenario into the data store."""
        pass

    @abstractmethod
    def fetch_by_category_slug(
        self, slug: str, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch scenarios by category slug."""
        pass


__all__ = ["RepositoryInterface", "AbstractRepository"]
