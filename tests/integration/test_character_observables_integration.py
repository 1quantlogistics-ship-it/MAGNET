"""
Integration test for character observables implementation.

Tests:
1. Feature curve extraction from compiled geometry
2. Observable measurements from geometry
3. Shape document generation
4. API endpoint availability
"""

import pytest
from typing import Dict, Any


def test_feature_curve_extraction():
    """Test that feature curves are extracted during compilation."""
    from magnet.kernel.stdlib.compiler import compile_to_geometry
    from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D
    
    # Create a minimal valid state with 3 sections
    state = {
        "design_id": "test_feature_curves",
        "design_version": 1,
        "hull": {"loa": 20.0, "beam": 5.0, "draft": 1.5},
        "resources": {
            "body1": {
                "_type": "geometry.body",
                "body_type": "hull",
                "offset_y_m": 0.0,
            },
            "sec1": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.0,
                "points": [[0.0, 0.0], [2.5, 0.5], [2.5, 2.0], [0.0, 2.5]],
            },
            "sec2": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.5,
                "points": [[0.0, 0.0], [2.5, 0.3], [2.5, 2.2], [0.0, 2.7]],
            },
            "sec3": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 1.0,
                "points": [[0.0, 0.0], [1.0, 0.3], [1.0, 1.5], [0.0, 2.0]],
            },
            "surf1": {
                "_type": "geometry.surface",
                "surface_definition": "panelized",
                "section_ids": ["sec1", "sec2", "sec3"],
            },
        },
    }
    
    geometry = compile_to_geometry(state)
    
    # Check that feature curves are populated
    assert hasattr(geometry, "stem_profile"), "stem_profile not extracted"
    assert hasattr(geometry, "transom_outline"), "transom_outline not extracted"
    assert hasattr(geometry, "deck_edge"), "deck_edge (sheer_line) not extracted"
    assert hasattr(geometry, "chine_curve"), "chine_curve not extracted"
    assert hasattr(geometry, "keel_profile"), "keel_profile not extracted"
    
    # Check metadata mirror
    assert "feature_curves" in geometry.metadata, "feature_curves not in metadata"
    feature_curves = geometry.metadata["feature_curves"]
    assert "stem_profile" in feature_curves
    assert "transom_outline" in feature_curves
    assert "sheer_line" in feature_curves
    assert "chine_line" in feature_curves
    assert "keel_line" in feature_curves
    
    # Validate keel_line has expected number of points (3 sections)
    assert len(geometry.keel_profile) == 3, f"Expected 3 keel points, got {len(geometry.keel_profile)}"


def test_observable_measurements():
    """Test that observables can be measured from geometry."""
    from magnet.kernel.stdlib.compiler import compile_to_geometry
    from magnet.kernel import geometry_observables as obs_module
    
    # Create a simple hull
    state = {
        "design_id": "test_observables",
        "design_version": 1,
        "hull": {"loa": 20.0, "beam": 5.0, "draft": 1.5},
        "resources": {
            "body1": {"_type": "geometry.body", "body_type": "hull", "offset_y_m": 0.0},
            "sec1": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.0,
                "points": [[0.0, 0.0], [2.5, 0.5], [2.5, 2.0], [0.0, 2.5]],
            },
            "sec2": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.5,
                "points": [[0.0, 0.0], [2.5, 0.3], [2.5, 2.5], [0.0, 3.0]],
            },
            "sec3": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 1.0,
                "points": [[0.0, 0.0], [1.5, 0.3], [1.5, 2.0], [0.0, 2.5]],
            },
            "surf1": {
                "_type": "geometry.surface",
                "surface_definition": "panelized",
                "section_ids": ["sec1", "sec2", "sec3"],
            },
        },
    }
    
    geometry = compile_to_geometry(state)
    
    # Test a few key measurements
    sheer_peak = obs_module.measure_longitudinal_metric_sheer_peak_station(geometry)
    assert sheer_peak is not None, "sheer_peak_station measurement failed"
    assert 0.0 <= sheer_peak.value <= 1.0, f"sheer_peak_station out of range: {sheer_peak.value}"
    
    transom_rake = obs_module.measure_profile_metric_transom_rake_deg(geometry)
    # transom_rake may be None if transom_outline too simple, which is OK
    if transom_rake is not None:
        assert 0.0 <= transom_rake.value <= 90.0, f"transom_rake_deg out of range: {transom_rake.value}"
    
    transom_beam_ratio = obs_module.measure_profile_metric_transom_beam_ratio(geometry)
    assert transom_beam_ratio is not None, "transom_beam_ratio measurement failed"
    assert 0.0 <= transom_beam_ratio.value <= 1.0, f"transom_beam_ratio out of range: {transom_beam_ratio.value}"


