"""
Shape Document Generation for Hull Character Observables.

Generates a compact, token-efficient representation of hull state that enables
the model to critique and fix hulls without spatial reasoning from raw coordinates.

Pre-computes:
- Observable snapshot (all measured character observables)
- Comparison to targets (if provided)
- Critique hints (domain-aware analysis)
- Suggested adjustments (pre-computed ADJUST statements)

Architecture:
- Observable measurements are kernel truth (no duplication)
- Shape document is a derived view for model consumption
- Targets come from named profiles or custom user specs
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Comparison:
    """Comparison of current value to target for a single observable."""
    current: float
    target: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]
    status: str  # "met" | "close" | "off" | "no_target"
    controllable: bool


@dataclass
class SuggestedAdjustment:
    """Pre-computed ADJUST/TARGET statement suggestion."""
    observable_id: str
    scope: Dict[str, Any]
    operation: str  # "ADJUST" | "TARGET"
    delta: Optional[float]
    value: Optional[float]
    unit: str
    rationale: str
    expected_effect: str = ""


# ---------------------------------------------------------------------------
# Kernel-computed sensitivities + convergence tolerances
# ---------------------------------------------------------------------------

# observable_id: (control_knob, sensitivity, unit_desc)
# sensitivity = observable_delta / control_delta
CONTROL_SENSITIVITIES: Dict[str, Tuple[str, float, str]] = {
    "longitudinal_metric:entry_half_angle_deg": ("section_metric:max_half_beam_m", 12.0, "deg/m"),
    "profile_metric:transom_beam_ratio": ("section_metric:max_half_beam_m", 0.15, "ratio/m"),
    "longitudinal_metric:sheer_peak_station": ("section_metric:sheer_z_m", 0.1, "station/m"),
    "longitudinal_metric:deadrise_progression_shape": ("section_metric:deadrise_deg_at_chine", 0.05, "warp/deg"),
}


# Convergence contract (stop suggesting when within tolerance)
OBSERVABLE_TOLERANCES: Dict[str, float] = {
    "longitudinal_metric:entry_half_angle_deg": 1.0,  # deg
    "profile_metric:transom_beam_ratio": 0.02,  # ratio
    "longitudinal_metric:sheer_peak_station": 0.03,  # station (0..1)
}


def is_target_satisfied(observable_id: str, current: float, target: float) -> bool:
    tolerance = float(OBSERVABLE_TOLERANCES.get(observable_id, 0.05))
    return abs(float(current) - float(target)) <= tolerance


def compute_suggested_delta(
    *,
    observable_id: str,
    current_value: float,
    target_value: float,
    max_delta: float,
) -> Tuple[float, str]:
    """
    Compute control delta from sensitivity table.
    Returns (delta, expected_effect_str).
    """
    if observable_id not in CONTROL_SENSITIVITIES:
        return (0.0, "unknown")

    _control_knob, sensitivity, _unit_desc = CONTROL_SENSITIVITIES[observable_id]
    sensitivity = float(sensitivity) if float(sensitivity) != 0.0 else 1.0

    observable_delta = float(target_value) - float(current_value)
    control_delta = observable_delta / sensitivity

    # Clamp to knob max delta
    max_delta = float(max_delta or 0.0)
    if max_delta > 0:
        control_delta = max(-max_delta, min(max_delta, control_delta))

    expected_change = control_delta * sensitivity
    sign = "+" if expected_change > 0 else ""
    expected_effect = f"{sign}{expected_change:.1f}"
    return (float(control_delta), expected_effect)


@dataclass
class ShapeDocument:
    """
    Compact shape analysis for model consumption.
    
    Token budget target: ~1200-1400 tokens for typical hulls.
    """
    schema_version: str = "1.0.0"
    generated_at: str = ""
    
    hull_identity: Dict[str, Any] = field(default_factory=dict)
    principal_dimensions: Dict[str, float] = field(default_factory=dict)
    observable_snapshot: Dict[str, float] = field(default_factory=dict)
    target_profile: Optional[Dict[str, Any]] = None
    comparison: Dict[str, Comparison] = field(default_factory=dict)
    critique_hints: List[str] = field(default_factory=list)
    suggested_adjustments: List[SuggestedAdjustment] = field(default_factory=list)
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        # Convert Comparison objects
        d["comparison"] = {
            k: asdict(v) if isinstance(v, Comparison) else v
            for k, v in self.comparison.items()
        }
        d["suggested_adjustments"] = [
            asdict(a) if isinstance(a, SuggestedAdjustment) else a
            for a in self.suggested_adjustments
        ]
        return d
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def token_estimate(self) -> int:
        """Estimate token count (rough: 4 chars per token)."""
        return len(self.to_json(indent=None)) // 4


# ---------------------------------------------------------------------------
# Main Generation Function
# ---------------------------------------------------------------------------

def generate_shape_document(
    state: Dict[str, Any],
    geometry: Any,
    target_profile: Optional[Dict[str, Any]] = None,
    target_profile_id: Optional[str] = None,
) -> ShapeDocument:
    """
    Generate a Shape Document from current state and geometry.
    
    Args:
        state: Current design state dict
        geometry: Compiled HullGeometry object
        target_profile: Explicit target values dict, or None
        target_profile_id: Named profile ID to load targets from
    
    Returns:
        ShapeDocument with all fields populated
    """
    doc = ShapeDocument()
    doc.generated_at = datetime.now(timezone.utc).isoformat()
    
    # 1. Hull identity
    doc.hull_identity = _extract_hull_identity(state)
    
    # 2. Principal dimensions
    doc.principal_dimensions = _extract_principal_dimensions(state)
    
    # 3. Observable snapshot (measure all)
    doc.observable_snapshot = _measure_all_observables(geometry, state)
    
    # 4. Target profile
    if target_profile_id:
        target_profile = get_target_profile(target_profile_id)
    if target_profile:
        doc.target_profile = {
            "profile_id": target_profile.get("profile_id", "custom"),
            "source": target_profile.get("source", "explicit"),
            "targets": target_profile.get("targets", {}),
        }
    
    # 5. Comparison (if targets exist)
    if doc.target_profile:
        doc.comparison = _compute_comparisons(
            doc.observable_snapshot,
            doc.target_profile["targets"],
        )
    
    # 6. Critique hints
    doc.critique_hints = _generate_critique_hints(doc.comparison)
    
    # 7. Suggested adjustments
    doc.suggested_adjustments = _generate_suggested_adjustments(doc.comparison)
    
    # 8. Quality summary
    doc.quality_summary = _compute_quality_summary(doc.comparison)
    
    return doc


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _extract_hull_identity(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract basic hull identity info."""
    return {
        "hull_id": str(state.get("design_id", "")),
        "design_version": int(state.get("design_version", 1)),
        "body_count": 1,  # TODO: extract from geometry if multi-body
    }


