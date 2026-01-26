"""
T8.4: North Star Alignment Tests (invariants).

These are lightweight "shape" invariants that protect the core architectural
principles:
- enum-driven hull-form synthesis must not come back
- numerical solvers must remain domain-agnostic (no domain imports)
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_coordinate_executor_is_domain_agnostic_by_import_boundary():
    import magnet.kernel.coordinate_executor as mod

    txt = _read_text(Path(mod.__file__))
    forbidden = (
        "magnet.hull_gen",
        "magnet.physics",
        "magnet.stability",
        "magnet.structural",
        "HullFamily",
        "HullType",
        "StemProfile",
        "SternProfile",
        "KeelType",
        "SectionShape",
    )
    for token in forbidden:
        assert token not in txt, f"Forbidden token found in coordinate executor: {token}"


def test_synthesis_constraints_does_not_reference_deleted_hull_enums():
    import magnet.kernel.synthesis_constraints as mod

    txt = _read_text(Path(mod.__file__))
    forbidden = (
        "HullFamily",
        "StemProfile",
        "SternProfile",
        "KeelType",
        "SectionShape",
    )
    for token in forbidden:
        assert token not in txt, f"Forbidden token found in synthesis constraints: {token}"


def test_bow_config_has_no_style_field():
    from magnet.hull_gen.parameters import BowConfig

    cfg = BowConfig()
    assert not hasattr(cfg, "style")


def test_hull_gen_enums_module_is_gone():
    with pytest.raises(ImportError):
        __import__("magnet.hull_gen.enums")

