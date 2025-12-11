"""
validation.py - Interior layout validation schema v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Defines validation rules and constraints for interior arrangements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Callable
from enum import Enum
import logging

from magnet.interior.schema.space import SpaceType, SpaceCategory, SpaceDefinition

__all__ = [
    'ValidationSeverity',
    'ValidationIssue',
    'ValidationResult',
    'LayoutConstraint',
    'SpaceConstraint',
    'MARITIME_CONSTRAINTS',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"           # Must be fixed - violates regulations
    WARNING = "warning"       # Should be fixed - best practice
    INFO = "info"             # Advisory - suggestion
    CRITICAL = "critical"     # Blocking - cannot proceed


# =============================================================================
# VALIDATION ISSUE
# =============================================================================

@dataclass
class ValidationIssue:
    """
    A single validation issue found in the layout.

    Attributes:
        issue_id: Unique identifier
        severity: Severity level
        category: Category of issue (safety, regulatory, structural, etc.)
        message: Human-readable description
        space_id: Affected space (if applicable)
        deck_id: Affected deck (if applicable)
        regulation_ref: Reference to applicable regulation
        auto_fixable: Whether this can be automatically fixed
        fix_suggestion: Suggested fix
    """

    issue_id: str
    severity: ValidationSeverity
    category: str
    message: str

    # Context
    space_id: Optional[str] = None
    deck_id: Optional[str] = None
    zone_id: Optional[str] = None
    location: Optional[str] = None

    # Regulatory
    regulation_ref: Optional[str] = None

    # Fix info
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "space_id": self.space_id,
            "deck_id": self.deck_id,
            "zone_id": self.zone_id,
            "location": self.location,
            "regulation_ref": self.regulation_ref,
            "auto_fixable": self.auto_fixable,
            "fix_suggestion": self.fix_suggestion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
        """Deserialize from dictionary."""
        return cls(
            issue_id=data["issue_id"],
            severity=ValidationSeverity(data["severity"]),
            category=data["category"],
            message=data["message"],
            space_id=data.get("space_id"),
            deck_id=data.get("deck_id"),
            zone_id=data.get("zone_id"),
            location=data.get("location"),
            regulation_ref=data.get("regulation_ref"),
            auto_fixable=data.get("auto_fixable", False),
            fix_suggestion=data.get("fix_suggestion"),
        )


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """
    Result of validating an interior layout.

    Attributes:
        is_valid: Whether layout passes validation
        issues: List of validation issues
        errors_count: Number of errors
        warnings_count: Number of warnings
        checked_rules: Rules that were checked
    """

    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)

    # Statistics
    errors_count: int = 0
    warnings_count: int = 0
    info_count: int = 0
    critical_count: int = 0

    # Metadata
    checked_rules: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update counts."""
        self.issues.append(issue)

        if issue.severity == ValidationSeverity.ERROR:
            self.errors_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings_count += 1
        elif issue.severity == ValidationSeverity.INFO:
            self.info_count += 1
        elif issue.severity == ValidationSeverity.CRITICAL:
            self.critical_count += 1
            self.is_valid = False

    def add_error(
        self,
        issue_id: str,
        category: str,
        message: str,
        **kwargs
    ) -> None:
        """Convenience method to add an error."""
        self.add_issue(ValidationIssue(
            issue_id=issue_id,
            severity=ValidationSeverity.ERROR,
            category=category,
            message=message,
            **kwargs
        ))

    def add_warning(
        self,
        issue_id: str,
        category: str,
        message: str,
        **kwargs
    ) -> None:
        """Convenience method to add a warning."""
        self.add_issue(ValidationIssue(
            issue_id=issue_id,
            severity=ValidationSeverity.WARNING,
            category=category,
            message=message,
            **kwargs
        ))

    def add_info(
        self,
        issue_id: str,
        category: str,
        message: str,
        **kwargs
    ) -> None:
        """Convenience method to add info."""
        self.add_issue(ValidationIssue(
            issue_id=issue_id,
            severity=ValidationSeverity.INFO,
            category=category,
            message=message,
            **kwargs
        ))

    def get_issues_by_severity(
        self,
        severity: ValidationSeverity
    ) -> List[ValidationIssue]:
        """Get issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]

    def get_issues_for_space(self, space_id: str) -> List[ValidationIssue]:
        """Get all issues for a specific space."""
        return [i for i in self.issues if i.space_id == space_id]

    def get_fixable_issues(self) -> List[ValidationIssue]:
        """Get issues that can be auto-fixed."""
        return [i for i in self.issues if i.auto_fixable]

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        for issue in other.issues:
            self.add_issue(issue)
        self.checked_rules.extend(other.checked_rules)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "errors_count": self.errors_count,
            "warnings_count": self.warnings_count,
            "info_count": self.info_count,
            "critical_count": self.critical_count,
            "checked_rules": self.checked_rules,
            "validation_time_ms": self.validation_time_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """Deserialize from dictionary."""
        result = cls(
            is_valid=data["is_valid"],
            errors_count=data.get("errors_count", 0),
            warnings_count=data.get("warnings_count", 0),
            info_count=data.get("info_count", 0),
            critical_count=data.get("critical_count", 0),
            checked_rules=data.get("checked_rules", []),
            validation_time_ms=data.get("validation_time_ms", 0.0),
        )
        for idata in data.get("issues", []):
            result.issues.append(ValidationIssue.from_dict(idata))
        return result


# =============================================================================
# SPACE CONSTRAINT
# =============================================================================

@dataclass
class SpaceConstraint:
    """
    Constraint that applies to a specific space type.

    Attributes:
        constraint_id: Unique identifier
        space_types: Space types this applies to
        min_area: Minimum area (m²)
        max_area: Maximum area (m²)
        min_height: Minimum height (m)
        max_occupancy_per_m2: Maximum people per m²
        required_adjacent: Space types that must be adjacent
        prohibited_adjacent: Space types that cannot be adjacent
        requires_ventilation: Whether ventilation is required
        requires_natural_light: Whether natural light is required
    """

    constraint_id: str
    space_types: Set[SpaceType]

    # Area constraints
    min_area: float = 0.0
    max_area: float = float('inf')
    min_height: float = 0.0

    # Occupancy
    max_occupancy_per_m2: float = 0.0

    # Adjacency
    required_adjacent: Set[SpaceType] = field(default_factory=set)
    prohibited_adjacent: Set[SpaceType] = field(default_factory=set)

    # Requirements
    requires_ventilation: bool = False
    requires_natural_light: bool = False
    requires_emergency_exit: bool = False

    # Regulatory
    regulation_ref: str = ""
    description: str = ""

    def applies_to(self, space_type: SpaceType) -> bool:
        """Check if constraint applies to a space type."""
        return space_type in self.space_types

    def validate_space(self, space: SpaceDefinition) -> List[ValidationIssue]:
        """Validate a space against this constraint."""
        issues = []

        if not self.applies_to(space.space_type):
            return issues

        # Check area
        if space.area < self.min_area:
            issues.append(ValidationIssue(
                issue_id=f"{self.constraint_id}_min_area",
                severity=ValidationSeverity.ERROR,
                category="area",
                message=f"Space {space.name} area ({space.area:.1f}m²) below minimum ({self.min_area:.1f}m²)",
                space_id=space.space_id,
                regulation_ref=self.regulation_ref,
                fix_suggestion=f"Increase space area to at least {self.min_area}m²",
            ))

        if space.area > self.max_area:
            issues.append(ValidationIssue(
                issue_id=f"{self.constraint_id}_max_area",
                severity=ValidationSeverity.WARNING,
                category="area",
                message=f"Space {space.name} area ({space.area:.1f}m²) exceeds recommended maximum ({self.max_area:.1f}m²)",
                space_id=space.space_id,
            ))

        # Check height
        if space.height < self.min_height:
            issues.append(ValidationIssue(
                issue_id=f"{self.constraint_id}_min_height",
                severity=ValidationSeverity.ERROR,
                category="height",
                message=f"Space {space.name} height ({space.height:.2f}m) below minimum ({self.min_height:.2f}m)",
                space_id=space.space_id,
                regulation_ref=self.regulation_ref,
            ))

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "constraint_id": self.constraint_id,
            "space_types": [st.value for st in self.space_types],
            "min_area": self.min_area,
            "max_area": self.max_area if self.max_area != float('inf') else None,
            "min_height": self.min_height,
            "max_occupancy_per_m2": self.max_occupancy_per_m2,
            "required_adjacent": [st.value for st in self.required_adjacent],
            "prohibited_adjacent": [st.value for st in self.prohibited_adjacent],
            "requires_ventilation": self.requires_ventilation,
            "requires_natural_light": self.requires_natural_light,
            "requires_emergency_exit": self.requires_emergency_exit,
            "regulation_ref": self.regulation_ref,
            "description": self.description,
        }


# =============================================================================
# LAYOUT CONSTRAINT
# =============================================================================

@dataclass
class LayoutConstraint:
    """
    Constraint that applies to the overall layout.

    Attributes:
        constraint_id: Unique identifier
        description: Human-readable description
        regulation_ref: Reference to applicable regulation
        validator: Function to validate layout
    """

    constraint_id: str
    description: str
    regulation_ref: str = ""
    category: str = "general"

    # Validator function signature: (layout) -> List[ValidationIssue]
    validator: Optional[Callable] = None

    def validate(self, layout: Any) -> List[ValidationIssue]:
        """Run validation on layout."""
        if self.validator:
            return self.validator(layout)
        return []


# =============================================================================
# MARITIME CONSTRAINTS
# =============================================================================

# Standard maritime constraints based on SOLAS and class rules
MARITIME_CONSTRAINTS: Dict[str, SpaceConstraint] = {
    # Accommodation constraints
    "cabin_crew_min": SpaceConstraint(
        constraint_id="cabin_crew_min",
        space_types={SpaceType.CABIN_CREW},
        min_area=4.5,
        min_height=2.1,
        requires_ventilation=True,
        regulation_ref="ILO MLC 2006",
        description="Minimum crew cabin requirements",
    ),
    "cabin_officer_min": SpaceConstraint(
        constraint_id="cabin_officer_min",
        space_types={SpaceType.CABIN_OFFICER},
        min_area=7.5,
        min_height=2.1,
        requires_ventilation=True,
        regulation_ref="ILO MLC 2006",
        description="Minimum officer cabin requirements",
    ),
    "mess_crew": SpaceConstraint(
        constraint_id="mess_crew",
        space_types={SpaceType.MESS_CREW},
        min_area=15.0,
        min_height=2.3,
        max_occupancy_per_m2=1.0,
        regulation_ref="ILO MLC 2006",
        description="Crew mess room requirements",
    ),
    "hospital": SpaceConstraint(
        constraint_id="hospital",
        space_types={SpaceType.HOSPITAL},
        min_area=12.0,
        min_height=2.3,
        requires_ventilation=True,
        requires_natural_light=True,
        regulation_ref="ILO MLC 2006",
        description="Ship hospital requirements",
    ),

    # Control space constraints
    "bridge": SpaceConstraint(
        constraint_id="bridge",
        space_types={SpaceType.BRIDGE},
        min_area=25.0,
        min_height=2.5,
        requires_natural_light=True,
        regulation_ref="SOLAS V",
        description="Navigation bridge requirements",
    ),

    # Machinery constraints
    "engine_room": SpaceConstraint(
        constraint_id="engine_room",
        space_types={SpaceType.ENGINE_ROOM},
        min_height=4.0,
        requires_ventilation=True,
        requires_emergency_exit=True,
        regulation_ref="SOLAS II-1",
        description="Engine room requirements",
    ),
    "switchboard_room": SpaceConstraint(
        constraint_id="switchboard_room",
        space_types={SpaceType.SWITCHBOARD_ROOM},
        min_area=12.0,
        min_height=2.5,
        prohibited_adjacent={SpaceType.FUEL_TANK, SpaceType.CARGO_TANK},
        regulation_ref="IEC 60092",
        description="Electrical switchboard room requirements",
    ),

    # Circulation constraints
    "corridor": SpaceConstraint(
        constraint_id="corridor",
        space_types={SpaceType.CORRIDOR},
        min_height=2.1,
        regulation_ref="SOLAS II-2",
        description="Corridor minimum height",
    ),
    "stairway": SpaceConstraint(
        constraint_id="stairway",
        space_types={SpaceType.STAIRWAY},
        min_area=2.5,
        min_height=2.1,
        regulation_ref="SOLAS II-2",
        description="Stairway requirements",
    ),

    # Service constraints
    "galley": SpaceConstraint(
        constraint_id="galley",
        space_types={SpaceType.GALLEY},
        min_area=15.0,
        min_height=2.3,
        requires_ventilation=True,
        prohibited_adjacent={SpaceType.SEWAGE_TREATMENT, SpaceType.TOILET},
        regulation_ref="ILO MLC 2006",
        description="Galley requirements",
    ),

    # Safety constraints
    "battery_room": SpaceConstraint(
        constraint_id="battery_room",
        space_types={SpaceType.BATTERY_ROOM},
        min_height=2.3,
        requires_ventilation=True,
        prohibited_adjacent={SpaceType.CABIN_CREW, SpaceType.CABIN_OFFICER, SpaceType.GALLEY},
        regulation_ref="Class Rules",
        description="Battery room ventilation and separation",
    ),
    "paint_locker": SpaceConstraint(
        constraint_id="paint_locker",
        space_types={SpaceType.PAINT_LOCKER},
        requires_ventilation=True,
        prohibited_adjacent={SpaceType.CABIN_CREW, SpaceType.CABIN_OFFICER, SpaceType.ENGINE_ROOM},
        regulation_ref="SOLAS II-2",
        description="Paint locker requirements",
    ),
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_space_constraints(
    spaces: List[SpaceDefinition],
    constraints: Dict[str, SpaceConstraint] = None,
) -> ValidationResult:
    """
    Validate spaces against constraints.

    Args:
        spaces: List of spaces to validate
        constraints: Constraints to check (defaults to MARITIME_CONSTRAINTS)

    Returns:
        ValidationResult with any issues found
    """
    if constraints is None:
        constraints = MARITIME_CONSTRAINTS

    result = ValidationResult()

    for space in spaces:
        for constraint in constraints.values():
            if constraint.applies_to(space.space_type):
                issues = constraint.validate_space(space)
                for issue in issues:
                    result.add_issue(issue)
                result.checked_rules.append(constraint.constraint_id)

    return result


def validate_adjacency(
    spaces: List[SpaceDefinition],
    constraints: Dict[str, SpaceConstraint] = None,
) -> ValidationResult:
    """
    Validate space adjacency rules.

    Args:
        spaces: List of spaces to validate
        constraints: Constraints to check (defaults to MARITIME_CONSTRAINTS)

    Returns:
        ValidationResult with any adjacency issues
    """
    if constraints is None:
        constraints = MARITIME_CONSTRAINTS

    result = ValidationResult()
    space_map = {s.space_id: s for s in spaces}

    for space in spaces:
        constraint = None
        for c in constraints.values():
            if c.applies_to(space.space_type):
                constraint = c
                break

        if not constraint:
            continue

        # Check prohibited adjacencies
        for adjacent_id in space.connected_spaces:
            adjacent = space_map.get(adjacent_id)
            if adjacent and adjacent.space_type in constraint.prohibited_adjacent:
                result.add_error(
                    issue_id=f"adjacency_{space.space_id}_{adjacent_id}",
                    category="adjacency",
                    message=f"Space {space.name} ({space.space_type.value}) cannot be adjacent to {adjacent.name} ({adjacent.space_type.value})",
                    space_id=space.space_id,
                    regulation_ref=constraint.regulation_ref,
                )

    return result