def _extract_principal_dimensions(state: Dict[str, Any]) -> Dict[str, float]:
    """Extract principal dimensions from state."""
    hull = state.get("hull", {})
    return {
        "loa_m": float(hull.get("loa", 0)),
        "lwl_m": float(hull.get("lwl", 0)),
        "beam_m": float(hull.get("beam", 0)),
        "draft_m": float(hull.get("draft", 0)),
        "depth_m": float(hull.get("depth", 0)),
    }


def _measure_all_observables(geometry: Any, state: Dict[str, Any]) -> Dict[str, float]:
    """
    Measure all character observables from geometry.
    
    Only includes successfully measured values (omits None).
    """
    from magnet.kernel import geometry_observables as obs_module
    
    snapshot = {}
    
    # Try each character observable measurement
    measurers = {
        "longitudinal_metric:sheer_peak_station": obs_module.measure_longitudinal_metric_sheer_peak_station,
        "longitudinal_metric:sheer_curvature_peak_station": obs_module.measure_longitudinal_metric_sheer_curvature_peak_station,
        "profile_metric:stem_rake_deg": obs_module.measure_profile_metric_stem_rake_deg,
        "profile_metric:stem_concavity_ratio": obs_module.measure_profile_metric_stem_concavity_ratio,
        "longitudinal_metric:entry_half_angle_deg": obs_module.measure_longitudinal_metric_entry_half_angle_deg,
        "longitudinal_metric:bow_fineness_ratio": obs_module.measure_longitudinal_metric_bow_fineness_ratio,
        "profile_metric:transom_rake_deg": obs_module.measure_profile_metric_transom_rake_deg,
        "profile_metric:transom_beam_ratio": obs_module.measure_profile_metric_transom_beam_ratio,
        "longitudinal_metric:chine_rise_rate": obs_module.measure_longitudinal_metric_chine_rise_rate,
        "longitudinal_metric:deadrise_progression_shape": obs_module.measure_longitudinal_metric_deadrise_progression_shape,
        "longitudinal_metric:rocker_profile_curvature": obs_module.measure_longitudinal_metric_rocker_profile_curvature,
    }
    
    for obs_id, measurer in measurers.items():
        try:
            result = measurer(geometry)
            if result is None:
                continue

            # Prefer Measurement protocol with explicit validity
            if hasattr(result, "is_valid"):
                if not bool(result.is_valid):
                    continue
                value = getattr(result, "value", None)
            else:
                # Back-compat: measurer returned a raw numeric value
                value = result

            if value is not None and isinstance(value, (int, float)):
                snapshot[obs_id] = float(value)
        except Exception as e:
            # Silently skip unmeasurable observables
            pass
    
    return snapshot