def test_shape_document_generation():
    """Test that shape document generates correctly."""
    from magnet.kernel.stdlib.compiler import compile_to_geometry
    from magnet.kernel.shape_document import generate_shape_document
    
    state = {
        "design_id": "test_shape_doc",
        "design_version": 1,
        "hull": {"loa": 20.0, "beam": 5.0, "draft": 1.5, "hull_type": "sportfisher"},
        "resources": {
            "body1": {"_type": "geometry.body", "body_type": "hull", "offset_y_m": 0.0},
            "sec1": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.0,
                "points": [[0.0, 0.0], [2.5, 0.5], [2.5, 2.0], [0.0, 2.5]],
            },
            "sec2": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 0.5,
                "points": [[0.0, 0.0], [2.5, 0.3], [2.5, 2.5], [0.0, 3.0]],
            },
            "sec3": {
                "_type": "geometry.section",
                "body_id": "body1",
                "station": 1.0,
                "points": [[0.0, 0.0], [1.5, 0.3], [1.5, 2.0], [0.0, 2.5]],
            },
            "surf1": {
                "_type": "geometry.surface",
                "surface_definition": "panelized",
                "section_ids": ["sec1", "sec2", "sec3"],
            },
        },
    }
    
    geometry = compile_to_geometry(state)
    
    # Generate shape document with viking target profile
    shape_doc = generate_shape_document(
        state=state,
        geometry=geometry,
        target_profile_id="viking_sportfisher",
    )
    
    # Validate structure
    assert shape_doc.schema_version == "1.0.0"
    assert shape_doc.hull_identity["hull_id"] == "test_shape_doc"
    assert shape_doc.principal_dimensions["loa_m"] == 20.0
    
    # Check observable snapshot is populated
    assert len(shape_doc.observable_snapshot) > 0, "Observable snapshot is empty"
    
    # Check target profile is present
    assert shape_doc.target_profile is not None
    assert shape_doc.target_profile["profile_id"] == "viking_sportfisher"
    
    # Check comparisons are generated
    assert len(shape_doc.comparison) > 0, "No comparisons generated"

    # Check suggested adjustments include kernel-computed deltas + expected_effect (when off-target)
    # We expect at least one suggestion to exist for this intentionally imperfect geometry.
    assert isinstance(shape_doc.suggested_adjustments, list)
    assert len(shape_doc.suggested_adjustments) > 0, "No suggested adjustments generated"
    any_with_effect = any(
        (getattr(a, "delta", None) is not None)
        and isinstance(getattr(a, "expected_effect", ""), str)
        and len(getattr(a, "expected_effect", "")) > 0
        for a in shape_doc.suggested_adjustments
    )
    assert any_with_effect, "Expected at least one suggested adjustment with expected_effect"
    
    # Check token estimate is reasonable
    token_est = shape_doc.token_estimate()
    assert 500 < token_est < 3000, f"Token estimate out of expected range: {token_est}"
    
    # Validate JSON serialization
    shape_dict = shape_doc.to_dict()
    assert isinstance(shape_dict, dict)
    shape_json = shape_doc.to_json()
    assert isinstance(shape_json, str)
    assert len(shape_json) > 100


def test_target_profiles_registry():
    """Test that target profiles are available."""
    from magnet.kernel.shape_document import (
        list_target_profiles,
        get_target_profile,
        infer_profile_from_vessel_type,
    )
    
    # Check registry
    profiles = list_target_profiles()
    assert len(profiles) > 0, "No target profiles defined"
    assert "viking_sportfisher" in profiles
    assert "displacement_trawler" in profiles
    
    # Check profile retrieval
    viking = get_target_profile("viking_sportfisher")
    assert viking is not None
    assert "targets" in viking
    assert "longitudinal_metric:sheer_peak_station" in viking["targets"]
    
    # Check inference
    inferred = infer_profile_from_vessel_type("sportfisher")
    assert inferred == "viking_sportfisher"
    
    inferred = infer_profile_from_vessel_type("trawler")
    assert inferred == "displacement_trawler"


def test_observable_registry_completeness():
    """Test that all character observables are registered."""
    from magnet.kernel.geometry_observables import OBSERVABLE_REGISTRY, get_observable_spec
    
    # Character observables from plan
    character_observables = [
        "longitudinal_metric:sheer_peak_station",
        "longitudinal_metric:sheer_curvature_peak_station",
        "profile_metric:stem_rake_deg",
        "profile_metric:stem_concavity_ratio",
        "longitudinal_metric:entry_half_angle_deg",
        "longitudinal_metric:bow_fineness_ratio",
        "profile_metric:transom_rake_deg",
        "profile_metric:transom_beam_ratio",
        "longitudinal_metric:chine_rise_rate",
        "section_metric:chine_height_ratio",
        "longitudinal_metric:deadrise_progression_shape",
        "longitudinal_metric:rocker_profile_curvature",
    ]
    
    for obs_id in character_observables:
        spec = get_observable_spec(obs_id)
        assert spec is not None, f"Observable {obs_id} not registered"
        assert spec.observable_id == obs_id
        assert spec.measurable is True
        assert spec.unit != "", f"Observable {obs_id} has no unit"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
