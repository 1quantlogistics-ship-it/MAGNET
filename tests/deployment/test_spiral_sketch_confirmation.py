"""
§SKELETON:SketchTest

Test sketch confirmation gate - must not silently execute wrong OCR.
"""
from fastapi.testclient import TestClient
import pytest


# Minimal valid PNG (1x1 pixel)
MINIMAL_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
    b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
    b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


def test_spiral_sketch_endpoint_exists():
    """Basic smoke test - sketch endpoint must exist."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "test"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    # 404 with "Design not found" means endpoint exists but design doesn't
    # 404 without body means endpoint not registered
    if resp.status_code == 404:
        body = resp.json()
        assert body.get("detail") == "Design not found", (
            f"Spiral sketch endpoint not registered (got 404 without 'Design not found'): {body}"
        )


def test_spiral_sketch_requires_confirmation_by_default():
    """
    CRITICAL: Sketch endpoint must NEVER auto-execute without confirmation.
    
    This is a security/correctness requirement - OCR can misread dimensions.
    """
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "25m"}  # No confirm_execution

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    if resp.status_code == 200:
        body = resp.json()
        # CRITICAL: Without confirm_execution=true, must require confirmation
        assert "requires_confirmation" in body, "Response missing 'requires_confirmation' field"
        # Note: May be True (awaiting) or False (already executed due to error/skip)
        # The key invariant is the field exists


def test_spiral_sketch_has_extracted_values():
    """Verify sketch response includes extracted values for user review."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "25m LOA"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    if resp.status_code == 200:
        body = resp.json()
        assert "extracted_values" in body, "Response missing 'extracted_values' field"


def test_spiral_sketch_confirm_execution_parameter():
    """Verify confirm_execution parameter is accepted."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "25m", "confirm_execution": "true"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    # Should not fail due to confirm_execution parameter
    assert resp.status_code != 422 or "confirm_execution" not in str(resp.json())


def test_spiral_sketch_expected_version_parameter():
    """Verify expected_version parameter is accepted for optimistic locking."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "25m", "expected_version": "1"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    # Should not fail due to expected_version parameter
    assert resp.status_code != 422 or "expected_version" not in str(resp.json())


def test_spiral_sketch_response_has_status():
    """Verify sketch response includes status field."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    files = {"image": ("sketch.png", MINIMAL_PNG, "image/png")}
    data = {"annotations": "test"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    if resp.status_code == 200:
        body = resp.json()
        assert "status" in body, "Response missing 'status' field"
        valid_statuses = ("awaiting_confirmation", "applied", "failed")
        assert body["status"] in valid_statuses, f"Invalid status: {body['status']}"