def _compute_comparisons(
    snapshot: Dict[str, float],
    targets: Dict[str, float],
) -> Dict[str, Comparison]:
    """Compute comparison for each target."""
    from magnet.kernel.geometry_observables import get_observable_spec
    
    comparisons = {}
    
    for obs_id, target_val in targets.items():
        current_val = snapshot.get(obs_id)
        if current_val is None:
            # Target exists but current value not measured - skip
            continue
        
        delta = target_val - current_val
        delta_pct = (delta / abs(current_val) * 100) if current_val != 0 else 0
        
        # Determine status based on tolerance
        spec = get_observable_spec(obs_id)
        tolerance = spec.tolerance if spec else 0.05
        
        if abs(delta) <= tolerance:
            status = "met"
        elif abs(delta) <= tolerance * 3:
            status = "close"
        else:
            status = "off"
        
        controllable = spec.controllable if spec else False
        
        comparisons[obs_id] = Comparison(
            current=round(current_val, 3),
            target=round(target_val, 3),
            delta=round(delta, 3),
            delta_pct=round(delta_pct, 1),
            status=status,
            controllable=controllable,
        )
    
    return comparisons


# ---------------------------------------------------------------------------
# Critique Templates
# ---------------------------------------------------------------------------

CRITIQUE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "longitudinal_metric:sheer_peak_station": {
        "too_high": "Sheer peaks too far forward ({current:.2f} vs {target:.2f} target) — lacks teardrop character",
        "too_low": "Sheer peaks too far aft ({current:.2f} vs {target:.2f} target) — unusual profile",
    },
    "longitudinal_metric:entry_half_angle_deg": {
        "too_high": "Entry too blunt ({current:.1f}° vs {target:.1f}° target) — will pound in chop",
        "too_low": "Entry too fine ({current:.1f}° vs {target:.1f}° target) — may lack reserve buoyancy",
    },
    "profile_metric:transom_beam_ratio": {
        "too_low": "Transom too narrow ({current:.2f} vs {target:.2f} target) — reduced planing stability",
        "too_high": "Transom too wide ({current:.2f} vs {target:.2f} target) — unusual stern shape",
    },
    "profile_metric:stem_rake_deg": {
        "too_low": "Stem rake too vertical ({current:.1f}° vs {target:.1f}° target) — less seakindly",
        "too_high": "Stem rake too laid back ({current:.1f}° vs {target:.1f}° target) — may lose reserve buoyancy",
    },
    "longitudinal_metric:chine_rise_rate": {
        "too_low": "Chine rise too shallow ({current:.3f} vs {target:.3f} target) — less bow lift",
        "too_high": "Chine rise too steep ({current:.3f} vs {target:.3f} target) — unusual flare progression",
    },
}


def _generate_critique_hints(comparisons: Dict[str, Comparison]) -> List[str]:
    """Generate domain-aware critique hints from comparisons."""
    hints: List[str] = []
    
    # Sort by absolute delta (biggest misses first)
    sorted_comps = sorted(
        [(k, v) for k, v in comparisons.items() if v.status == "off"],
        key=lambda x: abs(x[1].delta or 0),
        reverse=True,
    )
    
    for obs_id, comp in sorted_comps[:5]:  # Top 5 issues
        templates = CRITIQUE_TEMPLATES.get(obs_id)
        if not templates:
            continue
        
        direction = "too_high" if (comp.delta or 0) < 0 else "too_low"
        template = templates.get(direction)
        if not template:
            continue
        
        hint = template.format(
            current=comp.current,
            target=comp.target,
        )
        hints.append(hint)
    
    return hints


