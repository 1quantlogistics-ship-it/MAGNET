import math
import json
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
    # Build a 12-point open curve (keel -> chine -> topside -> sheer), baseline-up.
    # This matches the proposer's smoothness floor (target_n >= 12) so resampling won't erase HARD.
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
    pts = pts1 + pts2  # 12 points total

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


def _program_v02(*, deadrise_fwd: float, deadrise_aft: float, keel_step: float) -> str:
    # 7 sections; forward half uses deadrise_fwd, aft half uses deadrise_aft.
    stations = [0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0]
    ops = [
        {"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0},
    ]
    for i, st in enumerate(stations):
        keel_z = i * float(keel_step)
        # Canonical convention: station 0=aft (AP), 1=forward (FP) → forward (bow) is higher station.
        beta = float(deadrise_fwd if st >= 0.5 else deadrise_aft)
        ops.append(_sec(sid=f"s{i}", station=st, keel_z=keel_z, deadrise_deg=beta))
    ops.append(
        {"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0}
    )
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_v02_pass_deadrise_drop_and_keel_slope_thresholds():
    """
    PASS case:
    - deadrise_drop_deg >= 6 (forward 24°, aft 18° => ~6°)
    - keel_slope_deg_p95 >= 2 (keel step ~0.08m over ~2m spacing yields ~2°)
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"deadrise_schedule","units":"deg","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":18.0},{"x":1.0,"value":24.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"deadrise_varies","target":"deadrise_schedule"}
      ],
      "closure_proof": [
        {"check_name":"deadrise_varies","result":"PASS","computed":{"span":6.0}}
      ],
      "binding_table": [
        {"dof_name":"deadrise_schedule","binds_to":["longitudinal_metric:deadrise_drop_deg","longitudinal_metric:keel_slope_deg_p95"],
         "observation_targets":[
           {"observable_id":"longitudinal_metric:deadrise_drop_deg","span_min":6.0},
           {"observable_id":"longitudinal_metric:keel_slope_deg_p95","span_min":2.0}
         ]}
      ]
    }"""
    prog = _program_v02(deadrise_fwd=24.0, deadrise_aft=18.0, keel_step=0.10)
    llm = FakeLLM([_resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is True
    assert res.program is not None


@pytest.mark.asyncio
async def test_v02_fail_deadrise_drop_threshold_fails_closed():
    """
    FAIL case:
    - constant deadrise => deadrise_drop_deg ~ 0, target is 6 => fail-closed after retry
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"deadrise_schedule","units":"deg","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":18.0},{"x":1.0,"value":18.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"deadrise_varies","target":"deadrise_schedule"}
      ],
      "closure_proof": [
        {"check_name":"deadrise_varies","result":"PASS","computed":{"span":0.0}}
      ],
      "binding_table": [
        {"dof_name":"deadrise_schedule","binds_to":["longitudinal_metric:deadrise_drop_deg"],
         "observation_targets":[{"observable_id":"longitudinal_metric:deadrise_drop_deg","span_min":6.0}]}
      ]
    }"""
    # Program keeps deadrise constant 18, keel varies (irrelevant for this test).
    prog = _program_v02(deadrise_fwd=18.0, deadrise_aft=18.0, keel_step=0.10)
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])  # retry repeats failure
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()


@pytest.mark.asyncio
async def test_v02_fail_keel_slope_threshold_fails_closed():
    """
    FAIL case:
    - constant keel_z => keel_slope_deg_p95 ~ 0, target is 2 => fail-closed after retry
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"rocker_schedule","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":0.0},{"x":1.0,"value":0.0}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [],
      "closure_proof": [],
      "binding_table": [
        {"dof_name":"rocker_schedule","binds_to":["longitudinal_metric:keel_slope_deg_p95"],
         "observation_targets":[{"observable_id":"longitudinal_metric:keel_slope_deg_p95","span_min":2.0}]}
      ]
    }"""
    # deadrise varies; keel_step is 0 => constant keel -> slope ~0
    prog = _program_v02(deadrise_fwd=24.0, deadrise_aft=18.0, keel_step=0.0)
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a hull", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()

