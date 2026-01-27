import pytest


class FakeLLM:
    """
    Minimal fake that mimics LLMClient.complete behavior for GeometryProposer.
    """

    def __init__(self, seq):
        self._seq = list(seq)

    async def complete(self, prompt, **kwargs):
        item = self._seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return str(item)

def _program_min_hull_json(*, varying_beam: bool = True) -> str:
    # 7 sections, with (optionally) increasing max beam so section_metric:max_half_beam_m varies.
    def sec(i: int, st: float, half_beam: float) -> dict:
        # simple open curve keel->sheer, z>=0 (baseline-up)
        pts = [[0.0, 0.0], [0.2 * half_beam, 0.2], [0.8 * half_beam, 0.8], [half_beam, 1.5]]
        return {
            "op": "CREATE",
            "type": "geometry.section",
            "id": f"s{i}",
            "params": {"section_id": f"s{i}", "body_id": "main_hull", "station": st, "points": pts, "edge_types": ["smooth"] * len(pts)},
            "reasoning": "x",
            "confidence": 1.0,
        }

    halfs = [1.5, 1.6, 1.8, 2.0, 2.1, 2.25, 2.4] if varying_beam else [2.0] * 7
    ops = [
        {"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0},
        *[sec(i, st, halfs[i]) for i, st in enumerate([0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0])],
        {"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0},
    ]
    import json
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_invalid_json_repairs_from_raw_response():
    from magnet.agents.geometry_proposer import GeometryProposer
    # Two-block response with fences and trailing text (parser must extract clean JSON).
    raw = """Here you go:
VESSEL_THINKING_PASS
```json
{"station_plan":{"count":7,"distribution":"uniform","explicit_xs":null,"rationale":"x"},
 "dof_schema":[{"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],"anchor_points":[{"x":0.0,"value":1.5},{"x":0.5,"value":2.0},{"x":1.0,"value":2.4}],"interpolation":"linear","defaulted":false,"consequence":null}],
 "verification_schema":[{"type":"varies","name":"beam_varies","target":"beam_schedule"}],
 "closure_proof":[{"check_name":"beam_varies","result":"PASS","computed":{"span":0.9}}],
 "binding_table":[{"dof_name":"beam_schedule","binds_to":["section_metric:max_half_beam_m"],"observation_targets":[{"observable_id":"section_metric:max_half_beam_m","span_min":0.1}]}]
}
```
GEOMETRY_PROGRAM
```json
""" + _program_min_hull_json(varying_beam=True) + """
```
extra trailing text"""

    llm = FakeLLM(
        [
            raw,
        ]
    )
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is True
    assert res.program is not None


@pytest.mark.asyncio
async def test_invalid_json_retries_then_succeeds():
    from magnet.agents.geometry_proposer import GeometryProposer

    # First response: missing thinking pass marker (forces retry); second is valid.
    bad = """GEOMETRY_PROGRAM
```json
""" + _program_min_hull_json(varying_beam=True) + """
```"""
    good = """VESSEL_THINKING_PASS
```json
{"station_plan":{"count":7,"distribution":"uniform","explicit_xs":null,"rationale":"x"},
 "dof_schema":[{"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],"anchor_points":[{"x":0.0,"value":1.5},{"x":0.5,"value":2.0},{"x":1.0,"value":2.4}],"interpolation":"linear","defaulted":false,"consequence":null}],
 "verification_schema":[{"type":"varies","name":"beam_varies","target":"beam_schedule"}],
 "closure_proof":[{"check_name":"beam_varies","result":"PASS","computed":{"span":0.9}}],
 "binding_table":[{"dof_name":"beam_schedule","binds_to":["section_metric:max_half_beam_m"],"observation_targets":[{"observable_id":"section_metric:max_half_beam_m","span_min":0.1}]}]
}
```
GEOMETRY_PROGRAM
```json
""" + _program_min_hull_json(varying_beam=True) + """
```"""

    llm = FakeLLM([bad, good])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is True
    assert res.program is not None
    # proposer must make surface intent explicit (contract-based compile)
    for op in (res.program.operations or []):
        if op.type == "geometry.surface":
            assert op.params.get("surface_definition") in ("smooth", "panelized")


@pytest.mark.asyncio
async def test_proposer_enforces_loft_correspondence_contracts():
    """
    v0 hardening: proposer must not emit a lofted surface without explicit section_ids,
    and sections should share a single point count with a consistent hard-edge index.
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    # Minimal, intentionally inconsistent program: 2 sections with different point counts and hard indices.
    prog = """VESSEL_THINKING_PASS
```json
{"station_plan":{"count":7,"distribution":"uniform","explicit_xs":null,"rationale":"x"},
 "dof_schema":[{"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],"anchor_points":[{"x":0.0,"value":1.0},{"x":0.5,"value":2.0},{"x":1.0,"value":1.4}],"interpolation":"linear","defaulted":false,"consequence":null}],
 "verification_schema":[{"type":"varies","name":"beam_varies","target":"beam_schedule"}],
 "closure_proof":[{"check_name":"beam_varies","result":"PASS","computed":{"span":1.0}}],
 "binding_table":[{"dof_name":"beam_schedule","binds_to":["section_metric:max_half_beam_m"],"observation_targets":[{"observable_id":"section_metric:max_half_beam_m","span_min":0.0}]}]
}
```
GEOMETRY_PROGRAM
```json
{
  "program_id": "p",
  "version": 1,
  "operations": [
    {"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0},
    {"op": "CREATE", "type": "geometry.section", "id": "s0", "params": {"section_id": "s0", "body_id": "main_hull", "station": 0.0, "points": [[0, -1],[1,0],[2,1]], "edge_types": ["smooth","hard","smooth"]}, "reasoning": "x", "confidence": 1.0},
    {"op": "CREATE", "type": "geometry.section", "id": "s1", "params": {"section_id": "s1", "body_id": "main_hull", "station": 1.0, "points": [[0, -1],[1,0],[1.5,0.5],[2,1]], "edge_types": ["smooth","smooth","hard","smooth"]}, "reasoning": "x", "confidence": 1.0},
    {"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0}
  ],
  "constraints": []
}
```"""

    llm = FakeLLM([prog])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}})
    assert res.success is True
    program = res.program
    assert program is not None

    secs = [op for op in program.operations if op.type == "geometry.section"]
    assert len(secs) >= 2
    counts = sorted({len(op.params.get("points") or []) for op in secs})
    assert len(counts) == 1

    hard_patterns = sorted({tuple(i for i,e in enumerate(op.params.get("edge_types") or []) if str(e).lower()=="hard") for op in secs})
    assert len(hard_patterns) == 1

    surfs = [op for op in program.operations if op.type == "geometry.surface"]
    assert surfs and surfs[0].params.get("section_ids")


@pytest.mark.asyncio
async def test_invalid_json_twice_returns_clear_error():
    from magnet.agents.geometry_proposer import GeometryProposer
    bad1 = "not json at all"
    bad2 = "still not json"

    llm = FakeLLM([bad1, bad2])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error is not None
    assert "thinking_pass_missing" in res.error.lower() or "llm" in res.error.lower()

