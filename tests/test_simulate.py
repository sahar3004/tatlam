import json

import pytest

from tatlam import simulate


def test_run_simulations_produces_expected_keys():
    scenario = simulate.SimulationScenario(
        name="api_rate_limit_spike",
        seed=1337,
        inputs={"requests_per_min": 600},
        failures=[{"t": 45, "type": "remote_429"}],
        expected={"success_rate_pct": ">=99"},
    )
    results = simulate.run_simulations([scenario])
    assert results[0]["result"]["retry_policy"] == "exponential_backoff_jitter"
    assert results[0]["result"]["circuit_breaker_engaged"] is True


def test_main_writes_results(tmp_path):
    out = tmp_path / "sim.json"
    code = simulate.main(["--out", str(out)])
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scenarios"], "Expected at least one scenario"
    assert "metrics" in data


def test_unknown_scenario_raises():
    bad = simulate.SimulationScenario(
        name="unknown",
        seed=1,
        inputs={},
        failures=[],
        expected={},
    )
    with pytest.raises(ValueError):
        simulate.run_simulations([bad])
