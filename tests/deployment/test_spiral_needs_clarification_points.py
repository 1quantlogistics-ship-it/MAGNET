from fastapi.testclient import TestClient


def test_spiral_returns_needs_clarification_for_invalid_section_points(monkeypatch):
    """
    If the proposer produces invalid polygon section points (e.g., [x,y,z] triples),
    spiral/chat must surface needs_clarification instead of committing or failing silently.
    """
    from magnet.deployment.api import create_fastapi_app

    # Patch proposer to simulate the specific failure mode deterministically.
    from magnet.agents import geometry_proposer as gp

    class FakeProposer:
        async def propose(self, intent, current_state=None, validation_history=None):
            # Match the string checks in spiral_endpoints.
            return gp.ProposerResult(
                success=False,
                program=None,
                program_text="",
                raw_response="",
                error=(
                    "geometry.section.points must be 2D [y,z] pairs. "
                    "Do not emit [x,y,z] triples; x comes from station."
                ),
            )

    monkeypatch.setattr(gp, "create_geometry_proposer", lambda *a, **k: FakeProposer())

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # Create a design so the spiral endpoint can load it.
    r = client.post("/api/v1/designs", json={"name": "test"})
    assert r.status_code == 200, r.text
    design_id = r.json().get("design_id")
    assert design_id

    r = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "make it deep v", "force_apply": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "needs_clarification"
    assert body.get("clarification_questions"), "Expected clarification questions"


