"""
tests/webgl/test_errors.py - Tests for WebGL error taxonomy v1.1

Module 58: WebGL 3D Visualization
Tests for structured error handling (FM5 resolution).
"""

import pytest


class TestGeometryError:
    """Tests for base GeometryError class."""

    def test_geometry_error_creation(self):
        """Test GeometryError creation."""
        from magnet.webgl.errors import GeometryError

        error = GeometryError(
            message="Test error",
        )

        assert "Test error" in str(error)
        assert error.code == "GEOM_000"

    def test_geometry_error_with_recovery_hint(self):
        """Test GeometryError with recovery hint."""
        from magnet.webgl.errors import GeometryError

        error = GeometryError(
            message="Something failed",
            recovery_hint="Try refreshing the page",
        )

        assert error.recovery_hint == "Try refreshing the page"

    def test_geometry_error_to_dict(self):
        """Test GeometryError serialization."""
        from magnet.webgl.errors import GeometryError

        error = GeometryError(
            message="Test",
            recovery_hint="Try again",
        )

        data = error.to_dict()

        assert data["message"] == "Test"
        assert data["code"] == "GEOM_000"
        assert data["recovery_hint"] == "Try again"


class TestGeometryUnavailableError:
    """Tests for GeometryUnavailableError (GEOM_001)."""

    def test_error_creation(self):
        """Test GeometryUnavailableError creation."""
        from magnet.webgl.errors import GeometryUnavailableError

        error = GeometryUnavailableError(
            design_id="d001",
            reason="GRM not available",
        )

        assert error.code == "GEOM_001"
        assert error.design_id == "d001"

    def test_error_default_hint(self):
        """Test default recovery hint."""
        from magnet.webgl.errors import GeometryUnavailableError

        error = GeometryUnavailableError(
            design_id="d001",
        )

        assert error.recovery_hint is not None
        assert len(error.recovery_hint) > 0


class TestGeometryParameterError:
    """Tests for GeometryParameterError (GEOM_002)."""

    def test_error_creation(self):
        """Test GeometryParameterError creation."""
        from magnet.webgl.errors import GeometryParameterError

        error = GeometryParameterError(
            param="loa",
            value=1000.0,
            valid_range=(5.0, 100.0),
        )

        assert error.code == "GEOM_002"
        assert "loa" in str(error)

    def test_error_with_valid_values(self):
        """Test error includes valid values."""
        from magnet.webgl.errors import GeometryParameterError

        error = GeometryParameterError(
            param="draft",
            value=-1.0,
            valid_range=(0.5, 5.0),
        )

        data = error.to_dict()
        assert "details" in data
        assert data["details"]["param"] == "draft"


class TestMeshGenerationError:
    """Tests for MeshGenerationError (GEOM_003)."""

    def test_error_creation(self):
        """Test MeshGenerationError creation."""
        from magnet.webgl.errors import MeshGenerationError

        error = MeshGenerationError(
            stage="tessellation",
            reason="Invalid section count",
        )

        assert error.code == "GEOM_003"
        assert "tessellation" in str(error)

    def test_error_with_details(self):
        """Test error with additional details."""
        from magnet.webgl.errors import MeshGenerationError

        error = MeshGenerationError(
            stage="hull_generation",
            reason="invalid params",
            vertex_count=0,
        )

        data = error.to_dict()
        assert "details" in data
        assert data["details"]["stage"] == "hull_generation"


class TestLODExceededError:
    """Tests for LODExceededError (GEOM_004)."""

    def test_error_creation(self):
        """Test LODExceededError creation."""
        from magnet.webgl.errors import LODExceededError

        error = LODExceededError(
            requested="ultra",
            max_allowed="high",
        )

        assert error.code == "GEOM_004"
        assert "ultra" in str(error)

    def test_error_includes_limits(self):
        """Test error includes resource limits."""
        from magnet.webgl.errors import LODExceededError

        error = LODExceededError(
            requested="ultra",
            max_allowed="medium",
        )

        data = error.to_dict()
        assert data["details"]["requested"] == "ultra"
        assert data["details"]["max_allowed"] == "medium"


