from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

import importlib
import run_batch


def test_load_all_embeddings_reads_vectors(sample_db: Path, monkeypatch):
    # Reload config after autouse fixture adjusted DB_PATH
    config = importlib.import_module("config")
    con = sqlite3.connect(sample_db)
    table = config.EMB_TABLE
    con.execute(f"CREATE TABLE IF NOT EXISTS {table} (title TEXT PRIMARY KEY, vector_json TEXT)")
    vec = [0.1, 0.2, 0.3]
    con.execute(
        f"INSERT OR REPLACE INTO {table} (title, vector_json) VALUES (?, ?)",  # noqa: S608
        ("אירוע בדיקה A", json.dumps(vec)),
    )
    con.commit()
    con.close()
    # Ensure the function reads from our temp DB
    monkeypatch.setattr(run_batch, "DB_PATH", str(sample_db))
    titles, vectors = run_batch.load_all_embeddings()
    assert "אירוע בדיקה A" in titles
    assert any(isinstance(v, np.ndarray) for v in vectors)


def test_embed_text_handles_failure(monkeypatch):
    def bad_client():  # pragma: no cover
        class C:
            def __getattr__(self, name):
                raise RuntimeError("no net")

        return C()

    monkeypatch.setattr(run_batch, "client_cloud", bad_client)
    assert run_batch.embed_text("hello") is None


def test_is_duplicate_title_threshold(monkeypatch):
    # Force deterministic vector
    monkeypatch.setattr(run_batch, "embed_text", lambda t: np.array([1.0, 0.0], dtype=np.float32))
    titles = ["X"]
    vecs = [np.array([1.0, 0.0], dtype=np.float32)]
    is_dup, _ = run_batch.is_duplicate_title("X", titles, vecs, threshold=0.9)
    assert is_dup is True
    is_dup2, _ = run_batch.is_duplicate_title("X2", titles, vecs, threshold=0.99)
    assert is_dup2 is True
