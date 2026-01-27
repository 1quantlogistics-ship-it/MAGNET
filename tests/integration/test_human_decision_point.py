from fastapi.testclient import TestClient


def test_human_decision_point_blocks_downstream_phases_until_approved(monkeypatch):
    """
    Human Decision Point:
    - If stability is severe (GM < 0), the Conductor sets kernel.awaiting_human_decision=true.
    - Downstream phases are blocked (status=BLOCKED) but should not hard-fail the request.
    - Approval clears the flag.
    """
    from magnet.kernel.conductor import Conductor
    from magnet.kernel.enums import PhaseStatus
    from magnet.kernel.registry import PhaseRegistry
    from magnet.core.state_manager import StateManager

    sm = StateManager()
    sm.begin_transaction()
    # Minimal mission dependency
    sm.set("mission.max_speed_kts", 10.0, source="test")
    # Prevent Conductor from invoking hull synthesis during the hull phase.
    # Provide non-baseline values with real provenance.
    sm.set("hull.lwl", 10.0, source="user")
    sm.set("hull.beam", 3.0, source="user")
    sm.set("hull.draft", 1.0, source="user")
    sm.set("hull.cb", 0.55, source="user")
    sm.set("hull.depth", 2.0, source="user")

    # Fake validators that satisfy each phase dependency chain up to stability
    class _State:
        def __init__(self, value: str):
            self.value = value

    class _Result:
        def __init__(self, state_value: str = "passed", error_message: str | None = None):
            self.state = _State(state_value)
            self.error_message = error_message

    class PassValidator:
        def validate(self, state_manager, context):
            return _Result("passed")

    class HydroValidator:
        def validate(self, state_manager, context):
            state_manager.set("hull.kb_m", 1.0, source="test")
            state_manager.set("hull.bm_m", 1.0, source="test")
            state_manager.set("hull.displacement_mt", 10.0, source="test")
            state_manager.set("hull.displacement_m3", 9.756, source="test")
            state_manager.set("hull.freeboard", 1.0, source="test")
            return _Result("passed")

    class WeightValidator:
        def validate(self, state_manager, context):
            # Provide KG inputs for stability module
            state_manager.set("weight.lightship_vcg_m", 10.0, source="test")  # huge KG => negative GM
            state_manager.set("weight.lightship_weight_mt", 10.0, source="test")
            return _Result("passed")

    class StabilitySevereValidator:
        def validate(self, state_manager, context):
            state_manager.set("stability.gm_transverse_m", -0.25, source="test")
            state_manager.set("stability.gm_m", -0.25, source="test")
            return _Result("warning")

    class FailIfRunValidator:
        def validate(self, state_manager, context):
            raise AssertionError("Downstream validator should not run while awaiting_human_decision")

    registry = PhaseRegistry(load_defaults=True)
    conductor = Conductor(state_manager=sm, registry=registry)

    # Register required validators referenced by default phases
    conductor.register_validator("mission/requirements", PassValidator())
    conductor.register_validator("hull/form", PassValidator())
    conductor.register_validator("physics/hydrostatics", HydroValidator())
    conductor.register_validator("structure/scantlings", PassValidator())
    conductor.register_validator("propulsion/sizing", PassValidator())
    conductor.register_validator("weight/estimation", WeightValidator())
    conductor.register_validator("stability/intact_gm", StabilitySevereValidator())
    conductor.register_validator("stability/gz_curve", PassValidator())

    # Downstream phases should be blocked; if validator runs, test fails.
    conductor.register_validator("loading/computer", FailIfRunValidator())
    conductor.register_validator("arrangement/generator", FailIfRunValidator())
    conductor.register_validator("compliance/regulatory", FailIfRunValidator())
    conductor.register_validator("production/planning", FailIfRunValidator())
    conductor.register_validator("cost/estimation", FailIfRunValidator())
    conductor.register_validator("optimization/design", FailIfRunValidator())
    conductor.register_validator("reporting/generator", FailIfRunValidator())

    # Satisfy dependency chain
    assert conductor.run_phase("mission").status == PhaseStatus.COMPLETED
    assert conductor.run_phase("hull").status == PhaseStatus.COMPLETED
    assert conductor.run_phase("structure").status == PhaseStatus.COMPLETED
    assert conductor.run_phase("propulsion").status == PhaseStatus.COMPLETED
    assert conductor.run_phase("weight").status == PhaseStatus.COMPLETED

    stability = conductor.run_phase("stability")
    assert stability.status == PhaseStatus.COMPLETED
    assert sm.get("kernel.awaiting_human_decision") is True
    assert sm.get("kernel.human_decision_request") is not None

    # Downstream blocked
    loading = conductor.run_phase("loading")
    assert loading.status == PhaseStatus.BLOCKED
    assert loading.errors == []

    # Approve by directly clearing flag (endpoint tested separately)
    sm.set("kernel.awaiting_human_decision", False, source="test")
    loading2 = conductor.run_phase("loading")
    # For this test, we only assert the Human Decision Point block is cleared.
    # The loading phase may still be blocked by normal input/output contracts.
    assert not (loading2.status == PhaseStatus.BLOCKED and loading2.errors == [])


def test_approve_decision_endpoint_clears_flag():
    from magnet.deployment.api import create_fastapi_app
    from magnet.deployment.design_store import DesignStore

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    r = client.post("/api/v1/designs", json={"name": "hdp"})
    assert r.status_code == 200, r.text
    design_id = r.json()["design_id"]

    store = DesignStore(None)
    sm = store.load(design_id)
    sm.begin_transaction()
    sm.set("kernel.awaiting_human_decision", True, source="test")
    store.save(design_id, state_manager=sm)

    r = client.post(
        f"/api/v1/designs/{design_id}/approve_decision",
        json={
            "decision": "CONTINUE_DESPITE_WARNING",
            "approved_by": "test_user",
            "timestamp": "2026-01-14T00:00:00Z",
            "rationale": "testing",
            "acknowledged_risks": ["GM < 0 will capsize"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True

    sm2 = store.load(design_id)
    assert sm2.get("kernel.awaiting_human_decision") is False
    token = sm2.get("kernel.human_decision_token")
    assert isinstance(token, dict)
    assert token.get("decision") == "CONTINUE_DESPITE_WARNING"

