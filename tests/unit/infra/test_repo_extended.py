
import pytest
from unittest.mock import MagicMock, patch
from tatlam.infra.repo import get_repository, fetch_count, fetch_by_category_slug


import pytest
import json
import numpy as np
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError
from tatlam.infra.repo import (
    get_repository, fetch_count, fetch_by_category_slug,
    db_has_column, save_embedding, _normalize_text, _parse_json_field,
    normalize_row, is_approved_row, fetch_all, insert_scenario,
    reject_scenario, fetch_all_basic_categories,
    add_to_hall_of_fame, add_to_graveyard, get_hall_of_fame_examples,
    get_common_rejection_reasons, get_graveyard_patterns,
    log_feedback_entry, get_learning_context, yield_all_titles_with_embeddings
)
from tatlam.infra.models import Scenario

@pytest.mark.unit
class TestRepoExtended:
    """Extended unit tests for 100% repository coverage."""

    # --- Utility Functions ---

    def test_db_has_column(self, in_memory_db, monkeypatch):
        """Test column existence check (cached)."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.TABLE_NAME = "scenarios"
        monkeypatch.setattr("tatlam.infra.repo.get_settings", lambda: mock_settings)

        # Test valid column
        assert db_has_column("scenarios", "title") is True
        # Test cached result
        assert db_has_column("scenarios", "title") is True
        
        # Test invalid column on Scenario model
        assert db_has_column("scenarios", "non_existent_col") is False
        
        # Test unknown table fallback
        monkeypatch.setenv("TABLE_NAME", "scenarios")
        assert db_has_column("other_table", "whatever") is True

    def test_normalize_text(self):
        """Test text normalization."""
        assert _normalize_text(None) == ""
        assert _normalize_text("Simple") == "Simple"
        # Hebrew check (visual vs logical) - simplistic check here
        assert isinstance(_normalize_text("שלום"), str)
        assert _normalize_text(123) == "123"

    def test_parse_json_field(self):
        """Test JSON parsing robustness."""
        assert _parse_json_field(None) == []
        assert _parse_json_field(["a"]) == ["a"]
        assert _parse_json_field({"k": "v"}) == {"k": "v"}
        assert _parse_json_field("") == []
        assert _parse_json_field("   ") == []
        assert _parse_json_field('[1, 2]') == [1, 2]
        assert _parse_json_field('{"a": 1}') == {"a": 1}
        # Bad JSON
        assert _parse_json_field('{invalid') == []
        assert _parse_json_field('123') == [] # Not list/dict
    
    def test_normalize_row(self):
        """Test row normalization for different input types."""
        # Dict
        row_dict = {"title": "Test", "steps": '["step1"]', "unknown": "val"}
        norm = normalize_row(row_dict)
        assert norm["title"] == "Test"
        assert norm["steps"] == ["step1"]
        
        # Object with keys() (like sqlite3.Row)
        class MockRow:
            def keys(self): return ["title", "steps"]
            def __getitem__(self, key): return row_dict[key]
            
        norm2 = normalize_row(MockRow())
        assert norm2["title"] == "Test"
        assert norm2["steps"] == ["step1"]
        
        # Scenario Object
        s = Scenario(title="Test", steps='["step1"]')
        norm3 = normalize_row(s)
        assert norm3["title"] == "Test"
        assert norm3["steps"] == ["step1"]
        
        # Fallback dict(row)
        # Using a list of tuples which dict() accepts
        row_tuples = [("title", "Test"), ("steps", '["step1"]')]
        norm4 = normalize_row(row_tuples)
        assert norm4["title"] == "Test"
        assert norm4["steps"] == ["step1"]

    def test_is_approved_row(self, monkeypatch):
        """Test approval filter logic."""
        mock_settings = MagicMock()
        mock_settings.TABLE_NAME = "scenarios"
        monkeypatch.setattr("tatlam.infra.repo.get_settings", lambda: mock_settings)
        
        # With REQUIRE_APPROVED_ONLY = False
        mock_settings.REQUIRE_APPROVED_ONLY = False
        assert is_approved_row({"status": "pending"}) is True
        
        # With REQUIRE_APPROVED_ONLY = True, checking status column
        mock_settings.REQUIRE_APPROVED_ONLY = True
        
        # Ensure db_has_column returns True for status
        monkeypatch.setattr("tatlam.infra.repo.db_has_column", lambda t, c: True)
        assert is_approved_row({"status": "approved"}) is True
        assert is_approved_row({"status": "pending"}) is False
        assert is_approved_row({"status": None}) is False
        
        # With REQUIRE_APPROVED_ONLY = True, checking approved_by (legacy) - simulating no status column
        monkeypatch.setattr("tatlam.infra.repo._has_status_column", lambda: False)
        assert is_approved_row({"approved_by": "admin"}) is True
        assert is_approved_row({"approved_by": "human"}) is True
        assert is_approved_row({"approved_by": ""}) is False

    # --- Core CRUD ---

    def test_save_embedding(self, in_memory_db):
        """Test embedding save (insert and update)."""
        vec = np.array([0.1, 0.2])
        # Insert
        save_embedding("test_emb", vec)
        # Check
        repo = get_repository()
        # No public fetch for embedding, verify via DB or re-save
        
        # Update
        vec2 = np.array([0.3, 0.4])
        save_embedding("test_emb", vec2)
        
        # Exception handling (mock commit failure)
        # Patch get_session in the repo module namespace
        with patch("tatlam.infra.repo.get_session") as mock_sess:
           mock_sess.return_value.__enter__.return_value.commit.side_effect = Exception("DB Error")
           save_embedding("fail", vec) # Should log warning, not raise

    def test_fetch_all_extended(self, in_memory_db, sample_scenario_data):
        """Test fetch_all with limits, offsets, filtering."""
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data) # pending
        repo.insert_scenario({**sample_scenario_data, "title": "Rejected"}, pending=True)
        repo.reject_scenario(2, "bad")
        
        # Fetch active
        res = fetch_all(status_filter="active")
        assert len(res) == 1
        assert res[0]["title"] == sample_scenario_data["title"]
        
        # Fetch rejected
        res_rej = fetch_all(status_filter="rejected")
        assert len(res_rej) == 1
        assert res_rej[0]["title"] == "Rejected"
        
        # Fetch all
        # Note: fetch_all logic for "all" is slightly implicit in `if status_filter == "active"` block
        # If passed "all", it skips the active filter, but runs explicit check `elif status_filter != "all"`.
        # So "all" means no WHERE clause on status.
        res_all = fetch_all(status_filter="all")
        assert len(res_all) == 2
        
        # Pagination
        repo.insert_scenario({**sample_scenario_data, "title": "Page2"})
        repo.insert_scenario({**sample_scenario_data, "title": "Page3"})
        # Total active: 1 (original) + 2 new = 3
        # Rejected: 1
        # Total: 4
        
        # Limit/Offset on active
        p1 = fetch_all(limit=1, offset=0, status_filter="active")
        assert len(p1) == 1
        # default sort is created_at desc.

    def test_fetch_all_legacy_approval(self, in_memory_db, sample_scenario_data, monkeypatch):
        """Test fetch_all with legacy approved_by check (no status col)."""
        mock_settings = MagicMock()
        mock_settings.TABLE_NAME = "scenarios"
        mock_settings.REQUIRE_APPROVED_ONLY = True
        monkeypatch.setattr("tatlam.infra.repo.get_settings", lambda: mock_settings)
        
        # Simulate NO status column
        monkeypatch.setattr("tatlam.infra.repo.db_has_column", lambda t, c: False)
        
        # Insert one mixed
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data) # pending (status=pending, approved_by="")
        
        # Should be excluded
        scenarios = fetch_all()
        assert len(scenarios) == 0
        
        # Now artificially approve it via SQL (since insert sets status pending)
        # We need to set approved_by="human"
        cursor = in_memory_db.cursor()
        cursor.execute("UPDATE scenarios SET approved_by='human' WHERE id=1")
        in_memory_db.commit()
        
        # Now it should show up
        scenarios2 = fetch_all()
        assert len(scenarios2) == 1

    def test_fetch_all_approved_only_with_status_col(self, in_memory_db, sample_scenario_data, monkeypatch):
        """Test fetch_all with approved_only=True and existing status column."""
        mock_settings = MagicMock()
        mock_settings.TABLE_NAME = "scenarios"
        mock_settings.REQUIRE_APPROVED_ONLY = True
        monkeypatch.setattr("tatlam.infra.repo.get_settings", lambda: mock_settings)
        
        # Ensure has_status_column -> True
        monkeypatch.setattr("tatlam.infra.repo.db_has_column", lambda t, c: True)
        
        repo = get_repository()
        # Insert pending
        repo.insert_scenario(sample_scenario_data, pending=True)
        # Insert approved
        repo.insert_scenario({**sample_scenario_data, "title": "Appr"}, pending=False)
        
        # Should only get one
        scenarios = fetch_all()
        assert len(scenarios) == 1
        assert scenarios[0]["title"] == "Appr"
        
    def test_fetch_count_extended(self, in_memory_db, sample_scenario_data, monkeypatch):
        """Test fetch count with and without approval required."""
        
        mock_settings = MagicMock()
        mock_settings.TABLE_NAME = "scenarios"
        monkeypatch.setattr("tatlam.infra.repo.get_settings", lambda: mock_settings)
        
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data)

        # 1. NOT Required Approved Only
        mock_settings.REQUIRE_APPROVED_ONLY = False
        assert fetch_count() == 1
            
        # 2. Required Approved Only
        mock_settings.REQUIRE_APPROVED_ONLY = True
        
        # 2a. With Status Column (default for test DB fixture)
        # Ensure has_status_column -> db_has_column -> True
        monkeypatch.setattr("tatlam.infra.repo.db_has_column", lambda t, c: True)
        
        # Only inserted one pending, so count of approved should be 0
        assert fetch_count() == 0
        
        # Insert an approved one
        repo.insert_scenario({**sample_scenario_data, "title": "Appr"}, pending=False)
        assert fetch_count() == 1

    def test_fetch_all_basic_categories(self, in_memory_db, sample_scenario_data):
        """Test basic info fetch."""
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data)
        
        cats = fetch_all_basic_categories()
        assert len(cats) == 1
        assert "steps" not in cats[0] # Should be minimal
        assert "title" in cats[0]

    def test_insert_scenario_validations(self, in_memory_db):
        """Test validations in insert."""
        repo = get_repository()
        with pytest.raises(ValueError, match="title is required"):
            repo.insert_scenario({"category": "c"})
        with pytest.raises(ValueError, match="category is required"):
            repo.insert_scenario({"title": "t"})
            
        # Duplicate title
        repo.insert_scenario({"title": "Dup", "category": "c"})
        with pytest.raises(ValueError, match="scenario already exists"):
            repo.insert_scenario({"title": "Dup", "category": "c"})

    def test_reject_scenario_not_found(self, in_memory_db):
        """Test rejecting non-existent scenario."""
        repo = get_repository()
        assert repo.reject_scenario(999, "reason") is False

    def test_fetch_by_category_slug_pagination(self, in_memory_db, sample_scenario_data):
        """Test pagination in slug fetch."""
        repo = get_repository()
        repo.insert_scenario({**sample_scenario_data, "title": "A"})
        repo.insert_scenario({**sample_scenario_data, "title": "B"})
        
        from tatlam.core.categories import category_to_slug
        slug = category_to_slug(sample_scenario_data["category"])
        
        res = fetch_by_category_slug(slug, limit=1, offset=0)
        assert len(res) == 1
        
        # No pagination
        res_all = fetch_by_category_slug(slug)
        assert len(res_all) >= 2

    # --- RLHF Learning ---

    def test_rlhf_workflow(self, in_memory_db, sample_scenario_data):
        """Test the full RLHF storage workflow."""
        repo = get_repository()
        sid = repo.insert_scenario(sample_scenario_data)
        
        # Hall of Fame
        hof_id = add_to_hall_of_fame(sid, sample_scenario_data, 95.0)
        assert hof_id > 0
        
        # Retrieve Examples
        examples = get_hall_of_fame_examples(category=sample_scenario_data["category"], limit=5)
        assert len(examples) == 1
        assert examples[0]["title"] == sample_scenario_data["title"]
        
        # empty result for bad category
        assert len(get_hall_of_fame_examples(category="bad_cat")) == 0
        
        # Graveyard
        bad_data = {**sample_scenario_data, "title": "Bad"}
        sid_bad = repo.insert_scenario(bad_data)
        gy_id = add_to_graveyard(sid_bad, bad_data, "Too boring", "More action needed")
        assert gy_id > 0
        
        # Invalid graveyard add
        with pytest.raises(ValueError):
            add_to_graveyard(sid_bad, bad_data, "") # missing reason
            
        # Common Rejection Reasons
        reasons = get_common_rejection_reasons(limit=5)
        assert len(reasons) == 1
        assert reasons[0] == ("Too boring", 1)
        
        # Patterns
        patterns = get_graveyard_patterns(category=sample_scenario_data["category"])
        assert "Too boring" in patterns
        
        # Learning Context
        ctx = get_learning_context(category=sample_scenario_data["category"])
        assert len(ctx["positive_examples"]) == 1
        assert len(ctx["negative_patterns"]) == 1

    def test_feedback_logging(self, in_memory_db):
        """Test feedback logging."""
        eid = log_feedback_entry(
            "uuid-123", {"inp": 1}, {"out": 2}, "approved", judge_score=0.9
        )
        assert eid == "uuid-123"
        # Can verify via simple SQL scan if needed, or trust return implies generic success

    def test_yield_titles_with_embeddings(self, in_memory_db):
        """Test the generator."""
        # Insert raw embedding
        save_embedding("T1", np.array([1, 2]))
        save_embedding("T2", np.array([3, 4]))
        
        gen = yield_all_titles_with_embeddings(batch_size=1)
        results = list(gen)
        assert len(results) == 2
        titles = sorted([r[0] for r in results])
        assert titles == ["T1", "T2"]
        
    def test_fetch_count_by_slug(self, in_memory_db, sample_scenario_data):
        """Test count by slug logic."""
        from tatlam.infra.repo import fetch_count_by_slug
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data)
        
        from tatlam.core.categories import category_to_slug
        slug = category_to_slug(sample_scenario_data["category"])
        
        assert fetch_count_by_slug(slug) == 1
        assert fetch_count_by_slug("invalid-slug") == 0

    def test_repo_class_passthrough(self, in_memory_db, sample_scenario_data):
        """Verify remaining class methods delegate correctly."""
        repo = get_repository()
        
        # fetch_all passthrough
        repo.insert_scenario(sample_scenario_data)
        assert len(repo.fetch_all(limit=1)) == 1
        
        # reject passthrough
        sid = repo.fetch_all()[0]["id"]
        assert repo.reject_scenario(sid, "bad") is True
        
        # fetch_by_category_slug passthrough
        slug = "invalid-slug" 
        assert len(repo.fetch_by_category_slug(slug)) == 0

        # fetch_count passthrough
        assert repo.fetch_count() >= 0

        # Check add_to_hall_of_fame
        assert repo.add_to_hall_of_fame(sid, sample_scenario_data, 90) > 0
        
        # Check add_to_graveyard
        assert repo.add_to_graveyard(sid, sample_scenario_data, "bad") > 0
        
        # Check get_learning_context
        assert isinstance(repo.get_learning_context(), dict)
        
        # Check yield passthrough
        save_embedding("T1", np.array([1]))
        assert len(list(repo.yield_titles_with_embeddings())) == 1

    def test_fetch_all_dto(self, in_memory_db, sample_scenario_data):
        """Test fetch_all_dto transformation."""
        repo = get_repository()
        repo.insert_scenario(sample_scenario_data)
        
        # Test function
        from tatlam.infra.repo import fetch_all_dto
        dtos = fetch_all_dto()
        assert len(dtos) == 1
        assert dtos[0].title == sample_scenario_data["title"]
        
        # Test class wrapper
        dtos2 = repo.fetch_all_dto()
        assert len(dtos2) == 1
        assert dtos2[0].title == sample_scenario_data["title"]

    def test_singleton_get_repository(self):
        """Verify singleton behavior."""
        r1 = get_repository()
        r2 = get_repository()
        assert r1 is r2

    def test_yield_titles_with_embeddings_skip_nulls(self, monkeypatch):
        """Test generator skips empty titles/vectors."""
        # Mock session execute to return row list directly
        rows = [("Good", "[1]"), (None, "[2]"), ("BadVec", None), ("", "[3]")]
        
        mock_session = MagicMock()
        mock_session.execute.return_value = rows
        
        # Patch get_session to return our mock
        # We need to mock the context manager structure
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_session
        
        monkeypatch.setattr("tatlam.infra.repo.get_session", lambda: mock_ctx)
        
        from tatlam.infra.repo import yield_all_titles_with_embeddings
        results = list(yield_all_titles_with_embeddings())
        assert len(results) == 1
        assert results[0][0] == "Good"

    def test_repo_class_fetch_one_wrapper(self, in_memory_db, sample_scenario_data):
        """Separate test for fetch_one wrapper to ensure coverage."""
        repo = get_repository()
        sid = repo.insert_scenario(sample_scenario_data)
        
        s = repo.fetch_one(sid)
        assert s["id"] == sid
        assert s["title"] == sample_scenario_data["title"]

    def test_fetch_one_not_found(self, in_memory_db):
        """Test fetch_one raises LookupError for missing ID."""
        repo = get_repository()
        with pytest.raises(LookupError):
            repo.fetch_one(99999)
