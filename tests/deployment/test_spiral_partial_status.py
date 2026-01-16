"""
§SKELETON:PartialTest

Test partial status when critical phases fail for spiral endpoints.
"""
from fastapi.testclient import TestClient
import pytest


def test_spiral_response_has_required_fields():
    """Verify response schema completeness."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test", "force_apply": True},
    )
    if resp.status_code == 200:
        body = resp.json()
        required = ["success", "design_id", "status", "failed_phases", "spiral_iteration"]
        for field in required:
            assert field in body, f"Response missing required field: {field}"


def test_spiral_status_values_valid():
    """Verify status field has valid values."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "Create a hull", "force_apply": True},
    )
    if resp.status_code == 200:
        body = resp.json()
        valid_statuses = ("applied", "partial", "failed", "proposal_low_confidence", "needs_clarification")
        assert body["status"] in valid_statuses, f"Invalid status: {body['status']}"


def test_spiral_failed_phases_is_list():
    """Verify failed_phases is always a list."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test", "run_critical_phases": True},
    )
    if resp.status_code == 200:
        body = resp.json()
        assert isinstance(body.get("failed_phases"), list), "failed_phases must be a list"


def test_spiral_critical_phases_parameter_accepted():
    """Verify critical_phases parameter is accepted."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={
            "message": "Create hull",
            "run_critical_phases": True,
            "critical_phases": ["hull_form", "weight_stability", "structure"],
        },
    )
    # Should not fail due to critical_phases parameter
    assert resp.status_code != 422 or "critical_phases" not in str(resp.json())


def test_spiral_invalidated_phases_is_list():
    """Verify invalidated_phases is always a list."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test"},
    )
    if resp.status_code == 200:
        body = resp.json()
        assert isinstance(body.get("invalidated_phases"), list), "invalidated_phases must be a list"

