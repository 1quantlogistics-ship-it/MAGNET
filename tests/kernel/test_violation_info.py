"""
Emergency stabilization tests for structured violation info.

Task IDs:
- E0.2 (Emergency: Make violations non-opaque)
- T5.7 (Fix Opaque Violations)
"""

from __future__ import annotations

from magnet.kernel.geometry_observables import (
    measure_section_metric_deadrise_deg_at_chine,
    measure_section_metric_max_half_beam_m,
)


def test_measurement_failure_has_structured_violation():
    # Degenerate: all points have same y => dy to chine is zero => cannot compute deadrise.
    section = {"points": [[0.0, -1.0], [0.0, -0.5], [0.0, 0.0]]}
    m = measure_section_metric_deadrise_deg_at_chine(section)

    assert m is not None
    assert hasattr(m, "is_valid")
    assert not m.is_valid
    assert m.value is None
    assert m.violation is not None
    assert m.violation.violation_type in ("numerical", "topological", "geometric", "physical")
    assert "deadrise" in m.violation.message or "dy" in m.violation.message


def test_max_half_beam_no_points_returns_violation():
    section = {"points": []}
    m = measure_section_metric_max_half_beam_m(section)

    assert m is not None
    assert not m.is_valid
    assert m.value is None
    assert m.violation is not None
    assert m.violation.violation_type == "topological"