# ---------------------------------------------------------------------------
# Adjustment Mappings
# ---------------------------------------------------------------------------

ADJUSTMENT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "longitudinal_metric:sheer_peak_station": {
        "controllable_via": "section_metric:sheer_z_m",
        "scope_strategy": "mid_forward",
        "rationale_template": "Raise sheer in mid-forward region to shift peak {direction}",
    },
    "longitudinal_metric:entry_half_angle_deg": {
        "controllable_via": "section_metric:max_half_beam_m",
        "scope_strategy": "forward",
        "rationale_template": "{action} forward beam to {action2} entry",
    },
    "profile_metric:transom_beam_ratio": {
        "controllable_via": "section_metric:max_half_beam_m",
        "scope_strategy": "aft",
        "rationale_template": "{action} aft beam to {action2} transom width",
    },
    "longitudinal_metric:chine_rise_rate": {
        "controllable_via": "section_metric:sheer_z_m",
        "scope_strategy": "forward",
        "rationale_template": "Adjust chine height in forward sections",
    },
}


SCOPE_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "forward": {"station_range": [0.85, 1.0]},
    "mid_forward": {"station_range": [0.6, 0.8]},
    "aft": {"station_range": [0.0, 0.15]},
    "midship": {"station_range": [0.4, 0.6]},
    "full": {},
}


def _generate_suggested_adjustments(
    comparisons: Dict[str, Comparison],
) -> List[SuggestedAdjustment]:
    """Generate suggested ADJUST/TARGET statements from comparisons."""
    from magnet.kernel.geometry_observables import get_observable_spec
    
    suggestions = []
    
    # Sort by absolute delta (biggest misses first)
    sorted_comps = sorted(
        [(k, v) for k, v in comparisons.items() if v.status == "off"],
        key=lambda x: abs(x[1].delta or 0),
        reverse=True,
    )
    
    for obs_id, comp in sorted_comps[:5]:  # Top 5
        spec = get_observable_spec(obs_id)
        # Stop condition: if target is satisfied, do not suggest changes
        try:
            if comp.target is not None and is_target_satisfied(obs_id, comp.current, comp.target):
                continue
        except Exception:
            pass
        
        # If directly controllable, suggest direct adjustment
        if spec and spec.controllable:
            suggestions.append(SuggestedAdjustment(
                observable_id=obs_id,
                scope={},
                operation="ADJUST",
                delta=comp.delta,
                value=None,
                unit=spec.unit,
                rationale=f"Direct adjustment to reach target",
                expected_effect="",
            ))
            continue
        
        # Otherwise, use mapping to controllable alternative
        mapping = ADJUSTMENT_MAPPINGS.get(obs_id)
        if not mapping:
            continue
        
        ctrl_obs = mapping["controllable_via"]
        ctrl_spec = get_observable_spec(ctrl_obs)
        if not ctrl_spec:
            continue
        
        scope = SCOPE_STRATEGIES.get(mapping["scope_strategy"], {})

        # Compute delta from sensitivity table (kernel does the math)
        ctrl_delta = 0.0
        expected_effect = "unknown"
        try:
            if comp.target is not None:
                ctrl_delta, expected_effect = compute_suggested_delta(
                    observable_id=obs_id,
                    current_value=float(comp.current),
                    target_value=float(comp.target),
                    max_delta=float(ctrl_spec.max_delta or 0.0),
                )
        except Exception:
            ctrl_delta = 0.0
            expected_effect = "unknown"
        
        # Generate rationale
        direction = "aft" if (comp.delta or 0) > 0 else "forward"
        action = "Increase" if (ctrl_delta or 0) > 0 else "Decrease"
        action2 = "widen" if (ctrl_delta or 0) > 0 else "narrow"
        
        rationale = mapping["rationale_template"].format(
            direction=direction,
            action=action,
            action2=action2,
        )
        
        suggestions.append(SuggestedAdjustment(
            observable_id=ctrl_obs,
            scope=scope,
            operation="ADJUST",
            delta=round(ctrl_delta, 2) if ctrl_delta else None,
            value=None,
            unit=ctrl_spec.unit,
            rationale=rationale,
            expected_effect=expected_effect,
        ))
    
    return suggestions[:5]  # Cap at 5


