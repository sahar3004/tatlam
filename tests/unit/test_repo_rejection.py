
def test_rejection_workflow(in_memory_db):
    # Import inside function to avoid stale module reference due to sys.modules hacking in other tests
    from tatlam.infra.repo import get_repository
    # Force import models to ensure status column is seen by SQLAlchemy
    import tatlam.infra.models
    repo = get_repository()

    # 1. Create a test scenario
    data = {
        "title": "Test Rejection Flow",
        "category": "Test",
        "threat_level": "Low",
        "likelihood": "Low",
        "complexity": "Low",
        "location": "Test",
        "background": "Test",
    }

    # Insert (defaults to pending)
    sid = repo.insert_scenario(data, pending=True)
    assert sid > 0

    # 2. Verify it shows up in default fetch (status=active)
    active = repo.fetch_all()
    # Note: Pending is active
    assert any(s["id"] == sid for s in active)

    # 3. Reject it
    reason = "Too simple"
    success = repo.reject_scenario(sid, reason)
    assert success is True

    # 4. Verify it is GONE from default fetch
    active_after = repo.fetch_all()
    assert not any(s["id"] == sid for s in active_after)

    # 5. Verify it appers in explicit 'rejected' fetch
    rejected = repo.fetch_all(status_filter="rejected")
    target = next((s for s in rejected if s["id"] == sid), None)
    assert target is not None
    assert target["status"] == "rejected"
    assert target["rejection_reason"] == "Too simple"


if __name__ == "__main__":
    # Small scaffold to run this without full pytest harness if needed,
    # but we'll run it via pytest
    test_rejection_workflow()
    print("Verification passed!")
