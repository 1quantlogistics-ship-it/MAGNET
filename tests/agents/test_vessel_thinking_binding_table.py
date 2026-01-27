import pytest


class FakeLLM:
    def __init__(self, seq):
        self._seq = list(seq)

    async def complete(self, prompt, **kwargs):
        return str(self._seq.pop(0))


def _resp(thinking_json: str, program_json: str) -> str:
    return f"""VESSEL_THINKING_PASS
```json
{thinking_json}
```
GEOMETRY_PROGRAM
```json
{program_json}
```"""


def _program_two_sections_identical() -> str:
    # 7 sections with identical max beam -> span=0 for section_metric:max_half_beam_m
    import json

    def sec(i: int, st: float) -> dict:
        pts = [[0.0, 0.0], [0.3, 0.2], [1.0, 0.8], [2.0, 1.5]]
        return {
            "op": "CREATE",
            "type": "geometry.section",
            "id": f"s{i}",
            "params": {"section_id": f"s{i}", "body_id": "main_hull", "station": st, "points": pts, "edge_types": ["smooth"] * len(pts)},
            "reasoning": "x",
            "confidence": 1.0,
        }

    ops = [
        {"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0},
        *[sec(i, st) for i, st in enumerate([0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0])],
        {"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0},
    ]
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_unbound_dof_with_varies_check_fails_closed():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":1.0},{"x":1.0,"value":2.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"beam_varies","target":"beam_schedule"}
      ],
      "closure_proof": [
        {"check_name":"beam_varies","result":"PASS","computed":{"span":1.0}}
      ],
      "binding_table": []
    }"""
    prog = _program_two_sections_identical()
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()


@pytest.mark.asyncio
async def test_unknown_observable_id_fails_closed():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":1.0},{"x":1.0,"value":2.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"beam_varies","target":"beam_schedule"}
      ],
      "closure_proof": [
        {"check_name":"beam_varies","result":"PASS","computed":{"span":1.0}}
      ],
      "binding_table": [
        {"dof_name":"beam_schedule","binds_to":["section_metric:unknown_metric"],"observation_targets":[{"observable_id":"section_metric:unknown_metric","span_min":0.1}]}
      ]
    }"""
    prog = _program_two_sections_identical()
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()


@pytest.mark.asyncio
async def test_geometry_observation_mismatch_fails_closed():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"beam_schedule","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":1.0},{"x":1.0,"value":2.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"beam_varies","target":"beam_schedule"}
      ],
      "closure_proof": [
        {"check_name":"beam_varies","result":"PASS","computed":{"span":1.0}}
      ],
      "binding_table": [
        {"dof_name":"beam_schedule","binds_to":["section_metric:max_half_beam_m"],"observation_targets":[{"observable_id":"section_metric:max_half_beam_m","span_min":0.1}]}
      ]
    }"""
    # Geometry has constant beam, so span_min fails.
    prog = _program_two_sections_identical()
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()

