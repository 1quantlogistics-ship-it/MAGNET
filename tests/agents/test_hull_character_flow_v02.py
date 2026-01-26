import json
import math
import pytest


class FakeLLM:
    def __init__(self, seq):
        self._seq = list(seq)
        self._last = str(seq[-1]) if seq else ""

    async def complete(self, prompt, **kwargs):
        # The proposer may legitimately retry once; tests should not assume call count.
        if not self._seq:
            return self._last
        self._last = str(self._seq.pop(0))
        return self._last


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
    dy = 2.0
    dz = dy * math.tan(math.radians(deadrise_deg))
    chine_z = keel_z + dz

    # 12-point curve so proposer normalization doesn't resample away HARD.
    pts1 = []
    for i in range(6):
        t = i / 5.0
        pts1.append([dy * t, float(keel_z + t * (chine_z - keel_z))])
    sheer_y = dy * 1.15
    sheer_z = float(chine_z + 1.6)
    pts2 = []
    for i in range(1, 7):
        t = i / 6.0
        pts2.append([dy + t * (sheer_y - dy), float(chine_z + t * (sheer_z - chine_z))])
    pts = pts1 + pts2

    edge = ["smooth"] * len(pts)
    edge[5] = "hard"
    return {
        "op": "CREATE",
        "type": "geometry.section",
        "id": sid,
        "params": {"section_id": sid, "body_id": "main_hull", "station": float(station), "points": pts, "edge_types": edge},
        "reasoning": "x",
        "confidence": 1.0,
    }


def _program_ok() -> str:
    stations = [0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0]
    ops = [{"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0}]
    for i, st in enumerate(stations):
        keel_z = i * 0.10
        beta = 24.0 if st >= 0.5 else 18.0
        ops.append(_sec(sid=f"s{i}", station=st, keel_z=keel_z, deadrise_deg=beta))
    ops.append({"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0})
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_flow_v02_accepts_when_targets_met():
    """
    Full-flow integration (FakeLLM):
    prompt -> thinking pass + geometry -> observables computed -> targets pass -> accepted
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"warped_deadrise","units":"deg","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":18.0},{"x":1.0,"value":24.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"deadrise_varies","target":"warped_deadrise"}
      ],
      "closure_proof": [
        {"check_name":"deadrise_varies","result":"PASS","computed":{"span":6.0}}
      ],
      "binding_table": [
        {"dof_name":"warped_deadrise","binds_to":["longitudinal_metric:deadrise_drop_deg","longitudinal_metric:keel_slope_deg_p95"],
         "observation_targets":[
           {"observable_id":"longitudinal_metric:deadrise_drop_deg","span_min":6.0},
           {"observable_id":"longitudinal_metric:keel_slope_deg_p95","span_min":2.0}
         ]}
      ]
    }"""
    prog = _program_ok()
    llm = FakeLLM([_resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(
        intent="Create a 72 ft deep-V sportfisher with warped bottom",
        current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}},
    )
    assert res.success is True
    assert res.program is not None
    assert res.vessel_thinking_pass is not None

