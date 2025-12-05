"""
MAGNET V1 Hull Form Constraints (ALPHA)

Physics-informed constraints to prevent absurd designs.
These constraints encode naval architecture wisdom to ensure
generated designs are physically plausible.

Reference: magnetarc_design_sanity_safeguards.md
"""

from dataclasses import dataclass
from typing import Tuple, List, Optional
from enum import Enum

# Import schema with fallback for standalone testing
try:
    from schemas.hull_params import HullParamsSchema, HullType
except ImportError:
    HullParamsSchema = None  # type: ignore
    HullType = None  # type: ignore


class ConstraintSeverity(str, Enum):
    """Severity level for constraint violations."""
    ERROR = "error"      # Hard failure - design is impossible
    WARNING = "warning"  # Soft failure - design is questionable
    INFO = "info"        # Informational - outside typical range


@dataclass
class ConstraintResult:
    """Result of a constraint check."""
    valid: bool
    constraint_name: str
    message: str
    value: float
    limit: Tuple[Optional[float], Optional[float]]  # (min, max)
    severity: ConstraintSeverity = ConstraintSeverity.ERROR

    def __str__(self) -> str:
        status = "PASS" if self.valid else "FAIL"
        return f"[{status}] {self.constraint_name}: {self.message}"


class HullFormConstraints:
    """
    Physics-informed constraints to prevent absurd hull designs.

    These constraints are based on:
    - Naval architecture best practices
    - Physical limits from hydrodynamics
    - Practical shipbuilding constraints
    - Historical data from successful vessels

    Goal: Prevent AI from generating "rectangle hulls" and other absurdities.
    """

    # Constraint limits based on naval architecture practice
    # Format: (min, max) - None means unbounded
    LIMITS = {
        # Dimensional ratios
        'length_beam_ratio': (3.5, 11.0),      # L/B - stability & seakeeping
        'beam_draft_ratio': (2.0, 6.0),        # B/T - stability
        'depth_draft_ratio': (1.2, 3.0),       # D/T - freeboard/strength
        'length_depth_ratio': (8.0, 18.0),     # L/D - structural strength

        # Form coefficients
        'block_coefficient': (0.35, 0.85),     # Cb - fullness
        'prismatic_coefficient': (0.55, 0.80), # Cp - longitudinal distribution
        'midship_coefficient': (0.75, 0.99),   # Cm - midship fullness
        'waterplane_coefficient': (0.65, 0.90),# Cwp - waterplane fullness

        # Speed-related (Froude number limits by hull type)
        'slenderness_coefficient_displacement': (4.0, 6.5),  # L/∇^(1/3) for slow vessels
        'slenderness_coefficient_fast': (5.5, 8.5),          # L/∇^(1/3) for fast vessels

        # Entrance/run geometry
        'entrance_angle_deg': (5.0, 30.0),     # Half angle of entrance
        'run_length_ratio': (0.15, 0.40),      # Run length / LWL

        # LCB position (fraction from AP)
        'lcb_position': (0.48, 0.56),          # Typical range

        # Catamaran-specific
        'hull_spacing_beam_ratio': (1.2, 2.5), # Spacing / demihull beam
    }

    # Type-specific limit overrides
    TYPE_LIMITS = {
        'planing': {
            'block_coefficient': (0.35, 0.55),
            'length_beam_ratio': (2.5, 5.0),
            'slenderness_coefficient': (3.0, 5.0),
        },
        'displacement': {
            'block_coefficient': (0.60, 0.85),
            'length_beam_ratio': (5.0, 10.0),
        },
        'semi_displacement': {
            'block_coefficient': (0.40, 0.65),
            'length_beam_ratio': (4.0, 8.0),
        },
        'catamaran': {
            'length_beam_ratio': (8.0, 15.0),  # Per demihull
            'beam_draft_ratio': (1.5, 4.0),    # Per demihull
        }
    }

    def __init__(self, strict: bool = True):
        """
        Initialize constraints.

        Args:
            strict: If True, use ERROR severity for violations.
                    If False, use WARNING for soft limits.
        """
        self.strict = strict

    def _check_range(
        self,
        value: float,
        limit: Tuple[Optional[float], Optional[float]],
        name: str,
        unit: str = ""
    ) -> ConstraintResult:
        """Check if value is within range."""
        min_val, max_val = limit
        in_range = True

        if min_val is not None and value < min_val:
            in_range = False
        if max_val is not None and value > max_val:
            in_range = False

        unit_str = f" {unit}" if unit else ""
        message = f"{value:.3f}{unit_str} (range: {min_val}-{max_val})"

        return ConstraintResult(
            valid=in_range,
            constraint_name=name,
            message=message,
            value=value,
            limit=limit,
            severity=ConstraintSeverity.ERROR if self.strict else ConstraintSeverity.WARNING
        )

    def validate_hull(
        self,
        hull: "HullParamsSchema",
        hull_type_override: Optional[str] = None
    ) -> List[ConstraintResult]:
        """
        Validate hull parameters against physics-informed constraints.

        Args:
            hull: HullParamsSchema instance
            hull_type_override: Override hull type for limit selection

        Returns:
            List of ConstraintResult objects
        """
        results = []

        # Determine hull type for type-specific limits
        hull_type = hull_type_override or (hull.hull_type.value if hull.hull_type else None)
        type_limits = self.TYPE_LIMITS.get(hull_type, {})

        # Merge type-specific limits with defaults
        def get_limit(name: str) -> Tuple[Optional[float], Optional[float]]:
            return type_limits.get(name, self.LIMITS.get(name, (None, None)))

        # === Dimensional Ratios ===

        # Length/Beam ratio
        lb_ratio = hull.length_beam_ratio
        results.append(self._check_range(
            lb_ratio,
            get_limit('length_beam_ratio'),
            'length_beam_ratio',
            'L/B'
        ))

        # Beam/Draft ratio
        bt_ratio = hull.beam_draft_ratio
        results.append(self._check_range(
            bt_ratio,
            get_limit('beam_draft_ratio'),
            'beam_draft_ratio',
            'B/T'
        ))

        # Depth/Draft ratio
        dt_ratio = hull.depth_draft_ratio
        results.append(self._check_range(
            dt_ratio,
            get_limit('depth_draft_ratio'),
            'depth_draft_ratio',
            'D/T'
        ))

        # Length/Depth ratio
        ld_ratio = hull.length_waterline / hull.depth
        results.append(self._check_range(
            ld_ratio,
            get_limit('length_depth_ratio'),
            'length_depth_ratio',
            'L/D'
        ))

        # === Form Coefficients ===

        results.append(self._check_range(
            hull.block_coefficient,
            get_limit('block_coefficient'),
            'block_coefficient',
            'Cb'
        ))

        results.append(self._check_range(
            hull.prismatic_coefficient,
            get_limit('prismatic_coefficient'),
            'prismatic_coefficient',
            'Cp'
        ))

        results.append(self._check_range(
            hull.midship_coefficient,
            get_limit('midship_coefficient'),
            'midship_coefficient',
            'Cm'
        ))

        results.append(self._check_range(
            hull.waterplane_coefficient,
            get_limit('waterplane_coefficient'),
            'waterplane_coefficient',
            'Cwp'
        ))

        # === Coefficient Consistency ===

        # Cb should approximately equal Cp × Cm
        expected_cb = hull.prismatic_coefficient * hull.midship_coefficient
        cb_error = abs(hull.block_coefficient - expected_cb) / expected_cb
        results.append(ConstraintResult(
            valid=cb_error < 0.05,  # 5% tolerance
            constraint_name='coefficient_consistency',
            message=f'Cb={hull.block_coefficient:.3f}, expected Cp×Cm={expected_cb:.3f} (error: {cb_error*100:.1f}%)',
            value=cb_error,
            limit=(0, 0.05),
            severity=ConstraintSeverity.WARNING
        ))

        # === Slenderness ===

        slenderness = hull.slenderness_coefficient
        slenderness_limit = get_limit('slenderness_coefficient_fast') if hull_type in ['planing', 'semi_displacement'] else get_limit('slenderness_coefficient_displacement')
        results.append(self._check_range(
            slenderness,
            slenderness_limit,
            'slenderness_coefficient',
            'L/∇^(1/3)'
        ))

        # === LCB Position ===

        results.append(self._check_range(
            hull.lcb_position,
            get_limit('lcb_position'),
            'lcb_position',
            'fraction from AP'
        ))

        # === Catamaran-specific ===

        if hull_type == 'catamaran' and hull.hull_spacing and hull.demihull_beam:
            spacing_ratio = hull.hull_spacing / hull.demihull_beam
            results.append(self._check_range(
                spacing_ratio,
                get_limit('hull_spacing_beam_ratio'),
                'hull_spacing_beam_ratio',
                'S/B_demihull'
            ))

        return results

    def is_valid(self, hull: "HullParamsSchema") -> bool:
        """
        Quick check if hull passes all ERROR-level constraints.

        Args:
            hull: HullParamsSchema instance

        Returns:
            True if all ERROR constraints pass
        """
        results = self.validate_hull(hull)
        return all(
            r.valid for r in results
            if r.severity == ConstraintSeverity.ERROR
        )

    def get_violations(
        self,
        hull: "HullParamsSchema",
        include_warnings: bool = False
    ) -> List[ConstraintResult]:
        """
        Get list of constraint violations.

        Args:
            hull: HullParamsSchema instance
            include_warnings: Include WARNING-level violations

        Returns:
            List of failed ConstraintResult objects
        """
        results = self.validate_hull(hull)
        violations = [r for r in results if not r.valid]

        if not include_warnings:
            violations = [
                r for r in violations
                if r.severity == ConstraintSeverity.ERROR
            ]

        return violations

    def validate_with_report(self, hull: "HullParamsSchema") -> str:
        """
        Generate human-readable validation report.

        Args:
            hull: HullParamsSchema instance

        Returns:
            Formatted report string
        """
        results = self.validate_hull(hull)

        lines = ["Hull Form Constraint Validation Report", "=" * 40, ""]

        # Group by pass/fail
        passed = [r for r in results if r.valid]
        failed = [r for r in results if not r.valid]

        if failed:
            lines.append("VIOLATIONS:")
            for r in failed:
                lines.append(f"  ✗ {r}")
            lines.append("")

        lines.append(f"PASSED ({len(passed)}/{len(results)}):")
        for r in passed:
            lines.append(f"  ✓ {r.constraint_name}: {r.value:.3f}")

        lines.append("")
        lines.append(f"Overall: {'VALID' if not failed else 'INVALID'}")

        return "\n".join(lines)
