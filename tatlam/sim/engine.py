"""Deterministic scenario simulations for QA dry-runs.

Moved from `tatlam/simulate.py` as part of Phase 2 modularization.
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tatlam.logging_setup import configure_logging

configure_logging()


@dataclass
class SimulationScenario:
    name: str
    seed: int
    inputs: dict[str, Any]
    failures: list[dict[str, Any]]
    expected: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationScenario:
        return cls(
            name=data["name"],
            seed=int(data.get("seed", 0)),
            inputs=dict(data.get("inputs", {})),
            failures=list(data.get("failures", [])),
            expected=dict(data.get("expected", {})),
        )


DEFAULT_PAYLOAD = {
    "scenarios": [
        {
            "name": "api_rate_limit_spike",
            "seed": 1337,
            "inputs": {"requests_per_min": 600, "payload": "valid"},
            "failures": [{"t": 45, "type": "remote_429"}],
            "expected": {
                "success_rate_pct": ">=99",
                "max_p95_latency_ms": "<=800",
                "retry_policy": "exponential_backoff_jitter",
                "idempotency_keys_used": True,
                "circuit_breaker_engaged": True,
            },
        },
        {
            "name": "gsheets_quota_boundary",
            "seed": 2025,
            "inputs": {"batch_size": 5000, "range": "A1:G"},
            "failures": [],
            "expected": {"requests_batched": True, "quota_safe": True},
        },
    ],
    "metrics": [
        "p50_ms",
        "p95_ms",
        "errors",
        "retries",
        "cost_usd",
        "tokens_in",
        "tokens_out",
    ],
}


def _simulate_api_rate_limit(rng: random.Random, scenario: SimulationScenario) -> dict[str, Any]:
    base_latency = 420 + rng.randint(-30, 30)
    p95_latency = base_latency + 280
    errors = 1 if scenario.failures else 0
    retries = errors * 3
    success_rate = 100 - (errors / max(1, scenario.inputs.get("requests_per_min", 1))) * 100
    return {
        "success_rate_pct": round(success_rate, 2),
        "max_p95_latency_ms": p95_latency,
        "retry_policy": "exponential_backoff_jitter",
        "idempotency_keys_used": True,
        "circuit_breaker_engaged": bool(scenario.failures),
        "p50_ms": base_latency,
        "p95_ms": p95_latency,
        "errors": errors,
        "retries": retries,
        "cost_usd": round(0.42 + retries * 0.01, 2),
        "tokens_in": 12_500 + retries * 500,
        "tokens_out": 2_400 + retries * 120,
    }


def _simulate_gsheets_quota(rng: random.Random, scenario: SimulationScenario) -> dict[str, Any]:
    batch_size = scenario.inputs.get("batch_size", 5000)
    batches = max(1, batch_size // 5000)
    latency = 310 + rng.randint(0, 40)
    return {
        "requests_batched": True,
        "quota_safe": True,
        "p50_ms": latency,
        "p95_ms": latency + 90,
        "errors": 0,
        "retries": 0,
        "cost_usd": round(batches * 0.05, 2),
        "tokens_in": batches * 3500,
        "tokens_out": batches * 1700,
    }


SIM_HANDLERS = {
    "api_rate_limit_spike": _simulate_api_rate_limit,
    "gsheets_quota_boundary": _simulate_gsheets_quota,
}


def run_simulations(scenarios: Iterable[SimulationScenario]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sc in scenarios:
        rng = random.Random(sc.seed)  # nosec B311 (deterministic simulation, not crypto)
        handler = SIM_HANDLERS.get(sc.name)
        if handler is None:
            raise ValueError(f"Unknown scenario: {sc.name}")
        result = handler(rng, sc)
        results.append(
            {"name": sc.name, "seed": sc.seed, "result": result, "expected": sc.expected}
        )
    return results


def load_payload(path: Path | None) -> dict[str, Any]:
    if path is None:
        return DEFAULT_PAYLOAD
    with path.open("r", encoding="utf-8") as handle:
        from typing import cast

        return cast(dict[str, Any], json.load(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Tatlam simulations")
    parser.add_argument("payload", nargs="?", help="Path to JSON scenarios payload")
    parser.add_argument(
        "--out", default="artifacts/simulation_results.json", help="Where to write results JSON"
    )
    args = parser.parse_args(argv)

    payload_path = Path(args.payload) if args.payload else None
    payload = load_payload(payload_path)
    scenarios = [SimulationScenario.from_dict(item) for item in payload.get("scenarios", [])]
    metrics = payload.get("metrics", [])

    results = run_simulations(scenarios)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"scenarios": results, "metrics": metrics}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✔ wrote {len(results)} simulation results to {out_path}")
    return 0


__all__ = [
    "SimulationScenario",
    "DEFAULT_PAYLOAD",
    "SIM_HANDLERS",
    "run_simulations",
    "load_payload",
    "main",
]
