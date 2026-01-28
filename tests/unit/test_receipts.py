from magnet.core.receipts import new_receipt


def test_receipt_roundtrip_to_dict():
    r = new_receipt(
        receipt_id="r1",
        source="test",
        action="commit",
        design_id="D",
        design_version=3,
        written_paths=["hull.loa", "hull.beam"],
        metadata={"k": "v"},
    )
    d = r.to_dict()
    assert d["receipt_id"] == "r1"
    assert d["source"] == "test"
    assert d["action"] == "commit"
    assert d["design_id"] == "D"
    assert d["design_version"] == 3
    assert "timestamp" in d and isinstance(d["timestamp"], str) and d["timestamp"]
    assert d["written_paths"] == ["hull.loa", "hull.beam"]
    assert d["metadata"]["k"] == "v"