class TestExportError:
    """Tests for ExportError (GEOM_006)."""

    def test_error_creation(self):
        """Test ExportError creation."""
        from magnet.webgl.errors import ExportError

        error = ExportError(
            format="fbx",
            reason="Unsupported format",
        )

        assert error.code == "GEOM_006"
        assert "fbx" in str(error)

    def test_error_with_details(self):
        """Test error with export details."""
        from magnet.webgl.errors import ExportError

        error = ExportError(
            format="glb",
            reason="Buffer overflow",
            buffer_size=0,
        )

        data = error.to_dict()
        assert "details" in data


class TestSectionCutError:
    """Tests for SectionCutError (GEOM_007)."""

    def test_error_creation(self):
        """Test SectionCutError creation."""
        from magnet.webgl.errors import SectionCutError

        error = SectionCutError(
            plane="transverse",
            position=15.0,
            reason="Position outside bounds",
        )

        assert error.code == "GEOM_007"
        assert "transverse" in str(error)
        assert "15" in str(error)


class TestGeometryErrorResponse:
    """Tests for geometry_error_response helper."""

    def test_error_response_basic(self):
        """Test geometry_error_response helper."""
        from magnet.webgl.errors import GeometryError, geometry_error_response

        error = GeometryError(
            message="Test error",
        )

        response = geometry_error_response(error)

        assert "error" in response
        assert response["error"]["code"] == "GEOM_000"

    def test_error_response_includes_hint(self):
        """Test error response includes recovery hint."""
        from magnet.webgl.errors import GeometryUnavailableError, geometry_error_response

        error = GeometryUnavailableError(
            design_id="d001",
        )

        response = geometry_error_response(error)

        assert "error" in response
        assert response["error"]["recovery_hint"] is not None


class TestErrorCodes:
    """Tests for error code constants."""

    def test_all_codes_unique(self):
        """Test all error codes are unique."""
        from magnet.webgl.errors import (
            GeometryUnavailableError,
            GeometryParameterError,
            MeshGenerationError,
            LODExceededError,
            GeometryValidationError,
            ExportError,
            SectionCutError,
            ResourceExhaustedError,
        )

        errors = [
            GeometryUnavailableError("d"),
            GeometryParameterError("p", 0, (0, 1)),
            MeshGenerationError("s", "r"),
            LODExceededError("l", "m"),
            GeometryValidationError(["issue"]),
            ExportError("f", "r"),
            SectionCutError("p", 0, "r"),
            ResourceExhaustedError("r", 100, 200),
        ]

        codes = [e.code for e in errors]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"

    def test_codes_follow_pattern(self):
        """Test error codes follow GEOM_XXX pattern."""
        from magnet.webgl.errors import (
            GeometryUnavailableError,
            GeometryParameterError,
            MeshGenerationError,
            LODExceededError,
        )

        errors = [
            GeometryUnavailableError("d"),
            GeometryParameterError("p", 0, (0, 1)),
            MeshGenerationError("s", "r"),
            LODExceededError("l", "m"),
        ]

        for error in errors:
            assert error.code.startswith("GEOM_")
            assert len(error.code) == 8  # GEOM_XXX


class TestErrorInheritance:
    """Tests for error class inheritance."""

    def test_all_inherit_from_geometry_error(self):
        """Test all errors inherit from GeometryError."""
        from magnet.webgl.errors import (
            GeometryError,
            GeometryUnavailableError,
            GeometryParameterError,
            MeshGenerationError,
            LODExceededError,
            GeometryValidationError,
            ExportError,
            SectionCutError,
            ResourceExhaustedError,
        )

        error_classes = [
            GeometryUnavailableError,
            GeometryParameterError,
            MeshGenerationError,
            LODExceededError,
            GeometryValidationError,
            ExportError,
            SectionCutError,
            ResourceExhaustedError,
        ]

        for cls in error_classes:
            assert issubclass(cls, GeometryError)
            assert issubclass(cls, Exception)

    def test_errors_catchable_as_base(self):
        """Test errors can be caught as GeometryError."""
        from magnet.webgl.errors import (
            GeometryError,
            GeometryUnavailableError,
        )

        try:
            raise GeometryUnavailableError("d001")
        except GeometryError as e:
            assert e.code == "GEOM_001"
        except Exception:
            pytest.fail("Should have been caught as GeometryError")
