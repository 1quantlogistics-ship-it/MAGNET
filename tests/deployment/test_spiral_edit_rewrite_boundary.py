from fastapi.testclient import TestClient


def test_spiral_blocks_rewrite_in_edit_mode_until_confirmed(monkeypatch):
    """
    Contract:
    - If a design already has a hull shell, spiral defaults to EDIT mode.
    - In EDIT mode, a proposer output that uses CREATE geometry.body/section/surface is treated as a REWRITE attempt
      and must return needs_clarification unless the user explicitly confirms REWRITE.
    """
    from magnet.deployment.api import create_fastapi_app
    from magnet.agents import geometry_proposer as gp

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # Create a design
    r = client.post("/api/v1/designs", json={"name": "test"})
    assert r.status_code == 200, r.text
    design_id = r.json().get("design_id")
    assert design_id

    # Seed an initial hull via direct JSON program (no LLM). This establishes "existing hull" for EDIT mode.
    seed = {
        "operations": [
            {
                "op": "CREATE",
                "type": "geometry.body",
                "id": "main",
                "params": {"body_id": "main", "body_type": "seed", "physics_category": "surface_piercing"},
            },
            *[
                {
                    "op": "CREATE",
                    "type": "geometry.section",
                    "id": f"s{i}",
                    "params": {
                        "section_id": f"s{i}",
                        "body_id": "main",
                        "station": float(st),
                        "points": [[0.0, -1.0], [1.0, 0.0]],
                    },
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
                    "physics_category": "surface_piercing",
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
    body = r.json()
    assert body["success"] is True
    assert body["status"] in ("applied", "partial")

    # Fake proposer returns a rewrite-shaped program (CREATEs) + thinking pass.
    rewrite_program = "\n".join(
        [
            'CREATE geometry.body main { body_id: "main", body_type: "rewrite", physics_category: "surface_piercing", offset_x_m: 0.0, offset_y_m: 0.0, offset_z_m: 0.0 }',
            'CREATE geometry.section s0 { section_id: "s0", body_id: "main", station: 0.02, points: [[0.0,-1.0],[1.0,0.0]] }',
            'CREATE geometry.surface surf { surface_id: "surf", body_id: "main", definition: "lofted", physics_category: "surface_piercing", surface_definition: "smooth", section_ids: ["s0"] }',
        ]
    )

    class FakeProposer:
        async def propose(self, intent, current_state=None, constraints=None, validation_history=None, shape_document=None, **kwargs):
            return gp.ProposerResult(
                success=True,
                program=gp.DesignProgram(
                    program_id="test_program",
                    version=1,
                    operations=[
                        gp.GeometryOperation(
                            op="CREATE",
                            type="geometry.body",
                            id="main",
                            params={"body_id": "main"},
                            reasoning="test",
                            confidence=0.9,
                        )
                    ],
                    constraints=[],
                ),
                program_text=rewrite_program,
                raw_response="",
                vessel_thinking_pass={
                    "schema_version": "0.4",
                    "station_plan": {"count": 8, "distribution": "cosine"},
                    "dof_schema": [],
                    "verification_schema": [],
                    "closure_proof": [],
                    "binding_table": [],
                },
                vessel_thinking_pass_hash="hash_rewrite_1",
            )

    monkeypatch.setattr(gp, "create_geometry_proposer", lambda *a, **k: FakeProposer())

    # Attempt edit: should be blocked as needs_clarification
    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "more aggressive", "force_apply": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert any(q.get("id") == "edit_rewrite_boundary_violation" for q in body.get("clarification_questions", []))

    # Confirm rewrite: should bypass gate and apply
    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={
            "message": "more aggressive",
            "force_apply": True,
            "clarification_response": {"id": "edit_rewrite_boundary_violation", "decision": "rewrite"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in ("applied", "partial", "failed"), body  # execution may fail for other reasons; gate must not block
    assert body["status"] != "needs_clarification"

