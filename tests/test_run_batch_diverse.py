from __future__ import annotations

import numpy as np

import run_batch


def test_select_top_k_diverse_monkeypatch(monkeypatch):
    # Prepare three items with distinct embeddings
    items = [
        (0.9, {"title": "A", "background": ""}),
        (0.8, {"title": "B", "background": ""}),
        (0.7, {"title": "C", "background": ""}),
    ]

    vectors = {
        "A": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "B": np.array([0.0, 1.0, 0.0], dtype=np.float32),
        "C": np.array([0.0, 0.0, 1.0], dtype=np.float32),
    }

    def fake_embed(text: str):  # pragma: no cover - wrapper mocked
        key = text.split("\n")[0]
        return vectors.get(key, np.array([0.0, 0.0, 0.0], dtype=np.float32))

    monkeypatch.setattr(run_batch, "embed_text", fake_embed)
    chosen = run_batch.select_top_k_diverse(items, k=2)
    assert len(chosen) == 2
    titles = {c["title"] for c in chosen}
    assert titles.issubset({"A", "B", "C"})
