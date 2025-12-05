"""
MAGNET V1 Semantic Validation (ALPHA)

Validates design consistency and achievability of mission requirements.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Design is invalid
    WARNING = "warning"  # Design is questionable
    INFO = "info"        # Informational note


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    category: str
    field: str
    message: str
    value: Any = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        sev = self.severity.value.upper()
        return f"[{sev}] {self.category}/{self.field}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation checks."""
    valid: bool
    issues: List[ValidationIssue]
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    info: List[ValidationIssue]

    @classmethod
    def from_issues(cls, issues: List[ValidationIssue]) -> "ValidationResult":
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in issues if i.severity == ValidationSeverity.INFO]
        return cls(
            valid=len(errors) == 0,
            issues=issues,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.info),
            "errors": [str(e) for e in self.errors],
            "warnings": [str(w) for w in self.warnings],
        }


class SemanticValidator:
    """
    Validates design for semantic consistency.

    Checks that:
    - Mission requirements are internally consistent
    - Hull parameters are achievable for mission
    - Physics results are plausible
    - Cross-references between modules are valid
    """

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def _add_issue(
        self,
        severity: ValidationSeverity,
        category: str,
        field: str,
        message: str,
        value: Any = None,
        suggestion: Optional[str] = None
    ):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            field=field,
            message=message,
            value=value,
            suggestion=suggestion
        ))

    def validate_mission(self, mission: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate mission requirements for internal consistency.

        Args:
            mission: Mission data dict

        Returns:
            List of validation issues
        """
        self.issues = []

        # Check required fields
        required_fields = ["mission_id", "range_nm", "speed_max_kts", "speed_cruise_kts"]
        for field in required_fields:
            if field not in mission or mission[field] is None:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "mission",
                    field,
                    f"Required field '{field}' is missing"
                )

        # Cruise speed should be less than max speed
        if "speed_cruise_kts" in mission and "speed_max_kts" in mission:
            if mission["speed_cruise_kts"] > mission["speed_max_kts"]:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "mission",
                    "speed_cruise_kts",
                    f"Cruise speed ({mission['speed_cruise_kts']} kts) exceeds max speed ({mission['speed_max_kts']} kts)",
                    suggestion="Reduce cruise speed or increase max speed"
                )

        # Range/endurance consistency
        if "range_nm" in mission and "speed_cruise_kts" in mission and "endurance_days" in mission:
            implied_range = mission["speed_cruise_kts"] * 24 * mission["endurance_days"]
            if implied_range < mission["range_nm"] * 0.9:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "mission",
                    "range_nm",
                    f"Range ({mission['range_nm']} nm) may not be achievable at cruise speed "
                    f"({mission['speed_cruise_kts']} kts) within endurance ({mission['endurance_days']} days). "
                    f"Implied range: {implied_range:.0f} nm",
                    suggestion="Review speed, range, or endurance requirements"
                )

        # Sea state limits
        if "sea_state_operational" in mission:
            if mission["sea_state_operational"] > 6:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "mission",
                    "sea_state_operational",
                    f"Operational sea state {mission['sea_state_operational']} is very high",
                    suggestion="Verify requirement; most vessels operate in SS 4-5"
                )

        return self.issues

    def validate_hull(self, hull: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate hull parameters for physical plausibility.

        Args:
            hull: Hull parameters dict

        Returns:
            List of validation issues
        """
        self.issues = []

        # Check required fields
        required_fields = ["length_waterline", "beam", "draft", "depth", "block_coefficient"]
        for field in required_fields:
            if field not in hull or hull[field] is None:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "hull",
                    field,
                    f"Required field '{field}' is missing"
                )
                return self.issues  # Can't continue without basic dimensions

        # LWL must be positive
        if hull["length_waterline"] <= 0:
            self._add_issue(
                ValidationSeverity.ERROR,
                "hull",
                "length_waterline",
                "Length at waterline must be positive"
            )

        # Coefficient relationships
        if all(k in hull for k in ["block_coefficient", "prismatic_coefficient", "midship_coefficient"]):
            expected_cb = hull["prismatic_coefficient"] * hull["midship_coefficient"]
            actual_cb = hull["block_coefficient"]
            error = abs(actual_cb - expected_cb) / expected_cb if expected_cb > 0 else 1.0

            if error > 0.10:  # 10% tolerance
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "hull",
                    "block_coefficient",
                    f"Cb ({actual_cb:.3f}) is inconsistent with Cp×Cm ({expected_cb:.3f}). Error: {error*100:.1f}%",
                    suggestion="Adjust coefficients for consistency: Cb = Cp × Cm"
                )
            elif error > 0.05:  # 5% tolerance
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "hull",
                    "block_coefficient",
                    f"Cb ({actual_cb:.3f}) differs from Cp×Cm ({expected_cb:.3f}) by {error*100:.1f}%"
                )

        # Draft must be less than depth
        if hull["draft"] >= hull["depth"]:
            self._add_issue(
                ValidationSeverity.ERROR,
                "hull",
                "draft",
                f"Draft ({hull['draft']} m) must be less than depth ({hull['depth']} m)"
            )

        # Freeboard check
        freeboard = hull["depth"] - hull["draft"]
        if freeboard < 0.5:
            self._add_issue(
                ValidationSeverity.WARNING,
                "hull",
                "freeboard",
                f"Freeboard ({freeboard:.2f} m) is very low",
                suggestion="Consider increasing depth or reducing draft for adequate freeboard"
            )

        return self.issues

    def validate_mission_hull_compatibility(
        self,
        mission: Dict[str, Any],
        hull: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """
        Validate that hull can achieve mission requirements.

        Args:
            mission: Mission requirements dict
            hull: Hull parameters dict

        Returns:
            List of validation issues
        """
        self.issues = []

        # Check if hull size is reasonable for payload
        if "payload_kg" in mission and "length_waterline" in hull and "beam" in hull:
            # Rough estimate: deck area available for payload
            deck_area = hull["length_waterline"] * hull["beam"] * 0.5  # 50% usable
            payload_tonnes = mission["payload_kg"] / 1000

            # Typical payload density: ~0.5-2.0 tonnes/m²
            implied_density = payload_tonnes / deck_area if deck_area > 0 else float('inf')

            if implied_density > 2.0:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "compatibility",
                    "payload",
                    f"Payload density ({implied_density:.2f} t/m²) is high for deck area ({deck_area:.0f} m²)",
                    suggestion="Consider larger vessel or reduced payload"
                )

        # Speed-displacement relationship (rough check)
        if "speed_max_kts" in mission and all(k in hull for k in ["length_waterline", "beam", "draft", "block_coefficient"]):
            displacement = hull["length_waterline"] * hull["beam"] * hull["draft"] * hull["block_coefficient"] * 1.025

            # Slenderness coefficient
            slenderness = hull["length_waterline"] / (displacement ** (1/3))

            # Fast ships need high slenderness
            if mission["speed_max_kts"] > 25 and slenderness < 6.0:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "compatibility",
                    "speed",
                    f"Hull slenderness ({slenderness:.1f}) may be too low for {mission['speed_max_kts']} kts. "
                    f"Fast ships typically need L/∇^(1/3) > 6.5",
                    suggestion="Consider longer, finer hull form"
                )

        return self.issues

    def validate_stability_results(
        self,
        stability: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """
        Validate stability calculation results.

        Args:
            stability: Stability results dict

        Returns:
            List of validation issues
        """
        self.issues = []

        # GM must be positive
        if "GM" in stability and stability["GM"] <= 0:
            self._add_issue(
                ValidationSeverity.ERROR,
                "stability",
                "GM",
                f"Metacentric height GM ({stability['GM']:.3f} m) is not positive. Vessel is unstable!",
                suggestion="Increase beam, reduce KG, or add ballast"
            )

        # IMO criteria
        if "imo_criteria_passed" in stability and not stability["imo_criteria_passed"]:
            self._add_issue(
                ValidationSeverity.ERROR,
                "stability",
                "imo_criteria",
                "Vessel does not meet IMO A.749 intact stability criteria"
            )

            # Add details for failed criteria
            if "imo_criteria_details" in stability:
                for name, details in stability["imo_criteria_details"].items():
                    if not details.get("passed", True):
                        self._add_issue(
                            ValidationSeverity.ERROR,
                            "stability",
                            f"imo_{name}",
                            f"{name}: {details['value']:.3f} {details.get('unit', '')} "
                            f"(required: {details['required']:.3f})"
                        )

        return self.issues

    def validate_all(
        self,
        mission: Optional[Dict[str, Any]] = None,
        hull: Optional[Dict[str, Any]] = None,
        stability: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Run all validation checks.

        Args:
            mission: Mission requirements dict
            hull: Hull parameters dict
            stability: Stability results dict

        Returns:
            ValidationResult with all issues
        """
        all_issues = []

        if mission:
            all_issues.extend(self.validate_mission(mission))

        if hull:
            all_issues.extend(self.validate_hull(hull))

        if mission and hull:
            all_issues.extend(self.validate_mission_hull_compatibility(mission, hull))

        if stability:
            all_issues.extend(self.validate_stability_results(stability))

        return ValidationResult.from_issues(all_issues)


def validate_design(
    mission: Optional[Dict[str, Any]] = None,
    hull: Optional[Dict[str, Any]] = None,
    stability: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Convenience function to validate a design.

    Args:
        mission: Mission requirements dict
        hull: Hull parameters dict
        stability: Stability results dict

    Returns:
        ValidationResult
    """
    validator = SemanticValidator()
    return validator.validate_all(mission, hull, stability)
