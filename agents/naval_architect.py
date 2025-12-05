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
    from physics.hydrostatics.stability import (
        calculate_stability,
        StabilityResult,
        generate_stability_report,
    )
    from physics.resistance import (
        calculate_total_resistance,
        ResistanceResult,
    )
    from physics.weight import (
        calculate_lightship_weight,
        LightshipResult,
        VesselCategory,
        PropulsionType,
    )
    from constraints.hull_form import HullFormConstraints
    ALPHA_AVAILABLE = True
    ALPHA_STABILITY_AVAILABLE = True
    ALPHA_RESISTANCE_AVAILABLE = True
    ALPHA_WEIGHT_AVAILABLE = True
except ImportError:
    ALPHA_AVAILABLE = False
    ALPHA_STABILITY_AVAILABLE = False
    ALPHA_RESISTANCE_AVAILABLE = False
    ALPHA_WEIGHT_AVAILABLE = False
    HullParamsSchema = None
    HullType = None
    StabilityResult = None
    ResistanceResult = None
    LightshipResult = None
    VesselCategory = None
    PropulsionType = None


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

        # Validate and enrich (pass mission_data for resistance calculation)
        return self._validate_and_save(hull_data, response_text, mission_data=mission_data)

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
            is_fallback=True,
            mission_data=mission_data
        )

    def _validate_and_save(
        self,
        hull_data: Dict[str, Any],
        reasoning: str,
        is_fallback: bool = False,
        mission_data: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Validate hull parameters and save to memory.

        Args:
            hull_data: Hull parameters dictionary
            reasoning: Reasoning text from LLM or fallback
            is_fallback: Whether this is a fallback design
            mission_data: Optional mission data for resistance calculation

        Returns:
            AgentResponse with validation results
        """
        concerns = []
        stability_data = None
        resistance_data = None
        weight_data = None

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

                # Calculate stability using ALPHA's stability module
                if ALPHA_STABILITY_AVAILABLE:
                    try:
                        stability_result = calculate_stability(
                            length_wl=hull.length_waterline,
                            beam=hull.beam,
                            draft=hull.draft,
                            depth=hull.depth,
                            block_coefficient=hull.block_coefficient,
                            waterplane_coefficient=hull.waterplane_coefficient,
                            hull_type=hull_data.get("hull_type", "displacement")
                        )

                        # Store stability results
                        stability_data = {
                            "GM": round(stability_result.GM, 3),
                            "KB": round(stability_result.KB, 3),
                            "KG": round(stability_result.KG, 3),
                            "BM": round(stability_result.BM, 3),
                            "KM": round(stability_result.KM, 3),
                            "max_GZ": round(stability_result.max_gz, 3),
                            "angle_max_GZ": round(stability_result.angle_max_gz, 1),
                            "range_positive_stability": round(stability_result.range_positive_stability, 1),
                            "imo_criteria_passed": stability_result.imo_criteria_passed,
                            "is_stable": stability_result.is_stable(),
                        }

                        # Add stability to hull_data for convenience
                        hull_data["stability"] = stability_data

                        # Write stability results to memory
                        self.memory.write("stability_results", stability_data, validate=False)

                        # Check stability
                        if not stability_result.is_stable():
                            concerns.append(f"STABILITY WARNING: GM={stability_result.GM:.3f}m, IMO criteria {'PASSED' if stability_result.imo_criteria_passed else 'FAILED'}")
                        elif stability_result.GM < 0.5:
                            concerns.append(f"Warning: Low GM ({stability_result.GM:.3f}m) - consider increasing beam or reducing KG")

                    except Exception as e:
                        concerns.append(f"Stability calculation error: {e}")

                # Calculate resistance at design speed using ALPHA's resistance module
                if ALPHA_RESISTANCE_AVAILABLE and mission_data:
                    try:
                        design_speed = mission_data.get("design_speed_kts") or mission_data.get("speed_max_kts", 25)

                        resistance_result = calculate_total_resistance(
                            speed_kts=design_speed,
                            length_wl=hull.length_waterline,
                            beam=hull.beam,
                            draft=hull.draft,
                            block_coefficient=hull.block_coefficient,
                            prismatic_coefficient=hull.prismatic_coefficient,
                            waterplane_coefficient=hull.waterplane_coefficient,
                            wetted_surface=wetted_surface
                        )

                        # Store resistance results
                        resistance_data = {
                            "design_speed_kts": design_speed,
                            "total_resistance_kN": round(resistance_result.total_resistance / 1000, 1),
                            "effective_power_kW": round(resistance_result.effective_power / 1000, 1),
                            "delivered_power_kW": round(resistance_result.delivered_power / 1000, 1),
                            "froude_number": round(resistance_result.froude_number, 3),
                        }

                        # Add to hull_data
                        hull_data["resistance"] = resistance_data

                        # Write resistance results to memory
                        self.memory.write("resistance_results", resistance_data, validate=False)

                    except Exception as e:
                        concerns.append(f"Resistance calculation error: {e}")

                # Calculate weight estimate using ALPHA's weight module
                if ALPHA_WEIGHT_AVAILABLE and resistance_data:
                    try:
                        # Get installed power from resistance calculation (with margin)
                        installed_power = resistance_data.get("delivered_power_kW", 0) * 1.15  # 15% margin

                        # Map hull type to vessel category
                        hull_type = hull_data.get("hull_type", "displacement")
                        vessel_category = VesselCategory.PATROL_MILITARY  # Default for MAGNET use case

                        # Get crew capacity from mission
                        crew_capacity = mission_data.get("crew", 10) if mission_data else 10

                        weight_result = calculate_lightship_weight(
                            length_bp=hull.length_waterline,
                            beam=hull.beam,
                            depth=hull.depth,
                            block_coefficient=hull.block_coefficient,
                            installed_power=installed_power,
                            vessel_category=vessel_category,
                            propulsion_type=PropulsionType.DIESEL_MECHANICAL,
                            crew_capacity=crew_capacity,
                            design_margin=0.05,
                            has_superstructure=True,
                        )

                        # Store weight results
                        weight_data = {
                            "lightship_weight_tonnes": round(weight_result.total_lightship, 1),
                            "hull_steel_weight_tonnes": round(weight_result.hull_steel_weight, 1),
                            "machinery_weight_tonnes": round(weight_result.machinery_weight, 1),
                            "outfit_weight_tonnes": round(weight_result.outfit_weight, 1),
                            "design_margin_tonnes": round(weight_result.margin_weight, 1),
                            "kg_lightship_m": round(weight_result.kg_lightship, 2),
                            "lcg_lightship_m": round(weight_result.lcg_lightship, 2),
                            "installed_power_kW": round(installed_power, 0),
                            "method": weight_result.method,
                            "vessel_category": weight_result.vessel_category,
                        }

                        # Add to hull_data
                        hull_data["weight"] = weight_data

                        # Write weight estimate to memory
                        self.memory.write("weight_estimate", weight_data, validate=False)

                        # Check weight vs displacement
                        displacement = hull_data.get("displacement_tonnes", 0)
                        if displacement > 0:
                            weight_ratio = weight_result.total_lightship / displacement
                            if weight_ratio > 0.75:
                                concerns.append(f"Warning: Lightship {weight_result.total_lightship:.0f}t is {weight_ratio*100:.0f}% of displacement - limited deadweight capacity")

                    except Exception as e:
                        concerns.append(f"Weight calculation error: {e}")

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
            "stability": stability_data,
            "resistance": resistance_data,
            "weight": weight_data,
            "is_fallback": is_fallback,
        })

        confidence = 0.5 if is_fallback else 0.8
        if concerns:
            confidence -= 0.1 * min(len(concerns), 3)

        # Build response content with stability/resistance/weight info
        content_parts = [
            f"Hull parameters proposed: {hull_data.get('hull_type', 'unknown')} "
            f"{hull_data.get('length_overall', 0):.1f}m LOA"
        ]
        if stability_data:
            content_parts.append(f"GM={stability_data['GM']:.3f}m, IMO {'✓' if stability_data['imo_criteria_passed'] else '✗'}")
        if resistance_data:
            content_parts.append(f"Power={resistance_data['delivered_power_kW']:.0f}kW @ {resistance_data['design_speed_kts']}kts")
        if weight_data:
            content_parts.append(f"Lightship={weight_data['lightship_weight_tonnes']:.0f}t")

        return AgentResponse(
            agent_id=self.agent_id,
            content=" | ".join(content_parts),
            confidence=max(0.1, confidence),
            reasoning=reasoning,
            proposals=[hull_data],
            concerns=concerns,
            metadata={
                "displacement_tonnes": hull_data.get("displacement_tonnes"),
                "wetted_surface_m2": hull_data.get("wetted_surface_m2"),
                "stability": stability_data,
                "resistance": resistance_data,
                "weight": weight_data,
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
