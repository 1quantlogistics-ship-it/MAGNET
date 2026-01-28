import os

import pytest


@pytest.mark.parametrize(
    "path,body",
    [
        (
            "/api/v1/designs/MAGNET-TEST/intent/preview",
            {"text": "beam 5m", "mode": "compound"},
        ),
        (
            "/api/v1/designs/MAGNET-TEST/actions",
            {
                "plan_id": "PLAN-1",
                "intent_id": "INTENT-1",
                "design_version_before": 1,
                "actions": [{"action_type": "set", "path": "hull.beam", "value": 5.0}],
            },
        ),
    ],
)
def test_legacy_intent_protocol_returns_410_when_disabled(monkeypatch, path, body):
    """
    Acceptance test (TASK-007):
    Legacy intent→action endpoints must be removed so the Spiral protocol is the
    single authority for mutations. Removed routes return 404.
    """
    from magnet.deployment.api import create_fastapi_app

    try:
        from fastapi.testclient import TestClient
    except Exception as e:  # pragma: no cover
        pytest.skip(f"fastapi test client not available: {e}")

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(path, json=body)
    assert resp.status_code == 404, resp.text


