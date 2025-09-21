from __future__ import annotations

import run_batch


class DummyBadRequest(Exception):
    pass


class FakeClient:
    def __init__(self, effects):
        self.effects = effects
        self.calls = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        effect = self.effects[len(self.calls) - 1]
        if isinstance(effect, Exception):
            raise effect
        return effect


def test_chat_create_safe_drops_temperature(monkeypatch):
    monkeypatch.setattr(run_batch, "BadRequestError", DummyBadRequest)
    client = FakeClient([DummyBadRequest("temperature too high"), {"ok": True}])
    result = run_batch.chat_create_safe(client, temperature=0.9, retries=2, foo="bar")
    assert result == {"ok": True}
    assert "temperature" in client.calls[0]
    assert "temperature" not in client.calls[1]


def test_chat_create_safe_raises_after_retries(monkeypatch):
    monkeypatch.setattr(run_batch, "BadRequestError", DummyBadRequest)
    client = FakeClient([RuntimeError("boom"), RuntimeError("boom")])
    try:
        run_batch.chat_create_safe(client, retries=2)
    except RuntimeError as err:
        assert "boom" in str(err)
    else:  # pragma: no cover - sanity guard
        raise AssertionError("Expected RuntimeError")


def test_coerce_bundle_shape_parses_lists():
    bundle = {
        "scenarios": [
            {
                "title": "בדיקה",
                "steps": '["a", "b"]',
                "required_response": "",
                "decision_points": {"note": "x"},
            }
        ]
    }
    fixed = run_batch.coerce_bundle_shape(bundle)
    scenario = fixed["scenarios"][0]
    assert scenario["steps"] == ["a", "b"]
    assert scenario["required_response"] == []
    assert scenario["decision_points"] == [{"note": "x"}]
