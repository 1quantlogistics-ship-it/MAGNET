import json
import math
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


def _sec(*, sid: str, station: float, keel_z: float, deadrise_deg: float) -> dict:
    """
    Build a 12-point open curve (keel -> chine -> sheer) so proposer normalization
    doesn't resample away HARD anchors.
    """
    dy = 2.0
    dz = dy * math.tan(math.radians(deadrise_deg))
    chine_z = keel_z + dz

    # 6 points keel->chine (inclusive)
    pts1 = []
    for i in range(6):
        t = i / 5.0
        pts1.append([dy * t, float(keel_z + t * (chine_z - keel_z))])

    # 6 points chine->sheer (exclusive chine, inclusive sheer)
    sheer_y = dy * 1.15
    sheer_z = float(chine_z + 1.6)
    pts2 = []
    for i in range(1, 7):
        t = i / 6.0
        pts2.append([dy + t * (sheer_y - dy), float(chine_z + t * (sheer_z - chine_z))])

    pts = pts1 + pts2
    edge = ["smooth"] * len(pts)
    edge[5] = "hard"  # chine anchor

    return {
        "op": "CREATE",
        "type": "geometry.section",
        "id": sid,
        "params": {"section_id": sid, "body_id": "main_hull", "station": float(station), "points": pts, "edge_types": edge},
        "reasoning": "x",
        "confidence": 1.0,
    }


def _program_regional() -> str:
    """
    7 stations:
    Canonical convention: station 0=aft, 1=forward.
    - entry region (>=0.75): deadrise varies (24 at 1.0, 18 at 0.88, 18 at 0.75) -> span 6 in entry range
    - run region (<=0.3): constant 18 -> span ~0 in run range
    """
    stations = [0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0]
    ops = [
        {"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0},
    ]

    for i, st in enumerate(stations):
        if st == 1.0:
            beta = 24.0
        elif st >= 0.75:
            beta = 18.0
        else:
            beta = 18.0
        ops.append(_sec(sid=f"s{i}", station=st, keel_z=i * 0.1, deadrise_deg=beta))

    ops.append(
        {"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0}
    )
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_v03_pass_entry_scoped_deadrise_span():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"entry_deadrise","units":"deg","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":24.0},{"x":1.0,"value":18.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"entry_deadrise_varies","target":"entry_deadrise"}
      ],
      "closure_proof": [
        {"check_name":"entry_deadrise_varies","result":"PASS","computed":{"span":6.0}}
      ],
      "binding_table": [
        {"dof_name":"entry_deadrise","binds_to":["section_metric:deadrise_deg_at_chine"],
         "observation_targets":[
           {"observable_id":"section_metric:deadrise_deg_at_chine","span_min":4.0,"station_range":[0.75,1.0]}
         ]}
      ]
    }"""

    prog = _program_regional()
    # Proposer may do a single retry; provide two identical responses.
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is True
    assert res.program is not None


@pytest.mark.asyncio
async def test_v03_fail_run_scoped_deadrise_span_fails_closed():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"run_deadrise","units":"deg","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":18.0},{"x":1.0,"value":18.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"run_deadrise_varies","target":"run_deadrise"}
      ],
      "closure_proof": [
        {"check_name":"run_deadrise_varies","result":"PASS","computed":{"span":0.0}}
      ],
      "binding_table": [
        {"dof_name":"run_deadrise","binds_to":["section_metric:deadrise_deg_at_chine"],
         "observation_targets":[
           {"observable_id":"section_metric:deadrise_deg_at_chine","span_min":4.0,"station_range":[0.0,0.3]}
         ]}
      ]
    }"""

    prog = _program_regional()
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])  # retry repeats failure
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()


@pytest.mark.asyncio
async def test_v03_sample_size_trap_insufficient_stations_is_distinct():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"keel_rocker","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":0.0},{"x":1.0,"value":0.3}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"keel_rocker_varies","target":"keel_rocker"}
      ],
      "closure_proof": [
        {"check_name":"keel_rocker_varies","result":"PASS","computed":{"span":0.3}}
      ],
      "binding_table": [
        {"dof_name":"keel_rocker","binds_to":["longitudinal_metric:keel_slope_deg_p95"],
         "observation_targets":[
           {"observable_id":"longitudinal_metric:keel_slope_deg_p95","span_min":2.0,"station_range":[0.0,0.05]}
         ]}
      ]
    }"""

    prog = _program_regional()
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()
    # Must distinguish “unmeasurable range” from “bad geometry”
    assert "insufficient_stations" in (res.error or "").lower()

