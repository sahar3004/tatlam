from __future__ import annotations

import run_batch


def test_build_batch_user_prompt_contains_category(monkeypatch):
    monkeypatch.setenv("CANDIDATE_COUNT", "3")
    text = run_batch.build_batch_user_prompt("חפץ חשוד ומטען", bundle_id="B1", count=3)
    assert "category: חפץ חשוד ומטען" in text
    assert "count: 3" in text


def test_check_and_repair_fallback(monkeypatch):
    # Force validator client to raise, we should get original bundle back
    def bad_client():  # pragma: no cover - used by monkeypatch only
        class C:
            def __getattr__(self, name):
                raise RuntimeError("no network")

        return C()

    monkeypatch.setattr(run_batch, "client_cloud", bad_client)
    bundle = {"bundle_id": "BTEST", "scenarios": [{"title": "X"}]}
    out = run_batch.check_and_repair(bundle)
    assert out == bundle
