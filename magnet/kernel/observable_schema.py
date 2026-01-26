"""
magnet/kernel/observable_schema.py

T2.3: ObservableSchema summary passed to LLM every turn.

Purpose:
- Provide a bounded, explicit list of observable_ids (and controllable subset).
- Provide canonical "unknown observable" rejection behavior.
- Provide a small set of example queries so the agent stays within the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from magnet.kernel.observable_registry import ObservableRegistry, ObservableSpec


@dataclass(frozen=True)
class ObservableSchema:
    observables: List[Dict[str, Any]]
    controllable_observable_ids: List[str]
    measurable_observable_ids: List[str]
    examples: List[str]
    unknown_observable_behavior: str
    targets: List[Dict[str, Any]]


class ObservableSchemaGenerator:
    def __init__(self, *, max_examples: int = 6) -> None:
        self._max_examples = int(max_examples)

    def build(
        self,
        *,
        registry: ObservableRegistry,
        targets: Optional[List[Dict[str, Any]]] = None,
    ) -> ObservableSchema:
        specs = registry.list_specs()
        obs_payload = [_spec_to_payload(s) for s in specs]

        controllable = sorted([s.observable_id for s in specs if bool(s.controllable)])
        measurable = sorted([s.observable_id for s in specs if bool(s.measurable)])

        examples = [
            "ASK observables()",
            "ASK controllable_observables()",
            "MEASURE observable_id=<id>",
            "TARGET observable_id=<id> value=<float> tolerance=<float>",
            "ADJUST observable_id=<id> delta=<float>",
            "COORDINATE targets={<obj>:<val>} adjustable=[<control>, ...]",
        ][: max(0, self._max_examples)]

        return ObservableSchema(
            observables=obs_payload,
            controllable_observable_ids=controllable,
            measurable_observable_ids=measurable,
            examples=examples,
            unknown_observable_behavior=(
                "Reject unknown observables: if observable_id not present in schema, return "
                "`unknown_observable` with nearest-match suggestions and do not mutate state."
            ),
            targets=list(targets or []),
        )

    def to_dict(self, schema: ObservableSchema) -> Dict[str, Any]:
        return {
            "observables": list(schema.observables),
            "controllable_observable_ids": list(schema.controllable_observable_ids),
            "measurable_observable_ids": list(schema.measurable_observable_ids),
            "targets": list(schema.targets),
            "examples": list(schema.examples),
            "unknown_observable_behavior": str(schema.unknown_observable_behavior),
        }


def _spec_to_payload(spec: ObservableSpec) -> Dict[str, Any]:
    return {
        "observable_id": str(spec.observable_id),
        "measurable": bool(spec.measurable),
        "controllable": bool(spec.controllable),
        "control_mode": str(getattr(spec, "control_mode", "") or ""),
        "unit": str(spec.unit or ""),
        "description": str(spec.description or ""),
        "tolerance": float(spec.tolerance or 0.0),
        "max_delta": float(spec.max_delta or 0.0),
        "knobs": list(spec.knobs or []),
        "applicable_to": list(getattr(spec, "applicable_to", []) or []),
    }

