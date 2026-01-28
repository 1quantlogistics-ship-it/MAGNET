import pytest


class FakeLLM:
    def __init__(self, seq):
        self._seq = list(seq)

    async def complete(self, prompt, **kwargs):
        item = self._seq.pop(0)
        return str(item)


def _resp(thinking_json: str, program_json: str) -> str:
    return f"""VESSEL_THINKING_PASS
```json
{thinking_json}
```
GEOMETRY_PROGRAM
```json
{program_json}
```"""


@pytest.mark.asyncio
async def test_thinking_pass_missing_blocks_execution():
    from magnet.agents.geometry_proposer import GeometryProposer

    llm = FakeLLM(
        [
            "GEOMETRY_PROGRAM\n```json\n{\"program_id\":\"p\",\"version\":1,\"operations\":[],\"constraints\":[]}\n```",
            "still missing",
        ]
    )
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error
    assert "thinking_pass_missing" in res.error.lower()


@pytest.mark.asyncio
async def test_needs_clarification_variant_is_surfaced():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{"status":"NEEDS_CLARIFICATION","question":"What is the target LOA?"}"""
    prog = """{"program_id":"p","version":1,"operations":[],"constraints":[]}"""
    llm = FakeLLM([_resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="make a boat", current_state={"resources": {}})
    assert res.success is False
    assert res.error and res.error.startswith("NEEDS_CLARIFICATION:")


@pytest.mark.asyncio
async def test_coverage_rule_enforced_non_defaulted_dof_must_have_check():
    from magnet.agents.geometry_proposer import GeometryProposer

    thinking = """{
      "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": null, "rationale": "x"},
      "dof_schema": [
        {"type":"schedule","name":"sheer_z","units":"m","domain":[0,1],"anchor_points":[{"x":0.0,"value":1.0},{"x":1.0,"value":2.0}],"interpolation":"linear","defaulted":false,"consequence":null}
      ],
      "verification_schema": [],
      "closure_proof": []
    }"""
    prog = """{"program_id":"p","version":1,"operations":[],"constraints":[]}"""
    # Provide two identical failures so proposer fails after retry.
    llm = FakeLLM([_resp(thinking, prog), _resp(thinking, prog)])
    proposer = GeometryProposer(llm_client=llm)  # type: ignore[arg-type]
    res = await proposer.propose(intent="noop", current_state={"resources": {}})
    assert res.success is False
    assert res.error
    assert "thinking_pass_invalid" in res.error.lower()

