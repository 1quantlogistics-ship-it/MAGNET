from magnet.agents.geometry_proposer import DesignProgram, GeometryOperation, GeometryProposer


def test_station_convention_inverts_when_bow_and_transom_are_swapped():
    """
    Regression: LLMs often emit station=0 at bow and station=1 at transom.
    Kernel contract is station 0=aft/AP, 1=forward/FP.

    If section ids clearly indicate bow/transom naming, the proposer should invert stations deterministically.
    """
    class _DummyLLM:
        async def complete(self, *a, **k):
            raise RuntimeError("LLM not used in this unit test")

    proposer = GeometryProposer(_DummyLLM())  # type: ignore[arg-type]

    program = DesignProgram(
        program_id="p",
        version=1,
        operations=[
            GeometryOperation(
                op="CREATE",
                type="geometry.section",
                id="section_bow",
                params={"section_id": "section_bow", "body_id": "main", "station": 0.02, "points": [[0.0, -1.0], [1.0, 0.0]]},
                reasoning="",
                confidence=0.9,
            ),
            GeometryOperation(
                op="CREATE",
                type="geometry.section",
                id="section_transom",
                params={"section_id": "section_transom", "body_id": "main", "station": 0.99, "points": [[0.0, -1.0], [1.0, 0.0]]},
                reasoning="",
                confidence=0.9,
            ),
        ],
        constraints=[],
    )

    out = proposer._normalize_station_convention(program)  # type: ignore[attr-defined]
    ops = {op.id: op for op in out.operations}
    assert abs(float(ops["section_bow"].params["station"]) - 0.98) < 1e-9
    assert abs(float(ops["section_transom"].params["station"]) - 0.01) < 1e-9

