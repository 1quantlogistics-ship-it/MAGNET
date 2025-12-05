"""
MAGNET Naval Architect Agent
=============================

The Naval Architect agent designs hull form parameters based on mission requirements.
Second agent in the design spiral after Director.

Responsibilities:
- Read mission requirements from memory
- Propose hull form parameters (dimensions, coefficients)
- Validate proposals using physics engine
- Write hull_params.json to memory

Communication Flow (from Operations Guide):
1. Director writes mission.json
2. Orchestrator triggers Naval Architect
3. Naval Architect proposes hull parameters → hull_params.json
4. Physics engine calculates hydrostatics → stability_results.json
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase

# Import ALPHA's schemas and physics
try:
    from schemas import HullParamsSchema, HullType
    from physics.hydrostatics.displacement import (
        calculate_displacement,
        calculate_wetted_surface_holtrop,
        calculate_waterplane_area,
    )
    from constraints.hull_form import HullFormConstraints
    ALPHA_AVAILABLE = True
except ImportError:
    ALPHA_AVAILABLE = False
    HullParamsSchema = None
    HullType = None


class NavalArchitectAgent(BaseAgent):
    """
    Naval Architect Agent - Hull Form Design.

    Proposes hull parameters based on mission requirements.
    Uses physics engine for validation and hydrostatic calculations.
    """

    NAVAL_ARCHITECT_PROMPT = """You are the Naval Architect Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to design hull form parameters based on mission requirements.

## Your Responsibilities:
1. Read mission requirements and understand the design drivers
2. Select appropriate hull type (monohull, catamaran, trimaran, etc.)
3. Propose principal dimensions (LOA, LWL, Beam, Draft, Depth)
4. Estimate form coefficients (Cb, Cp, Cm, Cwp)
5. Validate against naval architecture constraints

## Input Context:
You will receive the mission requirements including:
- Mission types (ISR, MCM, ASW, etc.)
- Performance requirements (speed, range, endurance)
- Payload requirements
- Environmental constraints (sea state)

## Output Format:
You must respond with a JSON object containing hull parameters. Include your reasoning before the JSON.

Example output:
```
Based on the mission requirements for a high-speed ISR platform:
- Hull Type: Semi-displacement catamaran for stability and deck area
- Length: 48m to accommodate payload and fuel
- Beam: 12.8m for catamaran stability
- Draft: 2.1m for high-speed operation
- Block Coefficient: 0.45 (fine hull for speed)

HULL_PARAMS_JSON:
{
  "hull_type": "semi_displacement",
  "length_overall": 48.0,
  "length_waterline": 45.0,
  "beam": 12.8,
  "draft": 2.1,
  "depth": 4.5,
  "block_coefficient": 0.45,
  "prismatic_coefficient": 0.65,
  "midship_coefficient": 0.85,
  "waterplane_coefficient": 0.78,
  "lcb_position": 0.52
}
```

## Design Guidelines:

### Hull Type Selection:
- MONOHULL: Traditional, good for displacement vessels
- CATAMARAN: Excellent stability, large deck area, good for unmanned
- TRIMARAN: Very high speed, complex construction
- SEMI_DISPLACEMENT: Good balance of speed and efficiency
- PLANING: Very high speed, limited seakeeping

### Principal Dimensions:
- Length/Beam ratio (L/B): 4-8 for monohulls, 8-15 for catamarans
- Beam/Draft ratio (B/T): 2-4 typical
- Draft typically 5-10% of LOA
- Freeboard = Depth - Draft (maintain adequate reserve buoyancy)

### Form Coefficients:
- Block coefficient (Cb): 0.35-0.45 fast, 0.45-0.55 medium, 0.55-0.65 slow
- Prismatic coefficient (Cp): 0.55-0.70, higher for higher Froude numbers
- Midship coefficient (Cm): 0.75-0.95, lower for fine hulls
- Waterplane coefficient (Cwp): 0.70-0.85

### Coefficient Relationships:
- Cb = Cp × Cm (must be consistent!)
- LCB position: 0.48-0.55 of LWL from aft perpendicular

