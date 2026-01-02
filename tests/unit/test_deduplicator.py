from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from tatlam.graph.nodes.deduplicator import deduplicator_node, _cosine_similarity, _embed_text, _load_existing_embeddings, _is_duplicate
from tatlam.graph.state import SwarmState, ScenarioCandidate, ScenarioStatus

@pytest.fixture
def mock_cloud_client():
    with patch("tatlam.core.llm_factory.client_cloud") as mock:
        client = MagicMock()
        mock.return_value = client
        yield mock, client

@pytest.fixture
def mock_db():
    with patch("tatlam.infra.db.get_session") as mock_sess:
        session = MagicMock()
        mock_sess.return_value.__enter__.return_value = session
        yield session

class TestDeduplicatorNode:

    def test_cosine_similarity(self):
        v1 = np.array([1, 0])
        v2 = np.array([1, 0])
        assert _cosine_similarity(v1, v2) > 0.99
        
        v3 = np.array([0, 1])
        assert _cosine_similarity(v1, v3) == 0.0
        
        # Zero vector
        v0 = np.array([0, 0])
        assert _cosine_similarity(v1, v0) == 0.0
        assert _cosine_similarity(v0, v0) == 0.0

    def test_embed_text_success(self, mock_cloud_client):
        _, client = mock_cloud_client
        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.1, 0.2])]
        client.embeddings.create.return_value = resp
        
        vec = _embed_text("text")
        assert vec is not None
        assert vec.shape == (2,)
        # Use approx for float comparison
        assert vec[0] == pytest.approx(0.1)

    def test_embed_text_failure(self, mock_cloud_client):
        _, client = mock_cloud_client
        client.embeddings.create.side_effect = Exception("Embed Fail")
        
        vec = _embed_text("text")
        assert vec is None

    def test_embed_text_cloud_unavailable(self, mock_cloud_client):
        """Test client_cloud() raising exception."""
        mock_get, _ = mock_cloud_client
        mock_get.side_effect = Exception("Cloud Config Fail")
        
        vec = _embed_text("text")
        assert vec is None

    def test_load_existing_embeddings(self, mock_db):
        query_rows = [
            ("t1", "[1.0, 0.0]"),
            ("t2", "invalid json"), # Should skip
            (None, "[0.0, 1.0]"), # Skip
            ("t3", "[]"), # Empty vec -> skip
            ("t4", "[0.0, 1.0]")
        ]
        mock_db.execute.return_value = query_rows
        
        titles, vecs = _load_existing_embeddings()
        
        assert len(titles) == 2
        assert "t1" in titles
        assert "t4" in titles
        assert len(vecs) == 2
        
        # Exception handling
        mock_db.execute.side_effect = Exception("DB Error")
        t, v = _load_existing_embeddings()
        assert t == []
        assert v == []

    def test_is_duplicate_logic(self):
        # mock vectors
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0]) # Orthogonal
        v3 = np.array([0.9, 0.1]) # Similar to v1
        
        with patch("tatlam.graph.nodes.deduplicator._embed_text") as mock_embed:
            # 1. Embed failure
            mock_embed.return_value = None
            dup, vec = _is_duplicate("t", "bg", [], [], [], 0.9)
            assert not dup
            assert vec is None
            
            # 2. Unique
            mock_embed.return_value = v1
            dup, vec = _is_duplicate("t", "bg", ["existing"], [v2], [], 0.9)
            assert not dup
            assert vec is not None
            
            # 3. Duplicate in DB
            dup, vec = _is_duplicate("t", "bg", ["existing"], [v3], [], 0.8)
            assert dup
            
            # 4. Duplicate in Batch
            dup, vec = _is_duplicate("t", "bg", [], [], [("t2", v3)], 0.8)
            assert dup

    def test_dup_check_branches(self):
        # Specific branch testing for coverage
        v1 = np.array([1.0])
        v2 = np.array([0.0]) # Diff
        
        # Test batch check continue (sim < thresh)
        # We need _is_duplicate to reach batch loop.
        # So DB loop must not return True.
        
        with patch("tatlam.graph.nodes.deduplicator._embed_text", return_value=v1):
            # No existing vectors -> skips DB loop
            # Batch vector v2 (ortho to v1) -> sim=0 < 0.9 -> continue
            dup, _ = _is_duplicate("t", "bg", [], [], [("other", v2)], 0.9)
            assert not dup

    def test_deduplicator_node_flow(self):
        state = SwarmState()
        
        c1 = state.add_candidate({"title": "C1"})
        c1.status = ScenarioStatus.FORMATTED
        
        c2 = state.add_candidate({"title": "C2"})
        c2.status = ScenarioStatus.FORMATTED
        
        c3 = state.add_candidate({"title": "C3"})
        c3.status = ScenarioStatus.DRAFT # Ignored
        
        # Mock dependencies
        with patch("tatlam.graph.nodes.deduplicator._load_existing_embeddings") as mock_load, \
             patch("tatlam.graph.nodes.deduplicator._is_duplicate") as mock_dup:
             
             mock_load.return_value = ([], [])
             
             # C1 is unique, C2 is duplicate
             v1 = np.array([1.0])
             mock_dup.side_effect = [
                 (False, v1), # C1
                 (True, v1)   # C2
             ]
             
             final_state = deduplicator_node(state)
             
             assert final_state.candidates[0].status == ScenarioStatus.UNIQUE
             assert final_state.candidates[0].data["_embedding"] == [1.0]
             
             assert final_state.candidates[1].status == ScenarioStatus.REJECTED
             assert "דומים מדי" in final_state.candidates[1].critique 
             
             assert final_state.candidates[2].status == ScenarioStatus.DRAFT

    def test_deduplicator_node_embed_fail(self):
        """Test fallback when embedding fails inside node."""
        state = SwarmState()
        c1 = state.add_candidate({"title": "C1"})
        c1.status = ScenarioStatus.FORMATTED
        
        with patch("tatlam.graph.nodes.deduplicator._load_existing_embeddings", return_value=([], [])), \
             patch("tatlam.graph.nodes.deduplicator._is_duplicate", return_value=(False, None)): # Embed failed
             
             final_state = deduplicator_node(state)
             
             assert final_state.candidates[0].status == ScenarioStatus.UNIQUE
             # No embedding stored
             assert "_embedding" not in final_state.candidates[0].data

    def test_deduplicator_node_empty(self):
        state = SwarmState()
        final_state = deduplicator_node(state)
        assert final_state == state
