import pytest


# Generate 12 points for valid section (keel to deck) - minimum required for smooth lofting
VALID_SECTION_POINTS = [[0.0, i * 0.3] for i in range(12)]  # 12 points from y=0 to z=3.3


@pytest.mark.asyncio
async def test_symmetry_coupling_adds_missing_section_update(monkeypatch):
    """
    If two bodies are symmetric (offset_y_m ~= ±a) and the proposer updates one body's
    section points, we should deterministically add an UPDATE for the paired body's
    section at the same station (if it exists).
    """
    from magnet.agents.geometry_proposer import GeometryProposer, DesignProgram, GeometryOperation

    class FakeLLM:
        async def complete_json(self, *args, **kwargs):
            return DesignProgram(
                program_id="p",
                version=1,
                operations=[
                    GeometryOperation(
                        op="UPDATE",
                        type="geometry.section",
                        id="bow_port",
                        params={"points": VALID_SECTION_POINTS},
                        reasoning="update port bow",
                        confidence=0.9,
                    )
                ],
                constraints=[],
            )

    proposer = GeometryProposer(FakeLLM())
    state = {
        "resources": {
            "port": {"_type": "geometry.body", "offset_y_m": -5.0},
            "stbd": {"_type": "geometry.body", "offset_y_m": 5.0},
            "bow_port": {"_type": "geometry.section", "body_id": "port", "station": 0.0, "points": VALID_SECTION_POINTS},
            "bow_stbd": {"_type": "geometry.section", "body_id": "stbd", "station": 0.0, "points": VALID_SECTION_POINTS},
        }
    }
    res = await proposer.propose("make bow finer", current_state=state)
    assert res.success
    ids = [op.id for op in res.program.operations]
    assert "bow_port" in ids
    assert "bow_stbd" in ids, "Expected symmetry coupling to add UPDATE for paired body's section"


@pytest.mark.asyncio
async def test_symmetry_coupling_noop_when_paired_section_missing(monkeypatch):
    from magnet.agents.geometry_proposer import GeometryProposer, DesignProgram, GeometryOperation

    class FakeLLM:
        async def complete_json(self, *args, **kwargs):
            return DesignProgram(
                program_id="p",
                version=1,
                operations=[
                    GeometryOperation(
                        op="UPDATE",
                        type="geometry.section",
                        id="bow_port",
                        params={"points": VALID_SECTION_POINTS},
                        reasoning="update port bow",
                        confidence=0.9,
                    )
                ],
                constraints=[],
            )

    proposer = GeometryProposer(FakeLLM())
    state = {
        "resources": {
            "port": {"_type": "geometry.body", "offset_y_m": -5.0},
            "stbd": {"_type": "geometry.body", "offset_y_m": 5.0},
            "bow_port": {"_type": "geometry.section", "body_id": "port", "station": 0.0, "points": VALID_SECTION_POINTS},
        }
    }
    res = await proposer.propose("make bow finer", current_state=state)
    assert res.success
    ids = [op.id for op in res.program.operations]
    assert ids.count("bow_port") == 1
    assert len(ids) == 1, "Should not invent new section IDs when paired section is missing"


