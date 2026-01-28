"""
Change propagation engine for MAGNET iterative design loop.

When a parameter changes, this module:
1. Identifies which phases are invalidated
2. Triggers selective revalidation
3. Computes deltas for all tracked metrics
4. Surfaces constraint violations

The kernel validates physics, not design intent.
Novel forms work without new code.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import time
import copy

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MetricDelta:
    """Change in a tracked metric."""
    metric: str
    previous: Optional[float]
    current: Optional[float]
    delta: Optional[float]
    percent_change: Optional[float]
    direction: str  # "improved", "degraded", "neutral", "unknown"


@dataclass
class ConstraintViolation:
    """A constraint that failed after propagation."""
    constraint_id: str
    expression: str          # "hull.gm >= 0.5"
    current_value: float
    required_value: float
    severity: str            # "ERROR" | "WARNING"
    caused_by: str           # The key change that caused this
    suggestion: str


@dataclass
class PropagationResult:
    """Result of change propagation through pipeline."""
    changed_key: str
    previous_value: Any
    new_value: Any
    invalidated_phases: List[str]
    metric_deltas: Dict[str, MetricDelta]
    constraint_violations: List[ConstraintViolation]
    phase_results: Dict[str, Any]
    cascade_time_ms: int
    success: bool


# =============================================================================
# TRACKED METRICS
# =============================================================================

# Metrics tracked across iterations for delta computation
TRACKED_METRICS = [
    # Hull
    "hull.displacement_m3",
    "hull.wetted_surface_m2",
    "hull.block_coefficient",
    "hull.prismatic_coefficient",
    
    # Stability
    "stability.gm_m",
    "stability.bm_m",
    "stability.kb_m",
    
    # Resistance/Performance
    "resistance.total_kn",
    "performance.max_speed_kts",
    
    # Weight
    "weight.lightship_kg",
    "weight.vcg_m",
    "weight.lcg_m",
    
    # Cost
    "cost.build_usd",
    "cost.annual_operating_usd",
]

# Metrics where LOWER is better
LOWER_IS_BETTER = {
    "resistance.total_kn",
    "weight.lightship_kg",
    "cost.build_usd",
    "cost.annual_operating_usd",
}

# Metrics where HIGHER is better
HIGHER_IS_BETTER = {
    "stability.gm_m",
    "performance.max_speed_kts",
}


# =============================================================================
# PHASE DEPENDENCIES
# =============================================================================

# Phase dependencies from conductor registry
PHASE_DEPS = {
    "mission": set(),
    "hull": {"mission"},
    "structure": {"hull"},
    "propulsion": {"hull"},
    "arrangement": {"hull"},
    "weight": {"hull", "structure", "propulsion"},
    "stability": {"weight"},
    "loading": {"weight", "stability"},
    "compliance": {"stability", "loading", "mission"},
    "production": {"structure", "weight"},
    "cost": {"production"},
    "optimization": {"cost", "compliance"},
    "reporting": {"compliance", "cost"},
}

# State key prefixes to phase mapping
KEY_TO_PHASE = {
    "hull.": "hull",
    "geometry.": "hull",
    "resources.geometry.": "hull",
    "structure.": "structure",
    "propulsion.": "propulsion",
    "weight.": "weight",
    "stability.": "stability",
    "loading.": "loading",
    "mission.": "mission",
    "cost.": "cost",
}

# Execution order
PHASE_ORDER = [
    "mission", "hull", "structure", "propulsion", "arrangement",
    "weight", "stability", "loading", "compliance", "production",
    "cost", "optimization", "reporting"
]


# =============================================================================
# PROPAGATION ENGINE
# =============================================================================

class PropagationEngine:
    """
    Tracks dependencies and triggers selective revalidation.
    
    Core of the iterative design spiral:
    - Engineer changes a parameter
    - Engine identifies affected phases
    - Engine reruns only those phases
    - Engine computes deltas and surfaces violations
    """
    
    def __init__(self):
        self._previous_metrics: Dict[str, float] = {}
        self._last_changed_key: Optional[str] = None
    
    def get_invalidated_phases(self, changed_key: str) -> List[str]:
        """
        Get all phases that need recomputation after a key changes.
        
        Uses BFS to find all downstream phases.
        """
        # Find which phase owns this key
        source_phase = None
        for prefix, phase in KEY_TO_PHASE.items():
            if changed_key.startswith(prefix):
                source_phase = phase
                break
        
        if not source_phase:
            logger.debug(f"No phase found for key: {changed_key}")
            return []
        
        # BFS to find all downstream phases
        invalidated: Set[str] = {source_phase}
        queue = [source_phase]
        
        while queue:
            current = queue.pop(0)
            for phase, deps in PHASE_DEPS.items():
                if current in deps and phase not in invalidated:
                    invalidated.add(phase)
                    queue.append(phase)
        
        # Return in execution order
        return [p for p in PHASE_ORDER if p in invalidated]
    
    def propagate_change(
        self,
        key: str,
        new_value: Any,
        state_manager: Any,
        conductor: Any,
    ) -> PropagationResult:
        """
        Execute change and propagate through pipeline.
        
        This is the core of the iterative design loop:
        1. Capture previous metrics
        2. Apply change
        3. Determine phases to rerun
        4. Rerun phases
        5. Compute deltas
        6. Check constraints
        """
        start_time = time.perf_counter()
        self._last_changed_key = key
        
        # Capture previous state
        previous_value = self._get_state_value(state_manager, key)
        previous_metrics = self._capture_metrics(state_manager)
        
        # Apply change
        self._set_state_value(state_manager, key, new_value)
        
        # Determine what to recompute
        phases_to_run = self.get_invalidated_phases(key)
        logger.info(f"Change to {key} invalidates phases: {phases_to_run}")
        
        # Run phases in order
        phase_results = {}
        for phase in phases_to_run:
            try:
                result = conductor.run_phase(phase)
                phase_results[phase] = {
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "errors": result.errors,
                }
            except Exception as e:
                logger.warning(f"Phase {phase} failed during propagation: {e}")
                phase_results[phase] = {"status": "failed", "errors": [str(e)]}
        
        # Capture new metrics and compute deltas
        current_metrics = self._capture_metrics(state_manager)
        deltas = self._compute_deltas(previous_metrics, current_metrics)
        
        # Check constraints
        violations = self._check_constraints(state_manager, key)
        
        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Store current metrics for next iteration
        self._previous_metrics = current_metrics
        
        return PropagationResult(
            changed_key=key,
            previous_value=previous_value,
            new_value=new_value,
            invalidated_phases=phases_to_run,
            metric_deltas=deltas,
            constraint_violations=violations,
            phase_results=phase_results,
            cascade_time_ms=elapsed_ms,
            success=len(violations) == 0,
        )
    
    def _get_state_value(self, state_manager: Any, key: str) -> Any:
        """Get value from state manager."""
        if hasattr(state_manager, 'get'):
            return state_manager.get(key)
        return None
    
    def _set_state_value(self, state_manager: Any, key: str, value: Any) -> None:
        """Set value in state manager."""
        if hasattr(state_manager, 'set'):
            state_manager.set(key, value, source="propagation_engine")
    
    def _capture_metrics(self, state_manager: Any) -> Dict[str, float]:
        """Capture current values for all tracked metrics."""
        metrics = {}
        
        for metric in TRACKED_METRICS:
            value = self._get_state_value(state_manager, metric)
            if value is not None:
                try:
                    metrics[metric] = float(value)
                except (TypeError, ValueError):
                    pass
        
        # Also capture from validation results if available
        hydro = self._get_state_value(state_manager, "validation.hydrostatics") or {}
        if isinstance(hydro, dict):
            if "gm_m" in hydro:
                metrics["stability.gm_m"] = hydro["gm_m"]
            if "displacement_m3" in hydro:
                metrics["hull.displacement_m3"] = hydro["displacement_m3"]
        
        return metrics
    
    def _compute_deltas(
        self,
        previous: Dict[str, float],
        current: Dict[str, float],
    ) -> Dict[str, MetricDelta]:
        """Compute delta for each tracked metric."""
        deltas = {}
        
        for metric in TRACKED_METRICS:
            prev_val = previous.get(metric)
            curr_val = current.get(metric)
            
            if curr_val is not None:
                if prev_val is not None:
                    delta = curr_val - prev_val
                    pct = (delta / prev_val * 100) if prev_val != 0 else None
                else:
                    delta = None
                    pct = None
                
                deltas[metric] = MetricDelta(
                    metric=metric,
                    previous=prev_val,
                    current=curr_val,
                    delta=delta,
                    percent_change=pct,
                    direction=self._get_direction(metric, delta),
                )
        
        return deltas
    
    def _get_direction(self, metric: str, delta: Optional[float]) -> str:
        """Determine if change is an improvement."""
        if delta is None:
            return "unknown"
        if abs(delta) < 0.001:
            return "neutral"
        
        if metric in LOWER_IS_BETTER:
            return "improved" if delta < 0 else "degraded"
        elif metric in HIGHER_IS_BETTER:
            return "improved" if delta > 0 else "degraded"
        else:
            return "neutral"
    
    def _check_constraints(
        self,
        state_manager: Any,
        caused_by: str,
    ) -> List[ConstraintViolation]:
        """Check all constraints against current state."""
        violations = []
        
        # Get constraints from state
        constraints = self._get_state_value(state_manager, "constraints") or {}
        
        # Also check standard design constraints
        standard_constraints = [
            ("stability.gm_m", ">=", 0.15, "hard", "IMO minimum GM"),
            ("hull.displacement_m3", ">", 0, "hard", "Volume must be positive"),
        ]
        
        # Check standard constraints
        for path, op, required, severity, name in standard_constraints:
            value = self._get_state_value(state_manager, path)
            
            # Also check validation results
            if value is None and path == "stability.gm_m":
                hydro = self._get_state_value(state_manager, "validation.hydrostatics") or {}
                value = hydro.get("gm_m")
            
            if value is not None:
                passes = self._evaluate_constraint(value, op, required)
                
                if not passes:
                    violations.append(ConstraintViolation(
                        constraint_id=name,
                        expression=f"{path} {op} {required}",
                        current_value=value,
                        required_value=required,
                        severity="ERROR" if severity == "hard" else "WARNING",
                        caused_by=caused_by,
                        suggestion=self._generate_suggestion(path, value, required),
                    ))
        
        # Check user-defined constraints
        if isinstance(constraints, dict):
            for constraint_id, constraint in constraints.items():
                if not isinstance(constraint, dict):
                    continue
                
                path = constraint.get("path", "")
                op = constraint.get("operator", ">=")
                required = constraint.get("value", 0)
                
                value = self._get_state_value(state_manager, path)
                if value is not None:
                    passes = self._evaluate_constraint(value, op, required)
                    
                    if not passes:
                        violations.append(ConstraintViolation(
                            constraint_id=constraint_id,
                            expression=f"{path} {op} {required}",
                            current_value=value,
                            required_value=required,
                            severity=constraint.get("severity", "WARNING"),
                            caused_by=caused_by,
                            suggestion=self._generate_suggestion(path, value, required),
                        ))
        
        return violations
    
    def _evaluate_constraint(self, value: float, op: str, required: float) -> bool:
        """Evaluate a constraint."""
        if op == ">=":
            return value >= required
        elif op == "<=":
            return value <= required
        elif op == ">":
            return value > required
        elif op == "<":
            return value < required
        elif op == "==":
            return abs(value - required) < 0.001
        return True
    
    def _generate_suggestion(
        self,
        path: str,
        current: float,
        required: float,
    ) -> str:
        """Generate actionable suggestion for constraint violation."""
        gap = required - current
        
        suggestions = {
            "stability.gm_m": f"Consider: increase beam (+{abs(gap)*2:.2f}m), decrease VCG ({abs(gap):.2f}m), or add ballast",
            "hull.displacement_m3": "Check section definitions - volume must be positive",
            "resistance.total_kn": "Consider: finer bow, reduce wetted surface, or reduce speed",
            "weight.lightship_kg": "Consider: lighter materials, optimize structure",
            "cost.build_usd": "Consider: simpler construction, standard components",
        }
        
        for key, suggestion in suggestions.items():
            if key in path:
                return suggestion
        
        return f"Gap: {abs(gap):.3f}. Review design parameters affecting {path}"


# =============================================================================
# ITERATION TRACKER
# =============================================================================

class IterationTracker:
    """
    Track metric changes across design iterations.
    
    Enables:
    - Agent learning ("my change improved GM by 0.15m")
    - Convergence detection ("stability oscillating, stop iteration")
    - User feedback ("beam increase caused 8% resistance penalty")
    """
    
    def __init__(self):
        self._history: List[Dict[str, float]] = []
        self._iteration: int = 0
    
    def record_iteration(self, metrics: Dict[str, float]) -> None:
        """Record metrics for this iteration."""
        self._history.append(copy.deepcopy(metrics))
        self._iteration += 1
    
    def get_delta(self, metric: str) -> Optional[float]:
        """Get delta from previous iteration."""
        if len(self._history) < 2:
            return None
        
        prev = self._history[-2].get(metric)
        curr = self._history[-1].get(metric)
        
        if prev is not None and curr is not None:
            return curr - prev
        return None
    
    def get_trend(self, metric: str, window: int = 3) -> str:
        """
        Get trend direction over recent iterations.
        
        Returns: "improving", "degrading", "oscillating", "stable", "unknown"
        """
        if len(self._history) < window:
            return "unknown"
        
        recent = [h.get(metric) for h in self._history[-window:]]
        if None in recent:
            return "unknown"
        
        # Check for oscillation
        diffs = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
        signs = [1 if d > 0 else -1 if d < 0 else 0 for d in diffs]
        
        if len(set(signs)) > 1 and signs != [0] * len(signs):
            return "oscillating"
        
        # Check trend
        total_change = recent[-1] - recent[0]
        if abs(total_change) < 0.001:
            return "stable"
        
        # Check if improvement based on metric type
        if metric in HIGHER_IS_BETTER:
            return "improving" if total_change > 0 else "degrading"
        elif metric in LOWER_IS_BETTER:
            return "improving" if total_change < 0 else "degrading"
        
        return "stable"
    
    def is_converged(self, tolerance: float = 0.01, window: int = 3) -> bool:
        """Check if all metrics have converged."""
        if len(self._history) < window:
            return False
        
        for metric in TRACKED_METRICS:
            trend = self.get_trend(metric, window)
            if trend not in ("stable", "unknown"):
                return False
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of iteration history."""
        if not self._history:
            return {"iterations": 0}
        
        summary = {
            "iterations": self._iteration,
            "metrics": {},
        }
        
        for metric in TRACKED_METRICS:
            if metric in self._history[-1]:
                summary["metrics"][metric] = {
                    "current": self._history[-1][metric],
                    "delta": self.get_delta(metric),
                    "trend": self.get_trend(metric),
                }
        
        summary["converged"] = self.is_converged()
        
        return summary


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def propagate(
    key: str,
    value: Any,
    state_manager: Any,
    conductor: Any,
) -> PropagationResult:
    """
    Convenience function for single change propagation.
    
    Usage:
        result = propagate("hull.beam", 5.0, state_manager, conductor)
        if result.constraint_violations:
            print("Constraints violated:", result.constraint_violations)
    """
    engine = PropagationEngine()
    return engine.propagate_change(key, value, state_manager, conductor)