Be conservative. Validate coefficient relationships.
"""

    def __init__(
        self,
        agent_id: str = "naval_architect_001",
        memory_path: str = "memory",
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="naval_architect",
            memory_path=memory_path,
            **kwargs
        )
        self._proposal_counter = 0

        # Initialize constraints validator if available
        self.constraints = HullFormConstraints() if ALPHA_AVAILABLE else None

    @property
    def system_prompt(self) -> str:
        return self.NAVAL_ARCHITECT_PROMPT

    def _generate_proposal_id(self) -> str:
        """Generate unique proposal ID."""
        self._proposal_counter += 1
        return f"hull_params_v{self._proposal_counter}"

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.

        Looks for HULL_PARAMS_JSON: marker or code blocks.
        """
        # Try to find HULL_PARAMS_JSON marker
        if "HULL_PARAMS_JSON:" in response:
            json_start = response.find("HULL_PARAMS_JSON:") + len("HULL_PARAMS_JSON:")
            json_text = response[json_start:].strip()
        else:
            # Try to find JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find raw JSON with hull_type
                json_match = re.search(r'\{[^{}]*"hull_type"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    return None

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    def _read_mission(self) -> Optional[Dict[str, Any]]:
        """Read mission requirements from memory."""
        return self.memory.read("mission")

    def design_hull(self, mission_data: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Design hull parameters based on mission requirements.

        Args:
            mission_data: Optional mission data, will read from memory if not provided

        Returns:
            AgentResponse with hull parameters proposal
        """
        # Read mission if not provided
        if mission_data is None:
            mission_data = self._read_mission()

        if mission_data is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No mission data found. Director must create mission first.",
                confidence=0.0,
                concerns=["Mission not defined"],
            )

        # Build prompt with mission context
        prompt = f"""The mission requirements are:

---
{json.dumps(mission_data, indent=2)}
---

Please design hull parameters that meet these mission requirements.
Include your reasoning, then provide the hull parameters JSON with HULL_PARAMS_JSON: marker.
"""

        # Generate response from LLM
        try:
            response_text = self.generate(prompt)
        except ConnectionError:
            # Fallback for when LLM is not available
            return self._fallback_design(mission_data)

        # Extract JSON from response
        hull_data = self._extract_json_from_response(response_text)

        if hull_data is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="Failed to parse hull parameters from response",
                confidence=0.0,
                reasoning=response_text,
                concerns=["Could not extract structured hull data"],
            )

        # Validate and enrich
        return self._validate_and_save(hull_data, response_text)

    def _fallback_design(self, mission_data: Dict[str, Any]) -> AgentResponse:
        """
        Fallback design when LLM is not available.

        Uses heuristics based on mission requirements.
        """
        # Extract mission parameters (handle both ALPHA and BRAVO schema formats)
        speed = mission_data.get("speed_max_kts") or mission_data.get("design_speed_kts", 30)
        range_nm = mission_data.get("range_nm") or mission_data.get("endurance_nm", 1000)
        payload = mission_data.get("payload_kg", 10000)
        sea_state = mission_data.get("sea_state_operational", 5)

        # Heuristic sizing based on range and payload
        # Rough estimate: ~100 tonnes displacement per 5000 NM range at cruise
        base_displacement = max(100, range_nm / 50 + payload / 500)

        # Length from displacement (Cb * L * B * T = displacement / density)
        # Assume L/B ~ 6, B/T ~ 3, Cb ~ 0.45
        volume = base_displacement / 1.025  # m³
        length_wl = (volume / 0.45 / 0.167 / 0.5) ** (1/3) * 6  # L = 6 * (V/(Cb*L/B/B*T/B))^1/3
        length_wl = max(20, min(100, length_wl))  # Clamp to reasonable range

        # Derive other dimensions
        length_overall = length_wl * 1.05
        beam = length_wl / 6  # L/B = 6
        draft = beam / 3  # B/T = 3
        depth = draft * 2.2  # D/T = 2.2

        # Form coefficients based on speed
        if speed > 35:
            cb = 0.40
            cp = 0.62
        elif speed > 25:
            cb = 0.45
            cp = 0.65
        else:
            cb = 0.50
            cp = 0.68

        cm = cb / cp  # Cb = Cp * Cm
        cwp = 0.75  # Typical

        # Select hull type
        if sea_state >= 7 or payload > 50000:
            hull_type = "catamaran"
            beam = length_wl / 4  # Wider for catamaran
        elif speed > 40:
            hull_type = "planing"
        elif speed > 25:
            hull_type = "semi_displacement"
        else:
            hull_type = "displacement"

        hull_data = {
            "hull_type": hull_type,
            "length_overall": round(length_overall, 1),
            "length_waterline": round(length_wl, 1),
            "beam": round(beam, 1),
            "draft": round(draft, 2),
            "depth": round(depth, 2),
            "block_coefficient": round(cb, 3),
            "prismatic_coefficient": round(cp, 3),
            "midship_coefficient": round(cm, 3),
            "waterplane_coefficient": round(cwp, 3),
            "lcb_position": 0.52,
        }

        return self._validate_and_save(
            hull_data,
            "Fallback design using heuristics (LLM unavailable)",
            is_fallback=True
        )

    def _validate_and_save(
        self,
        hull_data: Dict[str, Any],
        reasoning: str,
        is_fallback: bool = False
    ) -> AgentResponse:
        """
        Validate hull parameters and save to memory.

        Args:
            hull_data: Hull parameters dictionary
            reasoning: Reasoning text from LLM or fallback
            is_fallback: Whether this is a fallback design

        Returns:
            AgentResponse with validation results
        """
        concerns = []

        # Validate with ALPHA's schema if available
        if ALPHA_AVAILABLE and HullParamsSchema:
            try:
                hull = HullParamsSchema(**hull_data)

                # Calculate hydrostatics
                displacement = calculate_displacement(
                    hull.length_waterline,
                    hull.beam,
                    hull.draft,
                    hull.block_coefficient
                )
                wetted_surface = calculate_wetted_surface_holtrop(
                    hull.length_waterline,
                    hull.beam,
                    hull.draft,
                    hull.block_coefficient,
                    hull.midship_coefficient,
                    hull.waterplane_coefficient
                )

                # Add calculated values
                hull_data["displacement_tonnes"] = round(displacement, 1)
                hull_data["wetted_surface_m2"] = round(wetted_surface, 1)

                # Validate with constraints
                if self.constraints:
                    validation = self.constraints.validate(hull)
                    if not validation.is_valid:
                        concerns.extend(validation.errors)
                    if validation.warnings:
                        concerns.extend([f"Warning: {w}" for w in validation.warnings])

            except Exception as e:
                concerns.append(f"Schema validation error: {e}")
        else:
            # Basic validation without ALPHA
            concerns.append("ALPHA physics not available - using basic validation")

            # Check coefficient consistency
            cb = hull_data.get("block_coefficient", 0)
            cp = hull_data.get("prismatic_coefficient", 0)
            cm = hull_data.get("midship_coefficient", 0)

            expected_cb = cp * cm
            if abs(cb - expected_cb) > 0.02:
                concerns.append(f"Coefficient inconsistency: Cb={cb} but Cp*Cm={expected_cb:.3f}")

        # Write to memory (using BRAVO's memory system)
        self.memory.write("hull_params", hull_data, validate=False)

        # Update system state
        self.memory.update_system_state(
            current_phase=DesignPhase.HULL_FORM,
            status="hull_proposed" if not is_fallback else "hull_proposed_fallback",
        )

        # Log decision
        self.log_decision({
            "action": "hull_proposed",
            "proposal_id": self._generate_proposal_id(),
            "parameters": hull_data,
            "is_fallback": is_fallback,
        })

        confidence = 0.5 if is_fallback else 0.8
        if concerns:
            confidence -= 0.1 * min(len(concerns), 3)

        return AgentResponse(
            agent_id=self.agent_id,
            content=f"Hull parameters proposed: {hull_data.get('hull_type', 'unknown')} "
                   f"{hull_data.get('length_overall', 0):.1f}m LOA",
            confidence=max(0.1, confidence),
            reasoning=reasoning,
            proposals=[hull_data],
            concerns=concerns,
            metadata={
                "displacement_tonnes": hull_data.get("displacement_tonnes"),
                "wetted_surface_m2": hull_data.get("wetted_surface_m2"),
            },
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Optional mission data or empty to read from memory

        Returns:
            AgentResponse with hull design proposal
        """
        mission_data = input_data.get("mission") if input_data else None
        return self.design_hull(mission_data)


# Convenience function
def create_naval_architect(memory_path: str = "memory", **kwargs) -> NavalArchitectAgent:
    """Create a Naval Architect agent instance."""
    return NavalArchitectAgent(memory_path=memory_path, **kwargs)
