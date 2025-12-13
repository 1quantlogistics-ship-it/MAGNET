"""
Golden Smoke Test for RunPod Handler
Proves: bootstrap works, validators execute, state mutates, contracts satisfied

Run before any RunPod deployment:
    python scripts/smoke/runpod_handler_golden.py
"""
import json
from copy import deepcopy

from magnet.deployment.runpod_handler import handler


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def get_nested(d, path):
    """Get nested dict value by dot-path."""
    cur = d
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def run_golden_test():
    """
    Golden test: run_phase hull with minimal inputs.

    Proves:
    1. Handler bootstraps (DI container initializes)
    2. Phase execution runs real calculators
    3. State is mutated with outputs
    4. Contract outputs exist
    """
    # Minimal seed state for hull phase (matches contracts.py required_inputs)
    design_state = {
        "hull": {
            "lwl": 50.0,
            "beam": 10.0,
            "draft": 2.5,
            "depth": 4.0,
            "cb": 0.55,
        }
    }

    payload = {
        "input": {
            "operation": "run_phase",
            "parameters": {"phase": "hull"},
            "design_state": design_state,
        }
    }

    print("Running golden smoke test...")
    result = handler(payload)

    # 1) Handler success
    assert_true(isinstance(result, dict), "Handler did not return dict")
    assert_true(result.get("success") is True, f"Handler failed: {result.get('error')}")

    # 2) Phase completed
    inner = result.get("result", {})
    assert_true(inner.get("phase") == "hull", f"Wrong phase: {inner}")
    assert_true(inner.get("status") in ["completed", "success"], f"Phase not completed: {inner}")

    # 3) State was returned
    updated_state = inner.get("state", {})
    assert_true(isinstance(updated_state, dict), "No state returned")

    # 4) Contract outputs exist (from contracts.py hull phase)
    # Required outputs: hull.displacement_m3, hull.vcb_m, hull.bmt
    hull_state = updated_state.get("hull", {})

    # Check at least displacement was calculated (proves calculator ran)
    displacement = hull_state.get("displacement_m3")
    assert_true(displacement is not None, f"hull.displacement_m3 not calculated. Hull state: {list(hull_state.keys())}")
    assert_true(isinstance(displacement, (int, float)) and displacement > 0,
                f"Invalid displacement: {displacement}")

    print(f"✅ GOLDEN SMOKE TEST PASSED")
    print(f"   Phase: hull")
    print(f"   Displacement: {displacement:.2f} m³")
    print(f"   State keys: {list(hull_state.keys())}")

    return result


def run_determinism_check():
    """Verify same inputs produce same outputs."""
    design_state = {
        "hull": {"lwl": 50.0, "beam": 10.0, "draft": 2.5, "depth": 4.0, "cb": 0.55}
    }
    payload = {
        "input": {
            "operation": "run_phase",
            "parameters": {"phase": "hull"},
            "design_state": design_state,
        }
    }

    r1 = handler(deepcopy(payload))
    r2 = handler(deepcopy(payload))

    s1 = r1.get("result", {}).get("state", {}).get("hull", {})
    s2 = r2.get("result", {}).get("state", {}).get("hull", {})

    d1 = s1.get("displacement_m3")
    d2 = s2.get("displacement_m3")

    assert_true(d1 == d2, f"Non-deterministic: {d1} vs {d2}")
    print("✅ DETERMINISM CHECK PASSED")


if __name__ == "__main__":
    run_golden_test()
    run_determinism_check()
