from __future__ import annotations

import types

from openai import BadRequestError

import run_batch


class DummyBadRequest(BadRequestError):
    def __init__(self, message: str = "bad"):
        super().__init__(message, response=None)


def test_chat_create_safe_retries_and_succeeds(monkeypatch):
    calls = []

    class Fake:
        def __init__(self):
            self.chat = types.SimpleNamespace(completions=self)

        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) < 3:
                raise DummyBadRequest("try again")
            return {"ok": True}

    monkeypatch.setattr(run_batch, "BadRequestError", DummyBadRequest)
    monkeypatch.setattr(run_batch, "time", types.SimpleNamespace(sleep=lambda x: None))
    out = run_batch.chat_create_safe(Fake(), retries=3)
    assert out == {"ok": True}
