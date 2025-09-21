"""Compatibility wrapper for simulation CLI and API.

Re-exports from `tatlam.sim.engine` to keep imports and CLI usage stable.
The `python tatlam/simulate.py` entry remains supported.
"""

from __future__ import annotations

from tatlam.sim import engine as _engine

SimulationScenario = _engine.SimulationScenario
DEFAULT_PAYLOAD = _engine.DEFAULT_PAYLOAD
SIM_HANDLERS = _engine.SIM_HANDLERS
run_simulations = _engine.run_simulations
load_payload = _engine.load_payload
main = _engine.main

__all__ = [
    "SimulationScenario",
    "DEFAULT_PAYLOAD",
    "SIM_HANDLERS",
    "run_simulations",
    "load_payload",
    "main",
]

if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
