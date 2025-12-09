"""
webgl/errors.py - Geometry error taxonomy v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Defines structured error types for geometry operations,
integrated with MAGNET's error system.

Addresses: FM5 (Weak error signaling)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("webgl.errors")


# =============================================================================
# ERROR CATEGORIES AND SEVERITY
# =============================================================================

class GeometryErrorCategory(Enum):
    """Categories of geometry errors."""
    UNAVAILABLE = "geometry_unavailable"  # Geometry not generated
    PARAMETER = "geometry_parameter"       # Invalid input parameters
    GENERATION = "geometry_generation"     # Mesh generation failed
    VALIDATION = "geometry_validation"     # Mesh validation failed
    RESOURCE = "geometry_resource"         # Resource limits exceeded
    EXPORT = "geometry_export"             # Export operation failed


class GeometryErrorSeverity(Enum):
    """Severity levels for geometry errors."""
    ERROR = "error"       # Operation failed, cannot continue
    WARNING = "warning"   # Operation succeeded with issues
    INFO = "info"         # Informational message


# =============================================================================
# BASE ERROR CLASS
# =============================================================================

class GeometryError(Exception):
    """
    Base class for geometry errors.

    Provides structured error information with:
    - Error code for programmatic handling
    - Human-readable message
    - Recovery hints for user guidance
    - Detailed context for debugging
    """

    code: str = "GEOM_000"
    category: GeometryErrorCategory = GeometryErrorCategory.GENERATION
    severity: GeometryErrorSeverity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        message: str = "",
        *,
        design_id: str = "",
        recovery_hint: str = "",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.message = message or self.__class__.__doc__ or "Geometry error"
        self.design_id = design_id
        self.recovery_hint = recovery_hint
        self.details = details or {}
        self.details.update(kwargs)

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "code": self.code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "design_id": self.design_id,
            "recovery_hint": self.recovery_hint,
            "details": self.details,
        }

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.design_id:
            parts.append(f"(design: {self.design_id})")
        if self.recovery_hint:
            parts.append(f"Hint: {self.recovery_hint}")
        return " ".join(parts)


# =============================================================================
# SPECIFIC ERROR TYPES
# =============================================================================

class GeometryUnavailableError(GeometryError):
    """Authoritative geometry not available for design."""

    code = "GEOM_001"
    category = GeometryErrorCategory.UNAVAILABLE
    severity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        design_id: str,
        reason: str = None,
        **kwargs,
    ):
        message = f"Authoritative geometry unavailable for design {design_id}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            design_id=design_id,
            recovery_hint="Run hull_form phase to generate geometry, or set allow_visual_only=True for approximation.",
            reason=reason,
            **kwargs,
        )


class GeometryParameterError(GeometryError):
    """Invalid geometry parameters."""

    code = "GEOM_002"
    category = GeometryErrorCategory.PARAMETER
    severity = GeometryErrorSeverity.WARNING

    def __init__(
        self,
        param: str,
        value: float,
        valid_range: Tuple[float, float],
        **kwargs,
    ):
        message = f"Parameter '{param}' value {value} outside valid range {valid_range}"
        super().__init__(
            message=message,
            recovery_hint=f"Adjust {param} to be within {valid_range[0]} and {valid_range[1]}.",
            param=param,
            value=value,
            valid_range=valid_range,
            **kwargs,
        )


class MeshGenerationError(GeometryError):
    """Mesh generation failed."""

    code = "GEOM_003"
    category = GeometryErrorCategory.GENERATION
    severity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        stage: str,
        reason: str,
        **kwargs,
    ):
        message = f"Mesh generation failed at {stage}: {reason}"
        super().__init__(
            message=message,
            recovery_hint="Check hull parameters for consistency. Ensure coefficients are physically valid.",
            stage=stage,
            reason=reason,
            **kwargs,
        )


class LODExceededError(GeometryError):
    """Requested LOD exceeds resource limits."""

    code = "GEOM_004"
    category = GeometryErrorCategory.RESOURCE
    severity = GeometryErrorSeverity.WARNING

    def __init__(
        self,
        requested: str,
        max_allowed: str,
        **kwargs,
    ):
        message = f"Requested LOD '{requested}' exceeds maximum '{max_allowed}' for this deployment tier"
        super().__init__(
            message=message,
            recovery_hint=f"Use '{max_allowed}' or lower LOD setting.",
            requested=requested,
            max_allowed=max_allowed,
            **kwargs,
        )


class GeometryValidationError(GeometryError):
    """Mesh validation failed."""

    code = "GEOM_005"
    category = GeometryErrorCategory.VALIDATION
    severity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        issues: List[str],
        **kwargs,
    ):
        issue_count = len(issues)
        message = f"Mesh validation failed with {issue_count} issue(s)"
        if issues:
            message += f": {issues[0]}"
            if issue_count > 1:
                message += f" (+{issue_count - 1} more)"

        super().__init__(
            message=message,
            recovery_hint="Review mesh generation parameters. Regenerate geometry with different settings.",
            issues=issues,
            issue_count=issue_count,
            **kwargs,
        )


class ExportError(GeometryError):
    """Export operation failed."""

    code = "GEOM_006"
    category = GeometryErrorCategory.EXPORT
    severity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        format: str,
        reason: str,
        **kwargs,
    ):
        message = f"Export to {format} failed: {reason}"
        super().__init__(
            message=message,
            recovery_hint=f"Try a different export format or reduce mesh complexity.",
            format=format,
            reason=reason,
            **kwargs,
        )


class SectionCutError(GeometryError):
    """Section cut operation failed."""

    code = "GEOM_007"
    category = GeometryErrorCategory.GENERATION
    severity = GeometryErrorSeverity.WARNING

    def __init__(
        self,
        plane: str,
        position: float,
        reason: str,
        **kwargs,
    ):
        message = f"Section cut at {plane}={position} failed: {reason}"
        super().__init__(
            message=message,
            recovery_hint="Verify position is within hull bounds. Try a different cutting plane.",
            plane=plane,
            position=position,
            reason=reason,
            **kwargs,
        )


class ResourceExhaustedError(GeometryError):
    """Resource limits exceeded during operation."""

    code = "GEOM_008"
    category = GeometryErrorCategory.RESOURCE
    severity = GeometryErrorSeverity.ERROR

    def __init__(
        self,
        resource: str,
        limit: Any,
        requested: Any,
        **kwargs,
    ):
        message = f"Resource '{resource}' exhausted: requested {requested}, limit {limit}"
        super().__init__(
            message=message,
            recovery_hint="Reduce mesh complexity or use lower LOD setting.",
            resource=resource,
            limit=limit,
            requested=requested,
            **kwargs,
        )


# =============================================================================
# ERROR RESPONSE HELPERS
# =============================================================================

def geometry_error_response(error: GeometryError) -> Dict[str, Any]:
    """
    Convert GeometryError to API response format.

    Returns structured error response suitable for JSON serialization.
    """
    return {
        "error": error.to_dict(),
    }


def create_error_from_dict(data: Dict[str, Any]) -> GeometryError:
    """
    Create appropriate error type from dictionary.

    Used for deserializing error responses.
    """
    code = data.get("code", "GEOM_000")
    message = data.get("message", "Unknown error")
    design_id = data.get("design_id", "")
    recovery_hint = data.get("recovery_hint", "")
    details = data.get("details", {})

    # Map code to error type
    error_types = {
        "GEOM_001": GeometryUnavailableError,
        "GEOM_002": GeometryParameterError,
        "GEOM_003": MeshGenerationError,
        "GEOM_004": LODExceededError,
        "GEOM_005": GeometryValidationError,
        "GEOM_006": ExportError,
        "GEOM_007": SectionCutError,
        "GEOM_008": ResourceExhaustedError,
    }

    error_cls = error_types.get(code, GeometryError)

    # Create error with available details
    if error_cls == GeometryUnavailableError:
        return error_cls(
            design_id=design_id,
            reason=details.get("reason"),
        )
    elif error_cls == GeometryParameterError:
        return error_cls(
            param=details.get("param", "unknown"),
            value=details.get("value", 0),
            valid_range=tuple(details.get("valid_range", (0, 1))),
        )
    elif error_cls == MeshGenerationError:
        return error_cls(
            stage=details.get("stage", "unknown"),
            reason=details.get("reason", message),
        )
    elif error_cls == LODExceededError:
        return error_cls(
            requested=details.get("requested", "unknown"),
            max_allowed=details.get("max_allowed", "unknown"),
        )
    elif error_cls == GeometryValidationError:
        return error_cls(
            issues=details.get("issues", [message]),
        )
    elif error_cls == ExportError:
        return error_cls(
            format=details.get("format", "unknown"),
            reason=details.get("reason", message),
        )
    elif error_cls == SectionCutError:
        return error_cls(
            plane=details.get("plane", "unknown"),
            position=details.get("position", 0),
            reason=details.get("reason", message),
        )
    elif error_cls == ResourceExhaustedError:
        return error_cls(
            resource=details.get("resource", "unknown"),
            limit=details.get("limit"),
            requested=details.get("requested"),
        )
    else:
        return GeometryError(
            message=message,
            design_id=design_id,
            recovery_hint=recovery_hint,
            details=details,
        )


# =============================================================================
# ERROR REGISTRY
# =============================================================================

# All geometry error codes for documentation
GEOMETRY_ERROR_CODES = {
    "GEOM_000": "Generic geometry error",
    "GEOM_001": "Authoritative geometry unavailable",
    "GEOM_002": "Invalid geometry parameter",
    "GEOM_003": "Mesh generation failed",
    "GEOM_004": "LOD exceeded resource limits",
    "GEOM_005": "Mesh validation failed",
    "GEOM_006": "Export operation failed",
    "GEOM_007": "Section cut operation failed",
    "GEOM_008": "Resource exhausted",
}
