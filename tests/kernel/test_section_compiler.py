"""
Tests for section compiler transform reporting.

TASK-006: Verify that all section resampling is reported explicitly.
"""

import pytest
from magnet.kernel.stdlib.section_compiler import (
    compile_section,
    TransformReport,
)


class TestTransformReporting:
    """TASK-006: Transform reports eliminate silent transforms."""
    
    def test_compile_section_returns_transform_report(self):
        """compile_section with return_transform_report=True returns tuple."""
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[0, 0], [1, 1], [1.5, 2], [2, 3]],
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        assert isinstance(report, TransformReport)
        assert report.original_points == 4
        assert report.resampled_points >= report.original_points  # May upsample
    
    def test_low_res_section_upsampled_with_default_rule(self):
        """Sections with < 32 points get upsampled, rule='default_32'."""
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[0, 0], [1, 1], [2, 2]],  # Only 3 points
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        assert report.original_points == 3
        assert report.resampled_points > 3
        assert report.rule == "default_32"
    
    def test_explicit_resample_uses_explicit_rule(self):
        """When resample_points is explicitly set, rule='explicit'."""
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[0, 0], [1, 1], [2, 2]],
            "resample_points": 20,
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        assert report.original_points == 3
        assert report.resampled_points == 20
        assert report.rule == "explicit"
    
    def test_high_res_section_not_resampled(self):
        """Sections with >= 32 points are not resampled, rule='none'."""
        # Create 40 points
        points = [[i * 0.1, i * 0.2] for i in range(40)]
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": points,
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        assert report.original_points == 40
        assert report.resampled_points == 40
        assert report.rule == "none"
    
    def test_reversed_order_reported(self):
        """When points are reversed (deck->keel to keel->deck), it's reported."""
        # Points in deck->keel order (z decreasing)
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[2, 3], [1.5, 2], [1, 1], [0, 0]],  # Deck to keel
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        assert report.reversed_order is True
    
    def test_hard_edges_snapped_reported(self):
        """Hard edge z-values that were snapped during resampling are reported."""
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[0, 0], [1, 1], [2, 2]],
            "edge_types": ["smooth", "hard", "smooth"],
        }
        
        section, report = compile_section(resource, loa=20.0, return_transform_report=True)
        
        # The hard edge at z=1 should be in the snapped list
        assert len(report.hard_edges_snapped) >= 1
        assert 1.0 in report.hard_edges_snapped
    
    def test_transform_report_to_dict(self):
        """TransformReport.to_dict() produces valid dict."""
        report = TransformReport(
            original_points=5,
            resampled_points=32,
            rule="default_32",
            hard_edges_snapped=[1.0, 2.0],
            reversed_order=True,
        )
        
        d = report.to_dict()
        
        assert d["original_points"] == 5
        assert d["resampled_points"] == 32
        assert d["rule"] == "default_32"
        assert d["hard_edges_snapped"] == [1.0, 2.0]
        assert d["reversed_order"] is True
    
    def test_section_has_transform_report_attribute(self):
        """Compiled section has transform_report attribute."""
        resource = {
            "_type": "geometry.section",
            "station": 0.5,
            "points": [[0, 0], [1, 1], [2, 2]],
        }
        
        section = compile_section(resource, loa=20.0)
        
        assert hasattr(section, "transform_report")
        assert isinstance(section.transform_report, dict)
        assert "original_points" in section.transform_report
        assert "rule" in section.transform_report


class TestGrepVerification:
    """Verify acceptance criteria from TASK-006."""
    
    def test_transform_report_exists_in_module(self):
        """grep 'transform_report' should find matches in section_compiler."""
        import magnet.kernel.stdlib.section_compiler as sc
        
        # Check that TransformReport class exists
        assert hasattr(sc, "TransformReport")
        
        # Check that compile_section mentions transform_report
        import inspect
        source = inspect.getsource(sc.compile_section)
        assert "transform_report" in source.lower()
