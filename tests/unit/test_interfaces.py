"""
Unit tests for tatlam/core/interfaces.py

Tests abstract interfaces and protocols for repository pattern.
Target: RepositoryInterface, AbstractRepository
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

import pytest

from tatlam.core.interfaces import AbstractRepository, RepositoryInterface


@pytest.mark.unit
class TestRepositoryInterface:
    """Test suite for RepositoryInterface Protocol."""

    def test_valid_implementation(self) -> None:
        """Test that a class with all required methods is valid."""

        class ValidRepository:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = ValidRepository()
        assert isinstance(repo, RepositoryInterface)

    def test_missing_fetch_all_fails(self) -> None:
        """Test that missing fetch_all fails the protocol check."""

        class InvalidRepository:
            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = InvalidRepository()
        assert not isinstance(repo, RepositoryInterface)

    def test_missing_fetch_one_fails(self) -> None:
        """Test that missing fetch_one fails the protocol check."""

        class InvalidRepository:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = InvalidRepository()
        assert not isinstance(repo, RepositoryInterface)

    def test_missing_fetch_count_fails(self) -> None:
        """Test that missing fetch_count fails the protocol check."""

        class InvalidRepository:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = InvalidRepository()
        assert not isinstance(repo, RepositoryInterface)

    def test_missing_insert_scenario_fails(self) -> None:
        """Test that missing insert_scenario fails the protocol check."""

        class InvalidRepository:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = InvalidRepository()
        assert not isinstance(repo, RepositoryInterface)

    def test_missing_fetch_by_category_slug_fails(self) -> None:
        """Test that missing fetch_by_category_slug fails the protocol check."""

        class InvalidRepository:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

        repo = InvalidRepository()
        assert not isinstance(repo, RepositoryInterface)

    def test_empty_class_fails(self) -> None:
        """Test that an empty class fails the protocol check."""

        class EmptyRepository:
            pass

        repo = EmptyRepository()
        assert not isinstance(repo, RepositoryInterface)


@pytest.mark.unit
class TestAbstractRepository:
    """Test suite for AbstractRepository abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that AbstractRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractRepository()  # type: ignore[abstract]

    def test_subclass_must_implement_all_methods(self) -> None:
        """Test that subclass must implement all abstract methods."""

        class IncompleteRepository(AbstractRepository):
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            # Missing other methods

        with pytest.raises(TypeError):
            IncompleteRepository()  # type: ignore[abstract]

    def test_valid_subclass_can_be_instantiated(self) -> None:
        """Test that a complete subclass can be instantiated."""

        class CompleteRepository(AbstractRepository):
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return [{"id": 1, "title": "Test"}]

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {"id": sid, "title": "Test"}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 42

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return [{"slug": slug}]

        repo = CompleteRepository()
        assert isinstance(repo, AbstractRepository)
        assert repo.fetch_all() == [{"id": 1, "title": "Test"}]
        assert repo.fetch_one(5) == {"id": 5, "title": "Test"}
        assert repo.fetch_count() == 42
        assert repo.insert_scenario({}) == 1
        assert repo.fetch_by_category_slug("test") == [{"slug": "test"}]

    def test_abstract_methods_are_defined(self) -> None:
        """Test that all expected abstract methods are defined."""
        abstract_methods = {"fetch_all", "fetch_one", "fetch_count",
                          "insert_scenario", "fetch_by_category_slug"}

        # Get abstract methods from the class
        actual_abstract = set()
        for name in dir(AbstractRepository):
            method = getattr(AbstractRepository, name)
            if getattr(method, "__isabstractmethod__", False):
                actual_abstract.add(name)

        assert abstract_methods == actual_abstract


