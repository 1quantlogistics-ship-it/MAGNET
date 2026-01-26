"""
Enum deletion invariants (Phase 3).

HARD RULE: No backward compatibility for deleted form enums/priors.
These tests ensure legacy modules/classes no longer import.
"""

import pytest


def test_legacy_family_priors_module_is_gone():
    with pytest.raises(ImportError):
        __import__("magnet.kernel.priors.hull_families")


def test_kernel_priors_no_family_exports():
    import magnet.kernel.priors as priors

    assert not hasattr(priors, "HullFamily")
    assert not hasattr(priors, "FAMILY_PRIORS")
    assert not hasattr(priors, "get_family_prior")


def test_legacy_synthesis_fallback_module_is_gone():
    with pytest.raises(ImportError):
        __import__("magnet.kernel.synthesis_fallback")


def test_hull_gen_hull_type_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import HullType  # noqa: F401


def test_hull_gen_chine_type_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import ChineType  # noqa: F401


def test_hull_gen_bow_style_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import BowStyle  # noqa: F401


def test_hull_gen_stem_profile_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import StemProfile  # noqa: F401


def test_hull_gen_stern_profile_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import SternProfile  # noqa: F401


def test_hull_gen_keel_type_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import KeelType  # noqa: F401


def test_hull_gen_section_shape_enum_is_gone():
    with pytest.raises(ImportError):
        from magnet.hull_gen.enums import SectionShape  # noqa: F401

