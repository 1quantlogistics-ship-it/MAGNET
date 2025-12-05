"""
MAGNET Memory Schemas
=====================

Pydantic schemas for all memory files in the MAGNET system.
These define the contracts for agent communication.

Note: Per Dev Plan, ALPHA may take ownership of schemas/ directory.
These are temporary implementations until ALPHA provides the official versions.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class VoteType(str, Enum):
    """Agent vote types for consensus."""
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class DesignPhase(str, Enum):
    """8-phase design spiral per Operations Guide."""
    MISSION = "mission"
    HULL_FORM = "hull_form"
    PROPULSION = "propulsion"
    STRUCTURE = "structure"
    ARRANGEMENT = "arrangement"
    WEIGHT_STABILITY = "weight_stability"
    COMPLIANCE = "compliance"
    PRODUCTION = "production"


class MissionSchema(BaseModel):
    """
    Mission requirements schema.
    Written by Director agent after interpreting user requirements.

    File: memory/mission.json
    """
    mission_id: str = Field(..., description="Unique mission identifier")
    vessel_type: str = Field(..., description="e.g., patrol_catamaran")
    loa_m: float = Field(..., description="Length overall in meters")
    beam_m: float = Field(..., description="Beam in meters")
    design_speed_kts: float = Field(..., description="Design speed in knots")
    cruise_speed_kts: float = Field(..., description="Cruise speed in knots")
    crew: int = Field(..., description="Crew complement")
    endurance_nm: float = Field(..., description="Range in nautical miles")
    payload_kg: float = Field(default=0, description="Payload capacity in kg")
    classification: Optional[str] = Field(default=None, description="e.g., ABS_HSNC")
    military_spec: Optional[str] = Field(default=None, description="e.g., MIL-DTL-901E_GRADE_A")
    constraints: Dict[str, float] = Field(default_factory=dict, description="Hard constraints")
    created_at: datetime = Field(default_factory=datetime.now)
    iteration: int = Field(default=1)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class HullParamsSchema(BaseModel):
    """
    Hull form parameters schema.
    Written by Naval Architect agent.

    File: memory/hull_params.json
    """
    hull_form: str = Field(..., description="e.g., deep_v_catamaran")
    demihull_count: int = Field(default=2)
    length_wl_m: float = Field(..., description="Waterline length")
    beam_demihull_m: float = Field(..., description="Beam of each demihull")
    demihull_spacing_m: float = Field(..., description="Spacing between demihulls")
    deadrise_transom_deg: float = Field(..., description="Deadrise at transom")
    deadrise_midship_deg: float = Field(..., description="Deadrise at midship")
    prismatic_coefficient: float = Field(..., ge=0.5, le=0.8)
    block_coefficient: float = Field(..., ge=0.3, le=0.6)
    lcb_from_transom_pct: float = Field(..., description="LCB as % from transom")
    proposed_by: str = Field(default="naval_architect")
    iteration: int = Field(default=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SystemStateSchema(BaseModel):
    """
    Current system state tracking.
    Tracks design spiral phase, iteration, and agent status.

    File: memory/system_state.json
    """
    current_phase: DesignPhase = Field(default=DesignPhase.MISSION)
    phase_iteration: int = Field(default=1)
    design_iteration: int = Field(default=1)
    active_agents: List[str] = Field(default_factory=list)
    pending_votes: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="initializing")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentVoteSchema(BaseModel):
    """
    Agent vote for consensus decisions.
    Appended to memory/decisions/voting_history.jsonl
    """
    agent_id: str = Field(..., description="Unique agent identifier")
    proposal_id: str = Field(..., description="ID of proposal being voted on")
    vote: VoteType = Field(..., description="approve, reject, or revise")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Explanation for vote")
    concerns: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class StructuralDesignSchema(BaseModel):
    """
    Structural design parameters.
    Written by Structural Engineer agent.

    File: memory/structural_design.json
    """
    material: str = Field(default="5083-H116", description="Hull material alloy")
    bottom_plate_mm: float = Field(..., description="Bottom plate thickness")
    side_plate_mm: float = Field(..., description="Side plate thickness")
    deck_plate_mm: float = Field(..., description="Deck plate thickness")
    frame_spacing_mm: float = Field(..., description="Transverse frame spacing")
    longitudinal_spacing_mm: float = Field(..., description="Longitudinal spacing")
    proposed_by: str = Field(default="structural_engineer")
    iteration: int = Field(default=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rule_reference: Optional[str] = Field(default=None, description="e.g., ABS HSNC 3-3-2/5.1")


class WeightEstimateSchema(BaseModel):
    """
    Weight and CG estimate.

    File: memory/weight_estimate.json
    """
    lightship_kg: float = Field(..., description="Lightship weight")
    deadweight_kg: float = Field(..., description="Deadweight")
    displacement_kg: float = Field(..., description="Full load displacement")
    lcg_from_transom_m: float = Field(..., description="Longitudinal CG")
    vcg_from_baseline_m: float = Field(..., description="Vertical CG")
    tcg_from_centerline_m: float = Field(default=0.0, description="Transverse CG")
    proposed_by: str = Field(default="weight_engineer")
    iteration: int = Field(default=1)


class StabilityResultsSchema(BaseModel):
    """
    Hydrostatic and stability calculations.

    File: memory/stability_results.json
    """
    displacement_tonnes: float
    draft_m: float
    trim_deg: float
    gm_m: float = Field(..., description="Metacentric height")
    bm_m: float = Field(..., description="Metacentric radius")
    kb_m: float = Field(..., description="Height of center of buoyancy")
    lcb_from_transom_m: float
    waterplane_area_m2: float
    wetted_surface_m2: float
    calculated_by: str = Field(default="physics_engine")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
