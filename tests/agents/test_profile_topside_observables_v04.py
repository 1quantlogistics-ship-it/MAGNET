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


def _sec(
    *,
    sid: str,
    station: float,
    keel_z: float,
    deadrise_deg: float,
    half_beam: float,
    sheer_z: float,
    sheer_y_factor: float = 1.15,
) -> dict:
    """
    12-point open curve (keel->chine->sheer), HARD at chine.
    - half_beam controls chine y (approx; max_half_beam proxy)
    - sheer_z controls max z (sheer_z_m proxy)
    - sheer_y_factor controls topside y above chine (flare/tumblehome proxy)
    """
    dy = float(half_beam)
    dz = dy * math.tan(math.radians(deadrise_deg))
    chine_z = keel_z + dz

    # 6 points keel->chine (inclusive)
    pts1 = []
    for i in range(6):
        t = i / 5.0
        pts1.append([dy * t, float(keel_z + t * (chine_z - keel_z))])

    # 6 points chine->sheer (exclusive chine, inclusive sheer)
    sheer_y = dy * float(sheer_y_factor)
    pts2 = []
    for i in range(1, 7):
        t = i / 6.0
        pts2.append([dy + t * (sheer_y - dy), float(chine_z + t * (float(sheer_z) - chine_z))])

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


def _program_profile(*, sheer_rise_m: float, entry_narrowing: bool) -> str:
    """
    Create 7 sections:
    - sheer_z increases by sheer_rise_m from aft to forward
    - half_beam decreases forward if entry_narrowing=True
    """
    stations = [0.0, 0.12, 0.25, 0.5, 0.72, 0.88, 1.0]
    ops = [{"op": "CREATE", "type": "geometry.body", "id": "main_hull", "params": {"body_id": "main_hull"}, "reasoning": "x", "confidence": 1.0}]

    aft_sheer = 2.5
    fwd_sheer = aft_sheer + float(sheer_rise_m)

    for i, st in enumerate(stations):
        t = float(st)
        sheer_z = aft_sheer + t * (fwd_sheer - aft_sheer)
        if entry_narrowing:
            hb = 2.6 - 2.0 * t  # narrows forward
        else:
            hb = 2.0  # constant
        ops.append(
            _sec(
                sid=f"s{i}",
                station=st,
                keel_z=-1.5 + 0.2 * t,
                deadrise_deg=22.0,
                half_beam=hb,
                sheer_z=sheer_z,
                sheer_y_factor=(1.35 if st >= 0.72 else 1.10),  # more flare forward region
            )
        )

    ops.append({"op": "CREATE", "type": "geometry.surface", "id": "hull_surface", "params": {"surface_id": "hull_surface", "body_id": "main_hull", "definition": "lofted"}, "reasoning": "x", "confidence": 1.0})
    return json.dumps({"program_id": "p", "version": 1, "operations": ops, "constraints": []})


@pytest.mark.asyncio
async def test_v04_pass_sheer_rise_and_entry_fineness_thresholds():
    """
    PASS:
    - sheer_rise_m >= 0.8
    - entry_fineness_p95 >= 0.05 in the forward region
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"sheer_profile","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":2.5},{"x":1.0,"value":3.3}],
         "interpolation":"linear","defaulted":false,"consequence":null},
        {"type":"schedule","name":"entry_shape","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":2.6},{"x":1.0,"value":0.6}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"sheer_varies","target":"sheer_profile"},
        {"type":"varies","name":"entry_varies","target":"entry_shape"}
      ],
      "closure_proof": [
        {"check_name":"sheer_varies","result":"PASS","computed":{"span":0.8}},
        {"check_name":"entry_varies","result":"PASS","computed":{"span":2.0}}
      ],
      "binding_table": [
        {"dof_name":"sheer_profile","binds_to":["longitudinal_metric:sheer_rise_m"],
         "observation_targets":[{"observable_id":"longitudinal_metric:sheer_rise_m","span_min":0.8}]},
        {"dof_name":"entry_shape","binds_to":["longitudinal_metric:entry_fineness_p95"],
         "observation_targets":[{"observable_id":"longitudinal_metric:entry_fineness_p95","span_min":0.05,"station_range":[0.7,1.0]}]}
      ]
    }"""
    prog = _program_profile(sheer_rise_m=0.8, entry_narrowing=True)
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a vessel", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is True
    assert res.program is not None


@pytest.mark.asyncio
async def test_v04_fail_flat_sheer_fails_closed():
    """
    FAIL: sheer_rise_m target not met.
    """
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"sheer_profile","units":"m","domain":[0,1],
         "anchor_points":[{"x":0.0,"value":2.5},{"x":1.0,"value":2.6}],
         "interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [
        {"type":"varies","name":"sheer_varies","target":"sheer_profile"}
      ],
      "closure_proof": [
        {"check_name":"sheer_varies","result":"PASS","computed":{"span":0.1}}
      ],
      "binding_table": [
        {"dof_name":"sheer_profile","binds_to":["longitudinal_metric:sheer_rise_m"],
         "observation_targets":[{"observable_id":"longitudinal_metric:sheer_rise_m","span_min":0.8}]}
      ]
    }"""
    prog = _program_profile(sheer_rise_m=0.1, entry_narrowing=True)
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a vessel", current_state={"resources": {}, "hull": {"loa": 21.95, "lwl": 21.95}})
    assert res.success is False
    assert res.error and "thinking_pass_invalid" in res.error.lower()

