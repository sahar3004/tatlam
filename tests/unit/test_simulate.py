"""
Unit tests for tatlam/simulate.py

Tests simulation compatibility wrapper and re-exports.
Target: 100% coverage for all exports
"""
from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSimulateModule:
    """Test suite for simulate.py module."""

    def test_imports_simulation_scenario(self) -> None:
        """Test SimulationScenario is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "SimulationScenario")
        # Verify it's the same as from engine
        from tatlam.sim.engine import SimulationScenario as EngineClass
        assert simulate.SimulationScenario is EngineClass

    def test_imports_default_payload(self) -> None:
        """Test DEFAULT_PAYLOAD is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "DEFAULT_PAYLOAD")
        from tatlam.sim.engine import DEFAULT_PAYLOAD as EngineDefault
        assert simulate.DEFAULT_PAYLOAD is EngineDefault

    def test_imports_sim_handlers(self) -> None:
        """Test SIM_HANDLERS is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "SIM_HANDLERS")
        from tatlam.sim.engine import SIM_HANDLERS as EngineHandlers
        assert simulate.SIM_HANDLERS is EngineHandlers

    def test_imports_run_simulations(self) -> None:
        """Test run_simulations is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "run_simulations")
        assert callable(simulate.run_simulations)
        from tatlam.sim.engine import run_simulations as EngineFunc
        assert simulate.run_simulations is EngineFunc

    def test_imports_load_payload(self) -> None:
        """Test load_payload is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "load_payload")
        assert callable(simulate.load_payload)
        from tatlam.sim.engine import load_payload as EngineFunc
        assert simulate.load_payload is EngineFunc

    def test_imports_main(self) -> None:
        """Test main function is exported from simulate module."""
        from tatlam import simulate

        assert hasattr(simulate, "main")
        assert callable(simulate.main)
        from tatlam.sim.engine import main as EngineMain
        assert simulate.main is EngineMain

    def test_all_exports_defined(self) -> None:
        """Test that __all__ contains all expected exports."""
        from tatlam import simulate

        expected_exports = [
            "SimulationScenario",
            "DEFAULT_PAYLOAD",
            "SIM_HANDLERS",
            "run_simulations",
            "load_payload",
            "main",
        ]

        assert hasattr(simulate, "__all__")
        for export in expected_exports:
            assert export in simulate.__all__, f"Missing export: {export}"

    def test_engine_module_imported(self) -> None:
        """Test that the engine module is properly imported."""
        from tatlam import simulate

        # Access private _engine to verify import
        assert hasattr(simulate, "_engine")
        from tatlam.sim import engine
        assert simulate._engine is engine
