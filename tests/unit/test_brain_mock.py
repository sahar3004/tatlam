"""
Unit tests for tatlam/core/brain.py

Tests TrinityBrain class with mocked API clients (NO REAL NETWORK CALLS).
Target: Verify TrinityBrain initialization and client management.

Updated for Phase 1 dependency injection architecture.
"""

import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
class TestBrainMock:
    """Test suite for TrinityBrain with mocked APIs."""

    def test_trinity_brain_initializes(self):
        """Test TrinityBrain can be instantiated without any clients."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert brain is not None

    def test_trinity_brain_has_writer_client_attribute(self):
        """Verify writer_client attribute exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "writer_client")

    def test_trinity_brain_has_judge_client_attribute(self):
        """Verify judge_client attribute exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "judge_client")

    def test_trinity_brain_has_simulator_client_attribute(self):
        """Verify simulator_client attribute exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "simulator_client")

    def test_trinity_brain_dependency_injection(self):
        """Test TrinityBrain accepts injected clients."""
        from tatlam.core.brain import TrinityBrain

        mock_writer = MagicMock(name="MockWriter")
        mock_judge = MagicMock(name="MockJudge")
        mock_simulator = MagicMock(name="MockSimulator")

        brain = TrinityBrain(
            writer_client=mock_writer,
            judge_client=mock_judge,
            simulator_client=mock_simulator,
            auto_initialize=False,
        )

        assert brain.writer_client is mock_writer
        assert brain.judge_client is mock_judge
        assert brain.simulator_client is mock_simulator

    def test_trinity_brain_has_writer_method(self):
        """Test has_writer() returns correct status."""
        from tatlam.core.brain import TrinityBrain

        # Without client
        brain_no_writer = TrinityBrain(auto_initialize=False)
        assert brain_no_writer.has_writer() is False

        # With client
        brain_with_writer = TrinityBrain(writer_client=MagicMock(), auto_initialize=False)
        assert brain_with_writer.has_writer() is True

    def test_trinity_brain_has_judge_method(self):
        """Test has_judge() returns correct status."""
        from tatlam.core.brain import TrinityBrain

        # Without client
        brain_no_judge = TrinityBrain(auto_initialize=False)
        assert brain_no_judge.has_judge() is False

        # With client
        brain_with_judge = TrinityBrain(judge_client=MagicMock(), auto_initialize=False)
        assert brain_with_judge.has_judge() is True

    def test_trinity_brain_has_simulator_method(self):
        """Test has_simulator() returns correct status."""
        from tatlam.core.brain import TrinityBrain

        # Without client
        brain_no_sim = TrinityBrain(auto_initialize=False)
        assert brain_no_sim.has_simulator() is False

        # With client
        brain_with_sim = TrinityBrain(simulator_client=MagicMock(), auto_initialize=False)
        assert brain_with_sim.has_simulator() is True

    def test_trinity_brain_get_status(self):
        """Test get_status() returns dict with all client statuses."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(
            writer_client=MagicMock(),
            judge_client=None,
            simulator_client=MagicMock(),
            auto_initialize=False,
        )

        status = brain.get_status()
        assert isinstance(status, dict)
        assert status["writer"] is True
        assert status["judge"] is False
        assert status["simulator"] is True

    def test_trinity_brain_generate_scenario_stream_exists(self):
        """Verify generate_scenario_stream method exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "generate_scenario_stream")
        assert callable(brain.generate_scenario_stream)

    def test_trinity_brain_audit_scenario_exists(self):
        """Verify audit_scenario method exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "audit_scenario")
        assert callable(brain.audit_scenario)

    def test_trinity_brain_chat_simulation_stream_exists(self):
        """Verify chat_simulation_stream method exists."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)
        assert hasattr(brain, "chat_simulation_stream")
        assert callable(brain.chat_simulation_stream)

    def test_trinity_brain_require_writer_raises_without_client(self):
        """Test _require_writer raises RuntimeError when client is None."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(RuntimeError, match="Writer.*not initialized"):
            brain._require_writer()

    def test_trinity_brain_require_judge_raises_without_client(self):
        """Test _require_judge raises RuntimeError when client is None."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(RuntimeError, match="Judge.*not initialized"):
            brain._require_judge()

    def test_trinity_brain_require_simulator_raises_without_client(self):
        """Test _require_simulator raises RuntimeError when client is None."""
        from tatlam.core.brain import TrinityBrain

        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(RuntimeError, match="Simulator.*not initialized"):
            brain._require_simulator()
