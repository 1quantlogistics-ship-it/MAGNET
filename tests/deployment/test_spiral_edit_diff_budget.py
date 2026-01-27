from fastapi.testclient import TestClient


def test_spiral_edit_mode_diff_budget_requires_rewrite_confirmation(monkeypatch):
    from magnet.deployment.api import create_fastapi_app
    from magnet.agents import geometry_proposer as gp

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # Create a design
    r = client.post("/api/v1/designs", json={"name": "test"})
    assert r.status_code == 200, r.text
    design_id = r.json().get("design_id")
    assert design_id

    # Seed an initial hull via direct JSON program (no LLM).
    seed = {
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": "main", "params": {"body_id": "main"}},
            *[
                {
                    "op": "CREATE",
                    "type": "geometry.section",
                    "id": f"s{i}",
                    "params": {"section_id": f"s{i}", "body_id": "main", "station": float(st), "points": [[0.0, -1.0], [1.0, 0.0]]},
                }
                for i, st in enumerate([0.00, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95])
            ],
            {
                "op": "CREATE",
                "type": "geometry.surface",
                "id": "surf",
                "params": {
                    "surface_id": "surf",
                    "body_id": "main",
                    "definition": "lofted",
                    "surface_definition": "smooth",
                    "section_ids": [f"s{i}" for i in range(8)],
                },
            },
        ]
    }
    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "json: " + __import__("json").dumps(seed), "force_apply": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("applied", "partial")

    # Fake proposer returns an ADJUST over full station range (touches most stations).
    program_text = 'ADJUST section_metric:sheer_z_m AT station_range=(0.0, 1.0) body_id="main" BY +0.2m'

    class FakeProposer:
        async def propose(self, intent, current_state=None, constraints=None, validation_history=None, shape_document=None, **kwargs):
            return gp.ProposerResult(
                success=True,
                program=gp.DesignProgram(
                    program_id="test_program",
                    version=1,
                    operations=[
                        gp.GeometryOperation(
                            op="UPDATE",
                            type="geometry.section",
                            id="s0",
                            params={},
                            reasoning="test",
                            confidence=0.9,
                        )
                    ],
                    constraints=[],
                ),
                program_text=program_text,
                raw_response="",
                vessel_thinking_pass={
                    "schema_version": "0.4",
                    "station_plan": {"count": 8, "distribution": "cosine"},
                    "dof_schema": [],
                    "verification_schema": [],
                    "closure_proof": [],
                    "binding_table": [],
                },
                vessel_thinking_pass_hash="hash_adjust_1",
            )

    monkeypatch.setattr(gp, "create_geometry_proposer", lambda *a, **k: FakeProposer())

    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "raise sheer everywhere", "force_apply": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert any(q.get("id") == "edit_diff_budget_exceeded" for q in body.get("clarification_questions", []))

    # Confirm rewrite: gate should not block (execution may still fail for other reasons).
    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "raise sheer everywhere", "force_apply": True, "clarification_response": {"id": "edit_diff_budget_exceeded", "decision": "rewrite"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] != "needs_clarification"

