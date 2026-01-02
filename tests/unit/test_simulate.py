"""
Tests for tatlam/simulate.py - Compatibility wrapper for simulation.
"""

import pytest


class TestSimulateModule:
    """Tests for the simulate.py compatibility wrapper."""

    def test_imports_simulation_scenario(self):
        """Should import SimulationScenario from sim.engine."""
        from tatlam.simulate import SimulationScenario

        assert SimulationScenario is not None

    def test_imports_default_payload(self):
        """Should import DEFAULT_PAYLOAD from sim.engine."""
        from tatlam.simulate import DEFAULT_PAYLOAD

        assert DEFAULT_PAYLOAD is not None

    def test_imports_sim_handlers(self):
        """Should import SIM_HANDLERS from sim.engine."""
        from tatlam.simulate import SIM_HANDLERS

        assert SIM_HANDLERS is not None
        assert isinstance(SIM_HANDLERS, dict)

    def test_imports_run_simulations(self):
        """Should import run_simulations function from sim.engine."""
        from tatlam.simulate import run_simulations

        assert callable(run_simulations)

    def test_imports_load_payload(self):
        """Should import load_payload function from sim.engine."""
        from tatlam.simulate import load_payload

        assert callable(load_payload)

    def test_imports_main(self):
        """Should import main function from sim.engine."""
        from tatlam.simulate import main

        assert callable(main)

    def test_all_exports(self):
        """Should export all expected symbols."""
        from tatlam import simulate

        expected_exports = [
            "SimulationScenario",
            "DEFAULT_PAYLOAD",
            "SIM_HANDLERS",
            "run_simulations",
            "load_payload",
            "main",
        ]
        for export in expected_exports:
            assert hasattr(simulate, export), f"Missing export: {export}"