@pytest.mark.unit
class TestRepositoryInterfaceFunctionality:
    """Test functional aspects of RepositoryInterface implementations."""

    def create_mock_repository(self) -> RepositoryInterface:
        """Create a mock repository for testing."""

        class MockRepository:
            def __init__(self) -> None:
                self.scenarios: list[dict[str, Any]] = [
                    {"id": 1, "title": "Scenario 1", "category": "security"},
                    {"id": 2, "title": "Scenario 2", "category": "safety"},
                    {"id": 3, "title": "Scenario 3", "category": "security"},
                ]

            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                result = self.scenarios
                if offset:
                    result = result[offset:]
                if limit:
                    result = result[:limit]
                return result

            def fetch_one(self, sid: int) -> dict[str, Any]:
                for s in self.scenarios:
                    if s["id"] == sid:
                        return s
                raise LookupError(f"Scenario {sid} not found")

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return len(self.scenarios)

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                new_id = max(s["id"] for s in self.scenarios) + 1
                self.scenarios.append({"id": new_id, **data})
                return new_id

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                result = [s for s in self.scenarios if s["category"] == slug]
                if offset:
                    result = result[offset:]
                if limit:
                    result = result[:limit]
                return result

        return MockRepository()

    def test_fetch_all_returns_list(self) -> None:
        """Test fetch_all returns a list of scenarios."""
        repo = self.create_mock_repository()
        result = repo.fetch_all()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_fetch_all_with_limit(self) -> None:
        """Test fetch_all respects limit parameter."""
        repo = self.create_mock_repository()
        result = repo.fetch_all(limit=2)
        assert len(result) == 2

    def test_fetch_all_with_offset(self) -> None:
        """Test fetch_all respects offset parameter."""
        repo = self.create_mock_repository()
        result = repo.fetch_all(offset=1)
        assert len(result) == 2
        assert result[0]["id"] == 2

    def test_fetch_one_returns_scenario(self) -> None:
        """Test fetch_one returns a single scenario."""
        repo = self.create_mock_repository()
        result = repo.fetch_one(1)
        assert result["id"] == 1
        assert result["title"] == "Scenario 1"

    def test_fetch_one_raises_on_missing(self) -> None:
        """Test fetch_one raises LookupError for missing scenario."""
        repo = self.create_mock_repository()
        with pytest.raises(LookupError):
            repo.fetch_one(999)

    def test_fetch_count_returns_integer(self) -> None:
        """Test fetch_count returns an integer."""
        repo = self.create_mock_repository()
        result = repo.fetch_count()
        assert isinstance(result, int)
        assert result == 3

    def test_insert_scenario_returns_id(self) -> None:
        """Test insert_scenario returns the new ID."""
        repo = self.create_mock_repository()
        new_id = repo.insert_scenario({"title": "New", "category": "test"})
        assert new_id == 4
        assert repo.fetch_count() == 4

    def test_fetch_by_category_slug(self) -> None:
        """Test fetch_by_category_slug filters correctly."""
        repo = self.create_mock_repository()
        result = repo.fetch_by_category_slug("security")
        assert len(result) == 2
        assert all(s["category"] == "security" for s in result)


@pytest.mark.unit
class TestDependencyInjection:
    """Test that interfaces support dependency injection patterns."""

    def test_function_accepts_protocol(self) -> None:
        """Test that functions can accept RepositoryInterface as parameter."""

        def process_scenarios(repo: RepositoryInterface) -> int:
            """Example function that uses repository interface."""
            scenarios = repo.fetch_all(limit=10)
            return len(scenarios)

        class MockRepo:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return [{"id": 1}, {"id": 2}]

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 0

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        repo = MockRepo()
        result = process_scenarios(repo)
        assert result == 2

    def test_class_accepts_protocol_in_init(self) -> None:
        """Test that classes can accept RepositoryInterface in __init__."""

        class ScenarioService:
            def __init__(self, repository: RepositoryInterface) -> None:
                self.repo = repository

            def get_scenario_count(self) -> int:
                return self.repo.fetch_count()

        class MockRepo:
            def fetch_all(
                self, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

            def fetch_one(self, sid: int) -> dict[str, Any]:
                return {}

            def fetch_count(
                self, where_sql: str = "", params: tuple[Any, ...] = ()
            ) -> int:
                return 42

            def insert_scenario(
                self, data: dict[str, Any], owner: str = "web", pending: bool = True
            ) -> int:
                return 1

            def fetch_by_category_slug(
                self, slug: str, limit: int | None = None, offset: int | None = None
            ) -> list[dict[str, Any]]:
                return []

        service = ScenarioService(MockRepo())
        assert service.get_scenario_count() == 42
