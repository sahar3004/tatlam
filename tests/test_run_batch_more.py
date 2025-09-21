from __future__ import annotations

from pathlib import Path

import numpy as np
import run_batch


def test_load_gold_examples_fs(tmp_path: Path, monkeypatch):
    folder = tmp_path / "gold_md"
    folder.mkdir()
    (folder / "a.md").write_text("Hello A\nLine2", encoding="utf-8")
    (folder / "b.txt").write_text("Hello B", encoding="utf-8")
    monkeypatch.setenv("GOLD_FS_DIR", str(folder))
    out = run_batch.load_gold_examples()
    assert "a.md" in out and "Hello A" in out


def test_load_gold_from_db(sample_db, monkeypatch):
    # default scope=category, with matching category
    out = run_batch.load_gold_from_db(category="חפץ חשוד ומטען", limit=5)
    assert "קטגוריה" in out or out == ""


def test_build_validator_prompt_and_memory():
    bundle = {"bundle_id": "B", "scenarios": [{"title": "T"}]}
    p = run_batch.build_validator_prompt(bundle)
    assert "Return ONLY valid JSON" in p or "תקין" in p
    mem = run_batch.memory_addendum()
    assert mem["role"] == "system"


def test_evaluate_and_pick(monkeypatch):
    # Monkeypatch scoring to avoid network and control selection
    def fake_score(sc: dict):  # pragma: no cover - used in monkeypatch
        return (100 if sc.get("title") == "A" else 50, sc)

    monkeypatch.setattr(run_batch, "score_one_scenario", fake_score)
    bundle = {"bundle_id": "B", "scenarios": [{"title": "A"}, {"title": "B"}]}
    picked = run_batch.evaluate_and_pick(bundle)
    titles = [s["title"] for s in picked["scenarios"]]
    assert "A" in titles


def test_minimal_title_fix_and_dedup(monkeypatch):
    # Force duplicate detection, rename via minimal_title_fix, and no-op DB save
    monkeypatch.setattr(run_batch, "is_duplicate_title", lambda *a, **k: (True, None))

    class FakeMsg:
        def __init__(self, content: str):
            self.content = content

    class FakeResp:
        def __init__(self, content: str):
            self.choices = [types.SimpleNamespace(message=FakeMsg(content))]

    import types

    monkeypatch.setattr(run_batch, "client_cloud", lambda: object())
    monkeypatch.setattr(
        run_batch,
        "chat_create_safe",
        lambda *a, **k: FakeResp('{"title":"כותרת מותאמת"}'),
    )
    monkeypatch.setattr(run_batch, "embed_text", lambda t: np.array([0.0, 1.0], dtype=np.float32))
    monkeypatch.setattr(run_batch, "save_embedding", lambda *a, **k: None)
    bundle = {"scenarios": [{"title": "A"}]}
    out = run_batch.dedup_and_embed_titles(bundle)
    assert out["scenarios"][0]["title"] == "כותרת מותאמת"
