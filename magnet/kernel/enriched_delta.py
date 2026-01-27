"""
EnrichedDelta — Unified delta structure for feedback.

Combines:
- RecalculationResult from CascadeExecutor (EXISTING)
- MetricDelta semantics from PropagationEngine (NEW)

This enables the design spiral to provide meaningful feedback:
- What changed (parameter, old value, new value)
- How much it changed (delta, percent)
- Whether it improved or degraded (direction)

Reference: MAGNET_Merge_Implementation_Plan.md Phase 4
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magnet.kernel.metric_polarity import get_direction, format_direction


@dataclass
class EnrichedDelta:
    """
    Enriched metric delta with direction semantics.

    Used in feedback generation to tell users not just WHAT changed,
    but WHETHER the change was good or bad.
    
    Example:
        delta = EnrichedDelta.from_values(
            parameter="stability.gm_m",
            old_value=0.4,
            new_value=0.6,
        )
        # delta.direction == "improved"
        # delta.delta == 0.2
        # delta.percent_change == 50.0
    """

    parameter: str
    old_value: Optional[float]
    new_value: Optional[float]
    delta: Optional[float]
    percent_change: Optional[float]
    direction: str  # "improved" | "degraded" | "neutral"

    # From RecalculationResult
    execution_time_ms: int = 0
    was_skipped: bool = False

    # Display helpers
    unit: str = ""
    display_name: str = ""

    @classmethod
    def from_values(
        cls,
        parameter: str,
        old_value: Optional[float],
        new_value: Optional[float],
        execution_time_ms: int = 0,
        unit: str = "",
    ) -> "EnrichedDelta":
        """Create EnrichedDelta from old and new values."""
        delta = None
        percent_change = None
        
        if old_value is not None and new_value is not None:
            delta = new_value - old_value
            if old_value != 0:
                percent_change = (delta / abs(old_value)) * 100

        direction = get_direction(parameter, delta if delta is not None else 0.0)

        # Generate display name from parameter path
        display_name = parameter.split(".")[-1].replace("_", " ").title()

        return cls(
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            delta=delta,
            percent_change=percent_change,
            direction=direction,
            execution_time_ms=execution_time_ms,
            unit=unit,
            display_name=display_name,
        )

    @classmethod
    def from_recalculation_result(
        cls,
        result: Any,  # RecalculationResult
    ) -> "EnrichedDelta":
        """Create from CascadeExecutor RecalculationResult."""
        return cls.from_values(
            parameter=result.parameter,
            old_value=result.old_value if hasattr(result, 'old_value') else None,
            new_value=result.new_value if hasattr(result, 'new_value') else None,
            execution_time_ms=result.execution_time_ms if hasattr(result, 'execution_time_ms') else 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "display_name": self.display_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "delta": self.delta,
            "percent_change": self.percent_change,
            "direction": self.direction,
            "unit": self.unit,
            "execution_time_ms": self.execution_time_ms,
            "was_skipped": self.was_skipped,
        }

    def format_for_display(self) -> str:
        """Format delta for human-readable display."""
        direction_str = format_direction(self.direction)
        
        if self.delta is None:
            return f"{self.display_name}: {self.new_value}"
        
        if self.percent_change is not None and abs(self.percent_change) >= 0.1:
            return (
                f"{self.display_name}: {self.old_value:.2f} → {self.new_value:.2f} "
                f"({self.delta:+.2f}, {self.percent_change:+.1f}%) {direction_str}"
            )
        else:
            return (
                f"{self.display_name}: {self.old_value:.2f} → {self.new_value:.2f} "
                f"({self.delta:+.2f}) {direction_str}"
            )

    @property
    def is_significant(self) -> bool:
        """Check if the change is significant (>1% or direction changed)."""
        if self.percent_change is None:
            return self.delta is not None and abs(self.delta) > 0
        return abs(self.percent_change) >= 1.0 or self.direction != "neutral"


@dataclass
class DeltaSummary:
    """Summary of multiple deltas for feedback generation."""
    
    deltas: List[EnrichedDelta] = field(default_factory=list)
    
    @property
    def improved_count(self) -> int:
        return sum(1 for d in self.deltas if d.direction == "improved")
    
    @property
    def degraded_count(self) -> int:
        return sum(1 for d in self.deltas if d.direction == "degraded")
    
    @property
    def neutral_count(self) -> int:
        return sum(1 for d in self.deltas if d.direction == "neutral")
    
    @property
    def significant_deltas(self) -> List[EnrichedDelta]:
        return [d for d in self.deltas if d.is_significant]
    
    @property
    def overall_direction(self) -> str:
        """Determine overall direction based on majority."""
        if self.improved_count > self.degraded_count:
            return "improved"
        elif self.degraded_count > self.improved_count:
            return "degraded"
        else:
            return "neutral"
    
    def format_summary(self) -> str:
        """Format summary for display."""
        parts = []
        
        if self.improved_count > 0:
            parts.append(f"✅ {self.improved_count} improved")
        if self.degraded_count > 0:
            parts.append(f"⚠️ {self.degraded_count} degraded")
        if self.neutral_count > 0:
            parts.append(f"➡️ {self.neutral_count} unchanged")
        
        return " | ".join(parts) if parts else "No changes"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deltas": [d.to_dict() for d in self.deltas],
            "improved_count": self.improved_count,
            "degraded_count": self.degraded_count,
            "neutral_count": self.neutral_count,
            "overall_direction": self.overall_direction,
        }


def create_deltas_from_validation(
    old_validation: Dict[str, Any],
    new_validation: Dict[str, Any],
) -> DeltaSummary:
    """
    Create EnrichedDeltas by comparing validation results.
    
    This is used after geometry recompilation to show what changed.
    """
    deltas = []
    
    # Compare hydrostatics
    old_hydro = old_validation.get("hydrostatics", {})
    new_hydro = new_validation.get("hydrostatics", {})
    
    hydro_params = ["gm_m", "bm_transverse_m", "kb_m", "displacement_m3"]
    for param in hydro_params:
        old_val = old_hydro.get(param)
        new_val = new_hydro.get(param)
        
        if old_val is not None or new_val is not None:
            deltas.append(EnrichedDelta.from_values(
                parameter=f"hydrostatics.{param}",
                old_value=old_val,
                new_value=new_val,
            ))
    
    # Compare resistance
    old_resist = old_validation.get("resistance", {})
    new_resist = new_validation.get("resistance", {})
    
    resist_params = ["resistance_kn", "total_resistance_kn"]
    for param in resist_params:
        old_val = old_resist.get(param)
        new_val = new_resist.get(param)
        
        if old_val is not None or new_val is not None:
            deltas.append(EnrichedDelta.from_values(
                parameter=f"resistance.{param}",
                old_value=old_val,
                new_value=new_val,
            ))
    
    return DeltaSummary(deltas=deltas)

