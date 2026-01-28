"""
UI Torture Guard (text-level): New Blank Design rebind must reset truth state.

We don't have a JS test runner in this repo, so this is a lightweight regression
guard that ensures the reset/new-design commands explicitly rebind the 3D scene
to the new design_id and reset the truth badge immediately.
"""

from pathlib import Path


def test_backend_adapter_rebinds_scene_on_new_and_reset():
    p = Path("magnet/ui_v2/js/backend-adapter.js")
    txt = p.read_text(encoding="utf-8")

    # Ensure we rebind the scene manager to the new designId
    assert "setDesignContext" in txt, "Expected backend-adapter to call scene-manager setDesignContext"

    # Ensure we explicitly reset truth badge to DECOUPLED during design switch/reset
    assert "setTruthBadge?.('DECOUPLED'" in txt or "setTruthBadge?.(\"DECOUPLED\"" in txt, \
        "Expected backend-adapter to reset truth badge to DECOUPLED on design switch/reset"

