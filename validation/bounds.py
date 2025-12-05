"""
MAGNET V1 Bounds Validation (ALPHA)

Domain-specific boundary checking for design parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional


@dataclass
class BoundDefinition:
    """Definition of a parameter bound."""
    min_value: Optional[float]
    max_value: Optional[float]
    unit: str
    description: str
    severity: str = "error"  # error, warning, info


# Bounds definitions for different parameter types
MISSION_BOUNDS: Dict[str, BoundDefinition] = {
    "range_nm": BoundDefinition(100, 20000, "nm", "Operational range"),
    "speed_max_kts": BoundDefinition(5, 60, "kts", "Maximum speed"),
    "speed_cruise_kts": BoundDefinition(5, 40, "kts", "Cruise speed"),
    "endurance_days": BoundDefinition(1, 180, "days", "Endurance at sea"),
    "payload_kg": BoundDefinition(0, 500000, "kg", "Payload capacity"),
    "sea_state_operational": BoundDefinition(1, 9, "", "Operational sea state"),
    "sea_state_survival": BoundDefinition(1, 9, "", "Survival sea state"),
    "autonomy_level": BoundDefinition(0, 5, "", "Autonomy level (0=crewed)"),
}

HULL_BOUNDS: Dict[str, BoundDefinition] = {
    "length_overall": BoundDefinition(10, 500, "m", "Length overall"),
    "length_waterline": BoundDefinition(10, 500, "m", "Length at waterline"),
    "beam": BoundDefinition(2, 100, "m", "Beam"),
    "draft": BoundDefinition(0.5, 30, "m", "Design draft"),
    "depth": BoundDefinition(1, 50, "m", "Molded depth"),
    "freeboard": BoundDefinition(0.5, 20, "m", "Freeboard"),
    "block_coefficient": BoundDefinition(0.30, 0.90, "", "Block coefficient Cb"),
    "prismatic_coefficient": BoundDefinition(0.50, 0.85, "", "Prismatic coefficient Cp"),
    "midship_coefficient": BoundDefinition(0.70, 1.00, "", "Midship coefficient Cm"),
    "waterplane_coefficient": BoundDefinition(0.60, 0.95, "", "Waterplane coefficient Cwp"),
    "lcb_position": BoundDefinition(0.45, 0.58, "", "LCB position (fraction from AP)"),
}

RATIO_BOUNDS: Dict[str, BoundDefinition] = {
    "length_beam_ratio": BoundDefinition(3.5, 11.0, "", "Length/Beam ratio"),
    "beam_draft_ratio": BoundDefinition(2.0, 6.0, "", "Beam/Draft ratio"),
    "depth_draft_ratio": BoundDefinition(1.2, 3.0, "", "Depth/Draft ratio"),
    "slenderness_coefficient": BoundDefinition(4.0, 8.5, "", "Slenderness L/∇^(1/3)"),
}

STABILITY_BOUNDS: Dict[str, BoundDefinition] = {
    "GM": BoundDefinition(0.15, 10.0, "m", "Metacentric height"),
    "KB": BoundDefinition(0.1, 20.0, "m", "Center of buoyancy height"),
    "BM": BoundDefinition(0.1, 50.0, "m", "Metacentric radius"),
    "max_gz": BoundDefinition(0.20, 5.0, "m", "Maximum righting arm"),
    "angle_max_gz": BoundDefinition(25, 90, "°", "Angle at maximum GZ"),
    "range_positive_stability": BoundDefinition(40, 180, "°", "Range of positive stability"),
}

RESISTANCE_BOUNDS: Dict[str, BoundDefinition] = {
    "froude_number": BoundDefinition(0, 0.50, "", "Froude number"),
    "Cf": BoundDefinition(0.001, 0.01, "", "Frictional resistance coefficient"),
    "Ct": BoundDefinition(0.002, 0.05, "", "Total resistance coefficient"),
}


@dataclass
class BoundsCheckResult:
    """Result of a bounds check."""
    field: str
    value: float
    in_bounds: bool
    bounds: Tuple[Optional[float], Optional[float]]
    unit: str
    message: str
    severity: str


class BoundsValidator:
    """
    Validates that design parameters are within acceptable bounds.

    Unlike semantic validation which checks consistency,
    bounds validation checks that individual values are
    within physically plausible ranges.
    """

    def __init__(self):
        self.results: List[BoundsCheckResult] = []

    def _check_bound(
        self,
        field: str,
        value: Any,
        bound: BoundDefinition
    ) -> BoundsCheckResult:
        """Check a single value against its bounds."""
        if value is None:
            return BoundsCheckResult(
                field=field,
                value=0,
                in_bounds=False,
                bounds=(bound.min_value, bound.max_value),
                unit=bound.unit,
                message=f"Value is None",
                severity="error"
            )

        in_bounds = True
        message = ""

        if bound.min_value is not None and value < bound.min_value:
            in_bounds = False
            message = f"{value} {bound.unit} is below minimum {bound.min_value} {bound.unit}"
        elif bound.max_value is not None and value > bound.max_value:
            in_bounds = False
            message = f"{value} {bound.unit} is above maximum {bound.max_value} {bound.unit}"
        else:
            message = f"{value} {bound.unit} is within bounds"

        return BoundsCheckResult(
            field=field,
            value=value,
            in_bounds=in_bounds,
            bounds=(bound.min_value, bound.max_value),
            unit=bound.unit,
            message=message,
            severity=bound.severity if not in_bounds else "ok"
        )

    def check_mission_bounds(self, mission: Dict[str, Any]) -> List[BoundsCheckResult]:
        """Check mission parameters against bounds."""
        self.results = []

        for field, bound in MISSION_BOUNDS.items():
            if field in mission:
                result = self._check_bound(field, mission[field], bound)
                self.results.append(result)

        return self.results

    def check_hull_bounds(self, hull: Dict[str, Any]) -> List[BoundsCheckResult]:
        """Check hull parameters against bounds."""
        self.results = []

        for field, bound in HULL_BOUNDS.items():
            if field in hull:
                result = self._check_bound(field, hull[field], bound)
                self.results.append(result)

        # Check computed ratios
        if "length_waterline" in hull and "beam" in hull:
            ratio = hull["length_waterline"] / hull["beam"]
            result = self._check_bound("length_beam_ratio", ratio, RATIO_BOUNDS["length_beam_ratio"])
            self.results.append(result)

        if "beam" in hull and "draft" in hull:
            ratio = hull["beam"] / hull["draft"]
            result = self._check_bound("beam_draft_ratio", ratio, RATIO_BOUNDS["beam_draft_ratio"])
            self.results.append(result)

        if "depth" in hull and "draft" in hull:
            ratio = hull["depth"] / hull["draft"]
            result = self._check_bound("depth_draft_ratio", ratio, RATIO_BOUNDS["depth_draft_ratio"])
            self.results.append(result)

        return self.results

    def check_stability_bounds(self, stability: Dict[str, Any]) -> List[BoundsCheckResult]:
        """Check stability results against bounds."""
        self.results = []

        for field, bound in STABILITY_BOUNDS.items():
            if field in stability:
                result = self._check_bound(field, stability[field], bound)
                self.results.append(result)

        return self.results

    def check_resistance_bounds(self, resistance: Dict[str, Any]) -> List[BoundsCheckResult]:
        """Check resistance results against bounds."""
        self.results = []

        for field, bound in RESISTANCE_BOUNDS.items():
            if field in resistance:
                result = self._check_bound(field, resistance[field], bound)
                self.results.append(result)

        return self.results

    def check_all(
        self,
        mission: Optional[Dict[str, Any]] = None,
        hull: Optional[Dict[str, Any]] = None,
        stability: Optional[Dict[str, Any]] = None,
        resistance: Optional[Dict[str, Any]] = None
    ) -> List[BoundsCheckResult]:
        """Check all available data against bounds."""
        all_results = []

        if mission:
            all_results.extend(self.check_mission_bounds(mission))
        if hull:
            all_results.extend(self.check_hull_bounds(hull))
        if stability:
            all_results.extend(self.check_stability_bounds(stability))
        if resistance:
            all_results.extend(self.check_resistance_bounds(resistance))

        return all_results

    def get_violations(self) -> List[BoundsCheckResult]:
        """Get only the bounds violations."""
        return [r for r in self.results if not r.in_bounds]

    def is_valid(self) -> bool:
        """Check if all bounds are satisfied (no errors)."""
        return all(
            r.in_bounds or r.severity != "error"
            for r in self.results
        )


def check_bounds(
    mission: Optional[Dict[str, Any]] = None,
    hull: Optional[Dict[str, Any]] = None,
    stability: Optional[Dict[str, Any]] = None,
    resistance: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[BoundsCheckResult]]:
    """
    Convenience function to check all bounds.

    Args:
        mission: Mission data
        hull: Hull parameters
        stability: Stability results
        resistance: Resistance results

    Returns:
        Tuple of (all_valid, results)
    """
    validator = BoundsValidator()
    results = validator.check_all(mission, hull, stability, resistance)
    return validator.is_valid(), results
