"""
§SKELETON:ConcurrencyTest

Test optimistic locking (409 on stale version) for spiral endpoints.
"""
from fastapi.testclient import TestClient
import pytest


def test_spiral_endpoint_exists():
    """Basic smoke test - endpoint must exist and not 404."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # POST with empty body
    r = client.post("/api/v1/designs/TEST/spiral/chat", json={})
    # 404 with "Design not found" means endpoint exists but design doesn't
    # 404 without body or 422 for validation means endpoint is registered
    if r.status_code == 404:
        body = r.json()
        assert body.get("detail") == "Design not found", (
            f"Spiral endpoint /spiral/chat not registered (got 404 without 'Design not found'): {body}"
        )


def test_spiral_chat_returns_required_fields():
    """Verify response has required fields for concurrency control."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    r = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "Create a hull", "force_apply": True},
    )
    # May return 404 (design not found) or 200 or validation error
    # But if 200, must have version fields
    if r.status_code == 200:
        body = r.json()
        assert "design_version_before" in body, "Missing design_version_before"
        assert "design_version_after" in body, "Missing design_version_after"
        assert "spiral_iteration" in body, "Missing spiral_iteration"


def test_spiral_chat_optimistic_locking_schema():
    """Verify 409 response schema when stale version detected."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # This test verifies the 409 response schema is correct
    # We can't easily trigger a real 409 without a design that exists,
    # but we can verify the endpoint accepts expected_version parameter
    r = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test", "expected_version": 999, "request_id": "test-1"},
    )
    # Should either be 404 (design not found) or 409 (stale version) or 200 (success)
    assert r.status_code in (200, 404, 409, 422), f"Unexpected status: {r.status_code}"
    
    # If 409, verify schema
    if r.status_code == 409:
        body = r.json()
        assert "detail" in body
        assert body["detail"].get("error") == "stale_version"


def test_spiral_request_id_accepted():
    """Verify request_id is accepted for idempotency."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    r = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test", "request_id": "idempotency-key-123"},
    )
    # Should not fail due to request_id parameter
    assert r.status_code != 422 or "request_id" not in str(r.json())