def _compute_quality_summary(comparisons: Dict[str, Comparison]) -> Dict[str, Any]:
    """Compute aggregate quality metrics."""
    if not comparisons:
        return {}
    
    targets_defined = len(comparisons)
    targets_met = sum(1 for c in comparisons.values() if c.status == "met")
    targets_close = sum(1 for c in comparisons.values() if c.status == "close")
    targets_off = sum(1 for c in comparisons.values() if c.status == "off")
    
    return {
        "targets_defined": targets_defined,
        "targets_met": targets_met,
        "targets_close": targets_close,
        "targets_off": targets_off,
        "completion_pct": round(100.0 * targets_met / targets_defined, 1) if targets_defined > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Target Profiles Registry
# ---------------------------------------------------------------------------

TARGET_PROFILES: Dict[str, Dict[str, Any]] = {
    "viking_sportfisher": {
        "profile_id": "viking_sportfisher",
        "source": "named_profile",
        "description": "Viking Yachts sportfisher character",
        "targets": {
            "longitudinal_metric:sheer_peak_station": 0.72,
            "profile_metric:stem_rake_deg": 13.0,
            "profile_metric:stem_concavity_ratio": 0.10,
            "longitudinal_metric:entry_half_angle_deg": 11.0,
            "longitudinal_metric:bow_fineness_ratio": 0.22,
            "profile_metric:transom_rake_deg": 12.0,
            "profile_metric:transom_beam_ratio": 0.85,
            "longitudinal_metric:chine_rise_rate": 0.065,  # Corrected from 0.65 (m/m, not %)
            "longitudinal_metric:deadrise_progression_shape": 0.90,
        },
    },
    
    "displacement_trawler": {
        "profile_id": "displacement_trawler",
        "source": "named_profile",
        "description": "Traditional displacement trawler",
        "targets": {
            "longitudinal_metric:sheer_peak_station": 0.95,
            "profile_metric:stem_rake_deg": 5.0,
            "profile_metric:stem_concavity_ratio": 0.02,
            "longitudinal_metric:entry_half_angle_deg": 22.0,
            "longitudinal_metric:bow_fineness_ratio": 0.40,
            "profile_metric:transom_rake_deg": 5.0,
            "profile_metric:transom_beam_ratio": 0.70,
            "longitudinal_metric:deadrise_progression_shape": 0.98,
        },
    },
    
    "center_console": {
        "profile_id": "center_console",
        "source": "named_profile",
        "description": "Modern center console fishing boat",
        "targets": {
            "longitudinal_metric:sheer_peak_station": 0.85,
            "profile_metric:stem_rake_deg": 10.0,
            "profile_metric:stem_concavity_ratio": 0.05,
            "longitudinal_metric:entry_half_angle_deg": 14.0,
            "profile_metric:transom_beam_ratio": 0.88,
            "longitudinal_metric:chine_rise_rate": 0.045,  # Corrected from 0.45 (m/m, not %)
        },
    },
    
    "express_cruiser": {
        "profile_id": "express_cruiser",
        "source": "named_profile",
        "description": "Express cruiser / weekender",
        "targets": {
            "longitudinal_metric:sheer_peak_station": 0.80,
            "profile_metric:stem_rake_deg": 12.0,
            "profile_metric:stem_concavity_ratio": 0.06,
            "longitudinal_metric:entry_half_angle_deg": 13.0,
            "profile_metric:transom_beam_ratio": 0.82,
            "longitudinal_metric:deadrise_progression_shape": 0.92,
        },
    },
}


def get_target_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """Get a named target profile."""
    return TARGET_PROFILES.get(profile_id)


def list_target_profiles() -> List[str]:
    """List available profile IDs."""
    return list(TARGET_PROFILES.keys())


def infer_profile_from_vessel_type(vessel_type: str) -> Optional[str]:
    """Map vessel type to profile ID."""
    mapping = {
        "sportfisher": "viking_sportfisher",
        "sportfishing": "viking_sportfisher",
        "viking": "viking_sportfisher",
        "trawler": "displacement_trawler",
        "displacement": "displacement_trawler",
        "center_console": "center_console",
        "cc": "center_console",
        "express": "express_cruiser",
        "cruiser": "express_cruiser",
    }
    return mapping.get(vessel_type.lower().replace(" ", "_").replace("-", "_"))
