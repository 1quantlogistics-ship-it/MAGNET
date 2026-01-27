"""
magnet/errors/propagation.py

T7.4: Unified error propagation.

Deep failures must surface as:
- technical detail (for debugging)
- human-readable user message
- actionable suggestions

This module is intentionally small and integrates with the existing error
taxonomy + recovery modules (do not duplicate them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from magnet.errors.recovery import RECOVERY_STRATEGIES
from magnet.errors.taxonomy import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    MAGNETError,
    create_physics_error,
    create_transaction_error,
    create_validation_error,
)


@dataclass(frozen=True)
class PropagatedError:
    origin_layer: str  # "kernel" | "conflict_resolver" | "validator" | "orchestrator" | etc.
    error_type: str
    technical_message: str
    user_message: str
    suggestions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    magnet_error: Optional[MAGNETError] = None


class ErrorPropagator(Protocol):
    def propagate(self, error: Exception, layer: str) -> PropagatedError: ...


def _recovery_suggestions_for(code: ErrorCode) -> List[str]:
    opts = RECOVERY_STRATEGIES.get(code, [])
    out: List[str] = []
    for opt in opts:
        # Keep suggestions user-facing: use the configured description.
        if opt.description:
            out.append(str(opt.description))
    return out


class DefaultErrorPropagator:
    """
    Default implementation:
    - maps known exception types into MAGNETError taxonomy
    - uses configured recovery strategies for suggestions
    - always produces a non-empty user_message
    """

    def propagate(self, error: Exception, layer: str) -> PropagatedError:
        origin = str(layer or "unknown")
        err_type = type(error).__name__
        technical = f"{err_type}: {error}"

        # If it's already a MAGNETError, preserve it.
        if isinstance(error, MAGNETError):
            me = error
            user = me.message or "An error occurred."
            suggestions = _recovery_suggestions_for(me.code) or list(me.recovery_options or [])
            return PropagatedError(
                origin_layer=origin,
                error_type=err_type,
                technical_message=technical,
                user_message=user,
                suggestions=suggestions,
                context={
                    "code": me.code.value,
                    "category": me.category.value,
                    "severity": me.severity.value,
                    "source": me.source,
                    "path": me.path,
                    "transaction_id": me.transaction_id,
                },
                magnet_error=me,
            )

        # Known safety/transactionality failures should be loud and actionable.
        name = err_type.lower()
        msg = str(error)

        if "mutationenforcement" in name or "direct write" in msg.lower():
            me = create_transaction_error(
                message="Write-path guard blocked an unsafe mutation.",
                transaction_id="unknown",
                source=f"{origin}.write_path",
            )
            return PropagatedError(
                origin_layer=origin,
                error_type=err_type,
                technical_message=technical,
                user_message="A safety guard blocked a direct state write. This change must be applied via the DesignMutator/write-transaction path.",
                suggestions=_recovery_suggestions_for(me.code) or ["Retry the change through the approved mutator/transaction API."],
                context={"category": me.category.value, "severity": me.severity.value},
                magnet_error=me,
            )

        if "unsafe" in name and "state" in name:
            me = create_validation_error(
                message="Unsafe evaluation blocked (requires isolated clone).",
                source=f"{origin}.isolation",
            )
            me.category = ErrorCategory.STATE  # type: ignore[assignment]
            me.severity = ErrorSeverity.ERROR  # type: ignore[assignment]
            return PropagatedError(
                origin_layer=origin,
                error_type=err_type,
                technical_message=technical,
                user_message="Safety guard: this evaluation requires an isolated snapshot/clone; refusing to run against live state.",
                suggestions=[
                    "Ensure the evaluation uses StateManager.clone() / GradientIsolation (clone → perturb → discard).",
                    "If you are inside an optimizer, evaluate in a sandboxed copy and commit only after validation.",
                ],
                context={"category": me.category.value, "severity": me.severity.value},
                magnet_error=me,
            )

        # Heuristic: treat explicit 'physics' failures as non-recoverable unless stated otherwise.
        if "physics" in name or "hydrostatics" in name or "equilibrium" in name:
            me = create_physics_error(message=msg or "Physics validation failed.", source=f"{origin}.physics")
            return PropagatedError(
                origin_layer=origin,
                error_type=err_type,
                technical_message=technical,
                user_message="Physics validation failed: the proposed design cannot satisfy physical constraints as stated.",
                suggestions=_recovery_suggestions_for(me.code) or [
                    "Reduce demanded performance/capacity or increase envelope (LOA/beam/draft).",
                    "Inspect the failing constraint and adjust the proposal to satisfy it.",
                ],
                context={"category": me.category.value, "severity": me.severity.value},
                magnet_error=me,
            )

        # Default: validation-style error with gentle suggestions.
        me = create_validation_error(message=msg or "Validation failed.", source=f"{origin}.error")
        suggestions = _recovery_suggestions_for(me.code) or [
            "Check parameter bounds and units.",
            "Try a smaller edit (reduce deltas / scope).",
        ]
        return PropagatedError(
            origin_layer=origin,
            error_type=err_type,
            technical_message=technical,
            user_message=me.message or "An error occurred.",
            suggestions=suggestions,
            context={"category": me.category.value, "severity": me.severity.value},
            magnet_error=me,
        )

