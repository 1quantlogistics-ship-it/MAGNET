"""
magnet/agents/vessel_thinking_schema.py

Typed schema for the Grammar‑First “Vessel Thinking Pass”.

This is a *thinking artifact* schema only. It does NOT introduce hull-type enums and does
NOT change integrity policy; it is used to enforce "no silent defaults" and to enable
server-side re-execution of generic, mechanically-checkable checks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field

from magnet.agents.geometry_observables import VALID_OBSERVABLE_IDS


class StationPlan(BaseModel):
    count: int = Field(..., ge=3, description="Number of stations/sections intended (>=3).")
    distribution: Optional[str] = Field(
        default=None, description='e.g. "uniform", "end-dense", "explicit"'
    )
    explicit_xs: Optional[List[float]] = Field(
        default=None, description="Optional explicit station x-positions (meters)."
    )
    rationale: str = Field(..., min_length=1)


class AnchorPoint(BaseModel):
    x: float = Field(..., description="Normalized domain coordinate (typically 0..1).")
    value: float = Field(..., description="Schedule value at x.")


class BaseDOF(BaseModel):
    name: str = Field(..., min_length=1)
    defaulted: bool = False
    consequence: Optional[str] = None


class ScalarDOF(BaseDOF):
    type: Literal["scalar"] = "scalar"
    units: Optional[str] = None
    value: float


class ScheduleDOF(BaseDOF):
    type: Literal["schedule"] = "schedule"
    units: Optional[str] = None
    domain: Tuple[float, float] = (0.0, 1.0)
    anchor_points: List[AnchorPoint] = Field(default_factory=list)
    interpolation: str = "linear"


class TrackDOF(BaseDOF):
    type: Literal["track"] = "track"
    anchor_rule: str = Field(..., min_length=1)
    # v0: flexible but typed container; validator will interpret common shapes
    body_coverage: Dict[str, Any] = Field(default_factory=dict)


class BodyDOF(BaseDOF):
    type: Literal["body"] = "body"
    body_id: Optional[str] = None
    station_count: int = Field(..., ge=3)
    point_count_per_station: int = Field(..., ge=3)


DOFEntry = Union[ScalarDOF, ScheduleDOF, TrackDOF, BodyDOF]


class BaseCheck(BaseModel):
    name: str = Field(..., min_length=1, description="Stable check id/name.")
    target: str = Field(..., min_length=1, description="DOF name or target identifier.")


class RangeCheck(BaseCheck):
    type: Literal["range"] = "range"
    min: float
    max: float


class MonotonicCheck(BaseCheck):
    type: Literal["monotonic"] = "monotonic"
    direction: Literal["increasing", "decreasing", "either"] = "either"


class VariesCheck(BaseCheck):
    type: Literal["varies"] = "varies"


class CoverageCheck(BaseCheck):
    type: Literal["coverage"] = "coverage"
    expected_stations: int = Field(..., ge=2)


class UniformCheck(BaseCheck):
    type: Literal["uniform"] = "uniform"
    attribute: str = Field(..., min_length=1)


class CorrespondenceCheck(BaseCheck):
    type: Literal["correspondence"] = "correspondence"
    rule: str = Field(..., min_length=1)


CheckEntry = Union[
    RangeCheck,
    MonotonicCheck,
    VariesCheck,
    CoverageCheck,
    UniformCheck,
    CorrespondenceCheck,
]


class ProofEntry(BaseModel):
    check_name: str = Field(..., min_length=1)
    result: Literal["PASS", "FAIL"]
    computed: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class VesselThinkingPass(BaseModel):
    station_plan: StationPlan
    dof_schema: List[DOFEntry] = Field(default_factory=list)
    verification_schema: List[CheckEntry] = Field(default_factory=list)
    closure_proof: List[ProofEntry] = Field(default_factory=list)
    realism_audit: Optional[str] = None

    # v0.1: DOF→Geometry binding table + observation targets (no priors; verifiable interface)
    binding_table: List["BindingEntry"] = Field(default_factory=list)


class NeedsClarification(BaseModel):
    status: Literal["NEEDS_CLARIFICATION"] = "NEEDS_CLARIFICATION"
    question: str = Field(..., min_length=1)


VesselThinkingResponse = Union[VesselThinkingPass, NeedsClarification]


def parse_vessel_thinking_response(payload: Any) -> VesselThinkingResponse:
    """
    Deterministic parser for the thinking payload.

    We intentionally avoid clever unions/discriminators here because the LLM sometimes
    omits `status` on the main shape. This parser:
    - treats {status: NEEDS_CLARIFICATION, question: ...} as NeedsClarification
    - otherwise validates as VesselThinkingPass
    """
    if isinstance(payload, dict) and str(payload.get("status", "")).upper() == "NEEDS_CLARIFICATION":
        return NeedsClarification.model_validate(payload)
    return VesselThinkingPass.model_validate(payload)


class ObservationTarget(BaseModel):
    """
    A measurable target the kernel will compute from the emitted geometry.
    """

    observable_id: str = Field(..., description="Observable id (must exist in registry).")
    span_min: float = Field(
        0.0,
        ge=0.0,
        description="Minimum required span across stations for this observable (same units as observable).",
    )
    threshold_min: Optional[float] = Field(
        default=None,
        description="Optional minimum bound for the measured value/aggregate (applies primarily to longitudinal_metric:*).",
    )
    threshold_max: Optional[float] = Field(
        default=None,
        description="Optional maximum bound for the measured value/aggregate (applies primarily to longitudinal_metric:*).",
    )
    body_id: Optional[str] = Field(default=None, description="Optional body scope; default=all bodies.")
    station_range: Tuple[float, float] = Field(
        default=(0.0, 1.0),
        description="Normalized station range [0..1] to scope the measurement to a region (entry/run).",
    )

    def validate_observable_id(self) -> None:
        if self.observable_id not in VALID_OBSERVABLE_IDS:
            raise ValueError(f"Unknown observable_id: {self.observable_id}")


class BindingEntry(BaseModel):
    """
    v0.1 binding entry.

    - binds_to: which observables this DOF claims to influence.
    - observation_targets: what the kernel should measure to verify the DOF is implemented.
    """

    dof_name: str = Field(..., min_length=1)
    binds_to: List[str] = Field(default_factory=list)
    observation_targets: List[ObservationTarget] = Field(default_factory=list)

    def validate_binds_to(self) -> None:
        unknown = [x for x in (self.binds_to or []) if x not in VALID_OBSERVABLE_IDS]
        if unknown:
            raise ValueError(f"Unknown binds_to observables: {unknown}")


# Resolve forward refs for binding_table.
VesselThinkingPass.model_rebuild()


