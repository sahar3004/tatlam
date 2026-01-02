"""
Tests for tatlam.graph.nodes.deduplicator - Deduplicator Node.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from tatlam.graph.state import SwarmState, ScenarioCandidate


class TestDeduplicatorNode:
    """Tests for the deduplicator_node function."""

    def test_deduplicator_skips_empty_candidates(self):
        """Deduplicator should skip if no candidates."""
        from tatlam.graph.nodes.deduplicator import deduplicator_node

        state = SwarmState(category="חפץ חשוד", candidates=[])

        result = deduplicator_node(state)
        # Should complete without error
        assert result is not None

    def test_deduplicator_processes_candidates(self):
        """Deduplicator should process all candidates."""
        from tatlam.graph.nodes.deduplicator import deduplicator_node

        candidates = [
            ScenarioCandidate(data={"title": "תרחיש א", "description": "תיאור 1"}),
            ScenarioCandidate(data={"title": "תרחיש ב", "description": "תיאור 2"}),
        ]
        state = SwarmState(category="חפץ חשוד", candidates=candidates)

        with patch("tatlam.graph.nodes.deduplicator._embed_text", return_value=None):
            with patch(
                "tatlam.graph.nodes.deduplicator._load_existing_embeddings", return_value=([], [])
            ):
                result = deduplicator_node(state)
                assert result is not None

    def test_deduplicator_handles_single_scenario(self):
        """Deduplicator should handle single scenario correctly."""
        from tatlam.graph.nodes.deduplicator import deduplicator_node

        candidates = [ScenarioCandidate(data={"title": "תרחיש יחיד", "description": "תיאור"})]
        state = SwarmState(category="חפץ חשוד", candidates=candidates)

        with patch("tatlam.graph.nodes.deduplicator._embed_text", return_value=None):
            with patch(
                "tatlam.graph.nodes.deduplicator._load_existing_embeddings", return_value=([], [])
            ):
                result = deduplicator_node(state)
                assert len(result.candidates) == 1


class TestCosineSimilarity:
    """Tests for the _cosine_similarity function."""

    def test_cosine_similarity_identical(self):
        """Identical vectors should have similarity 1.0."""
        from tatlam.graph.nodes.deduplicator import _cosine_similarity

        vec = np.array([1.0, 2.0, 3.0])
        assert _cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors should have similarity 0.0."""
        from tatlam.graph.nodes.deduplicator import _cosine_similarity

        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])
        assert _cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self):
        """Opposite vectors should have similarity -1.0."""
        from tatlam.graph.nodes.deduplicator import _cosine_similarity

        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([-1.0, 0.0])
        assert _cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_cosine_similarity_zero_vector(self):
        """Zero vectors should return 0.0."""
        from tatlam.graph.nodes.deduplicator import _cosine_similarity

        vec1 = np.array([0.0, 0.0])
        vec2 = np.array([1.0, 2.0])
        assert _cosine_similarity(vec1, vec2) == 0.0


class TestEmbedText:
    """Tests for the _embed_text function."""

    def test_embed_text_no_client(self):
        """Should return None when client unavailable."""
        from tatlam.graph.nodes.deduplicator import _embed_text
        from tatlam.core.llm_factory import ConfigurationError

        with patch("tatlam.core.llm_factory.client_cloud") as mock_client:
            mock_client.side_effect = ConfigurationError("No API key")
            result = _embed_text("some text")
            assert result is None

    def test_embed_text_success(self):
        """Should return embedding array on success."""
        from tatlam.graph.nodes.deduplicator import _embed_text

        mock_cloud = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_cloud.embeddings.create.return_value = mock_response

        with patch("tatlam.core.llm_factory.client_cloud", return_value=mock_cloud):
            result = _embed_text("some text")
            assert result is not None
            assert len(result) == 3

    def test_embed_text_api_error(self):
        """Should return None on API error."""
        from tatlam.graph.nodes.deduplicator import _embed_text

        mock_cloud = MagicMock()
        mock_cloud.embeddings.create.side_effect = Exception("API Error")

        with patch("tatlam.core.llm_factory.client_cloud", return_value=mock_cloud):
            result = _embed_text("some text")
            assert result is None


class TestLoadExistingEmbeddings:
    """Tests for the _load_existing_embeddings function."""

    def test_load_existing_embeddings_empty_db(self):
        """Should return empty lists when no embeddings exist."""
        from tatlam.graph.nodes.deduplicator import _load_existing_embeddings

        with patch("tatlam.infra.db.get_session") as mock_session:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(
                return_value=MagicMock(
                    scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
                )
            )
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_session.return_value = mock_ctx

            titles, embeddings = _load_existing_embeddings()
            assert titles == []
            assert embeddings == []
