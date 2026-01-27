from fastapi.testclient import TestClient


def test_spiral_persists_vessel_thinking_pass_into_metadata(monkeypatch):
    """
    Regression: spiral/chat must persist the VESSEL_THINKING_PASS artifact into design state metadata
    (so we can audit DOFs/bindings/targets later).

    Contract:
    - Proposer returns vessel_thinking_pass + hash
    - spiral/chat executes the program in a single commit that also stores metadata.vessel_thinking_pass
    """
    from magnet.deployment.api import create_fastapi_app

    # Patch proposer so we don't depend on a live LLM in tests.
    from magnet.agents import geometry_proposer as gp

    # Minimal valid hull program (body + 7 polygon sections + lofted surface).
    # Points are 10-point keel->deck open curves with strictly increasing z.
    program_text = "\n".join(
        [
            'CREATE geometry.body main { body_id: "main", body_type: "test_hull", physics_category: "surface_piercing", offset_x_m: 0.0, offset_y_m: 0.0, offset_z_m: 0.0 }',
            *[
                (
                    f'CREATE geometry.section s{i} {{ section_id: "s{i}", body_id: "main", station: {st:.3f}, '
                    'points: [[0.0,-1.0],[0.2,-0.9],[0.5,-0.7],[0.9,-0.5],[1.2,-0.2],[1.4,0.0],[1.5,0.3],[1.45,0.7],[1.35,1.1],[1.25,1.5]] }'
                )
                for i, st in enumerate([0.00, 0.10, 0.22, 0.38, 0.55, 0.76, 0.95])
            ],
            'CREATE geometry.surface surf { surface_id: "surf", body_id: "main", definition: "lofted", physics_category: "surface_piercing", surface_definition: "smooth", section_ids: ["s0","s1","s2","s3","s4","s5","s6"] }',
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
                program_text=program_text,
                raw_response="",
                vessel_thinking_pass={
                    "schema_version": "0.4",
                    "station_plan": {"count": 7, "distribution": "cosine"},
                    "dof_schema": [],
                    "verification_schema": [],
                    "closure_proof": [],
                    "binding_table": [],
                },
                vessel_thinking_pass_hash="hash_test_123",
            )

    monkeypatch.setattr(gp, "create_geometry_proposer", lambda *a, **k: FakeProposer())

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    r = client.post("/api/v1/designs", json={"name": "test"})
    assert r.status_code == 200, r.text
    design_id = r.json().get("design_id")
    assert design_id

    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "make it viking-ish", "force_apply": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True

    # Verify persisted artifact via DesignStore (tests run under a per-process root_dir).
    from magnet.deployment.design_store import DesignStore

    store = DesignStore(container=None)
    sm = store.load(design_id)
    meta = sm.to_dict().get("metadata") or {}
    assert "vessel_thinking_pass" in meta
    assert "vessel_thinking_pass_hash" in meta
    assert meta["vessel_thinking_pass_hash"] == "hash_test_123"

