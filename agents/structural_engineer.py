"""
MAGNET Structural Engineer Agent
=================================

The Structural Engineer agent designs scantlings based on hull parameters
and classification requirements.

Responsibilities:
- Read hull_params from memory
- Calculate design pressures for all zones
- Generate plating schedule per ABS HSNC 2023
- Select stiffener profiles
- Write structural_design.json to memory

Communication Flow (from Operations Guide):
1. Naval Architect writes hull_params.json with dimensions
2. Orchestrator triggers Structural Engineer
3. Structural Engineer proposes scantling design -> structural_design.json
4. Class Reviewer validates against ABS/DNV requirements
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase

# Import ALPHA's structural module
try:
    from physics.structural.materials import (
        AluminumAlloy,
        get_alloy_properties,
        DEFAULT_ALLOY,
        ALLOWED_ALLOYS,
    )
    from physics.structural.pressure import (
        PressureZone,
        PressureResult,
        calculate_all_zone_pressures,
    )
    from physics.structural.plating import (
        PlatingSchedule,
        generate_plating_schedule,
    )
    from physics.structural.stiffeners import (
        StiffenerResult,
        calculate_frame_spacing,
        calculate_all_stiffeners,
    )
    ALPHA_STRUCTURAL_AVAILABLE = True
except ImportError:
    ALPHA_STRUCTURAL_AVAILABLE = False


# Default spacing values (mm)
DEFAULT_STIFFENER_SPACING = 400  # mm
DEFAULT_FRAME_SPACING = 500  # mm


class StructuralEngineerAgent(BaseAgent):
    """
    Structural Engineer Agent - Scantling Design.

    Calculates structural requirements per ABS HSNC 2023:
    - Design pressures by zone
    - Plate thickness schedule
    - Stiffener sizing and selection
    - Frame spacing recommendations
    """

    STRUCTURAL_PROMPT = """You are the Structural Engineer Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to design structural scantlings based on hull parameters and classification requirements.

## Your Responsibilities:
1. Read hull parameters from memory
2. Calculate design pressures for all structural zones
3. Determine plate thicknesses per ABS HSNC 2023
4. Select stiffener profiles for each zone
5. Calculate frame spacing
6. Verify compliance with classification rules
7. Write structural_design.json to memory

## Input Context:
You will receive:
- Hull parameters (dimensions, displacement)
- Mission requirements (speed, service type)
- Classification requirements (ABS HSNC 2023)

## Output Format:
Respond with reasoning followed by JSON with STRUCTURAL_JSON: marker.

Example output:
```
Based on the hull parameters and ABS HSNC 2023 requirements:
- Design pressure (bottom forward): 85.2 kN/m²
- Bottom plating: 8.0 mm 5083-H116
- Side plating: 6.0 mm 5083-H116
- Stiffeners: L 100x75x8 @ 400mm spacing

STRUCTURAL_JSON:
{
  "material": "5083-H116",
  "frame_spacing_mm": 500,
  "stiffener_spacing_mm": 400,
  "plating": {
    "bottom_forward": {"thickness_mm": 8.0, "pressure_kPa": 85.2},
    "bottom_midship": {"thickness_mm": 7.0, "pressure_kPa": 65.0},
    "side_midship": {"thickness_mm": 6.0, "pressure_kPa": 32.5}
  },
  "stiffeners": {
    "bottom": "L 100x75x8",
    "side": "L 75x75x6"
  }
}
```

## Design Guidelines:

### Material Selection:
- Primary structure: 5083-H116 or 5456-H116 (marine grade)
- NEVER use 6xxx series alloys (severe HAZ degradation)
- Always design for HAZ (heat-affected zone) strength

### Plate Thickness:
- ABS formula: t = s × √(p × k / σ_a) + t_c
- Minimum 4.0mm for primary structure
- Quantize to commercial sizes (4, 5, 6, 7, 8, 9, 10mm...)

### Stiffener Selection:
- Section modulus: SM = (p × s × l²) / (C × σ_a)
- Use standard profiles (angles, flat bars, tees)
- Height limited by clearance requirements
"""

    def __init__(
        self,
        agent_id: str = "structural_engineer_001",
        memory_path: str = "memory",
        alloy: AluminumAlloy = None,
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="structural_engineer",
            memory_path=memory_path,
            **kwargs
        )
        self.alloy = alloy or (DEFAULT_ALLOY if ALPHA_STRUCTURAL_AVAILABLE else None)

    @property
    def system_prompt(self) -> str:
        return self.STRUCTURAL_PROMPT

    def _read_design_data(self) -> tuple[Optional[Dict], Optional[Dict]]:
        """Read hull_params and mission from memory."""
        hull_params = self.memory.read("hull_params")
        mission = self.memory.read("mission")
        return hull_params, mission

    def _get_service_type(self, mission: Optional[Dict]) -> str:
        """Determine ABS service type from mission."""
        if mission is None:
            return "workboat"

        vessel_type = mission.get("vessel_type", "").lower()

        if "patrol" in vessel_type or "military" in vessel_type:
            return "patrol_vessel"
        elif "ferry" in vessel_type or "passenger" in vessel_type:
            return "passenger_ferry"
        elif "cargo" in vessel_type or "freight" in vessel_type:
            return "cargo_vessel"
        elif "crew" in vessel_type:
            return "crew_boat"
        elif "yacht" in vessel_type:
            return "yacht"
        else:
            return "workboat"

    def _calculate_zone_pressures(
        self,
        hull_params: Dict[str, Any],
        mission: Optional[Dict[str, Any]],
    ) -> Dict[PressureZone, PressureResult]:
        """Calculate design pressures for all zones."""
        if not ALPHA_STRUCTURAL_AVAILABLE:
            return {}

        # Extract hull dimensions
        length_wl = hull_params.get("length_waterline", hull_params.get("length_overall", 40.0) * 0.93)
        beam = hull_params.get("beam", 10.0)
        draft = hull_params.get("draft", 2.0)
        depth = hull_params.get("depth", 4.0)
        displacement = hull_params.get("displacement_tonnes", 150)

        # Get speed and service type
        design_speed = 25.0
        if mission:
            design_speed = mission.get("design_speed_kts") or mission.get("speed_max_kts", 25.0)

        service_type = self._get_service_type(mission)

        # Get deadrise angle (estimate if not provided)
        deadrise = hull_params.get("deadrise_angle", 15.0)

        # Calculate pressures for all zones
        pressures = calculate_all_zone_pressures(
            displacement=displacement,
            length_wl=length_wl,
            beam=beam,
            draft=draft,
            depth=depth,
            speed_kts=design_speed,
            deadrise_angle=deadrise,
            service_type=service_type,
        )

        return pressures

    def _generate_plating_schedule(
        self,
        pressures: Dict[PressureZone, PressureResult],
        hull_params: Dict[str, Any],
        stiffener_spacing: float,
        frame_spacing: float,
    ) -> Optional[PlatingSchedule]:
        """Generate plating schedule for all zones."""
        if not ALPHA_STRUCTURAL_AVAILABLE or not pressures:
            return None

        length_wl = hull_params.get("length_waterline", hull_params.get("length_overall", 40.0) * 0.93)
        beam = hull_params.get("beam", 10.0)
        depth = hull_params.get("depth", 4.0)

        schedule = generate_plating_schedule(
            pressure_results=pressures,
            stiffener_spacing=stiffener_spacing,
            frame_spacing=frame_spacing,
            length_wl=length_wl,
            beam=beam,
            depth=depth,
            alloy=self.alloy,
        )

        return schedule

    def _calculate_stiffeners(
        self,
        pressures: Dict[PressureZone, PressureResult],
        stiffener_spacing: float,
        frame_spacing: float,
    ) -> Dict[PressureZone, StiffenerResult]:
        """Calculate stiffener requirements for all zones."""
        if not ALPHA_STRUCTURAL_AVAILABLE or not pressures:
            return {}

        stiffeners = calculate_all_stiffeners(
            pressure_results=pressures,
            stiffener_spacing=stiffener_spacing,
            frame_spacing=frame_spacing,
            alloy=self.alloy,
        )

        return stiffeners

    def _plating_result_to_dict(self, result) -> Dict[str, Any]:
        """Convert PlatingResult to serializable dict."""
        return {
            "zone": result.zone,
            "required_thickness_mm": round(result.required_thickness, 2),
            "minimum_thickness_mm": round(result.minimum_thickness, 1),
            "proposed_thickness_mm": result.proposed_thickness,
            "is_compliant": result.is_compliant,
            "margin_percent": round(result.margin_percent, 1),
            "design_pressure_kPa": round(result.design_pressure, 1),
            "stiffener_spacing_mm": result.stiffener_spacing,
            "allowable_stress_MPa": round(result.allowable_stress, 1),
            "alloy": result.alloy,
            "in_haz": result.in_haz,
            "rule_reference": result.rule_reference,
        }

    def _stiffener_result_to_dict(self, result: StiffenerResult) -> Dict[str, Any]:
        """Convert StiffenerResult to serializable dict."""
        profile_data = None
        if result.selected_profile:
            profile_data = {
                "type": result.selected_profile.type.value,
                "designation": result.selected_profile.designation,
                "height_mm": result.selected_profile.height,
                "width_mm": result.selected_profile.width,
                "section_modulus_cm3": result.selected_profile.section_modulus,
                "weight_kg_per_m": result.selected_profile.weight_per_meter,
            }

        return {
            "zone": result.zone,
            "required_section_modulus_cm3": round(result.required_section_modulus, 2),
            "actual_section_modulus_cm3": round(result.actual_section_modulus, 2),
            "selected_profile": profile_data,
            "is_compliant": result.is_compliant,
            "margin_percent": round(result.margin_percent, 1),
            "design_pressure_kPa": round(result.design_pressure, 1),
            "stiffener_spacing_mm": result.stiffener_spacing,
            "frame_spacing_mm": result.frame_spacing,
            "alloy": result.alloy,
            "rule_reference": result.rule_reference,
        }

    def design_structure(
        self,
        hull_params: Optional[Dict[str, Any]] = None,
        mission: Optional[Dict[str, Any]] = None,
        stiffener_spacing: float = DEFAULT_STIFFENER_SPACING,
        frame_spacing: float = DEFAULT_FRAME_SPACING,
    ) -> AgentResponse:
        """
        Design structural scantlings based on hull and mission.

        Args:
            hull_params: Hull parameters (reads from memory if not provided)
            mission: Mission data (reads from memory if not provided)
            stiffener_spacing: Stiffener spacing in mm
            frame_spacing: Frame spacing in mm

        Returns:
            AgentResponse with structural design
        """
        # Check ALPHA module availability
        if not ALPHA_STRUCTURAL_AVAILABLE:
            return AgentResponse(
                agent_id=self.agent_id,
                content="ALPHA structural module not available. Cannot design scantlings.",
                confidence=0.0,
                concerns=["physics.structural module not found"],
            )

        # Read from memory if not provided
        if hull_params is None or mission is None:
            stored_hull, stored_mission = self._read_design_data()
            hull_params = hull_params or stored_hull
            mission = mission or stored_mission

        # Check prerequisites
        if hull_params is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No hull parameters found. Naval Architect must design hull first.",
                confidence=0.0,
                concerns=["Hull parameters not defined"],
            )

        concerns = []

        # Calculate optimal frame spacing if we have enough data
        length_wl = hull_params.get("length_waterline", hull_params.get("length_overall", 40.0) * 0.93)
        beam = hull_params.get("beam", 10.0)
        draft = hull_params.get("draft", 2.0)
        design_speed = 25.0
        if mission:
            design_speed = mission.get("design_speed_kts") or mission.get("speed_max_kts", 25.0)

        # Get recommended frame spacing
        recommended_frame_spacing = calculate_frame_spacing(
            length_wl=length_wl,
            beam=beam,
            draft=draft,
            speed_kts=design_speed,
        )

        # Use recommended spacing if different from default
        if abs(recommended_frame_spacing - frame_spacing) > 50:
            frame_spacing = recommended_frame_spacing

        # Step 1: Calculate design pressures
        pressures = self._calculate_zone_pressures(hull_params, mission)

        if not pressures:
            return AgentResponse(
                agent_id=self.agent_id,
                content="Failed to calculate design pressures.",
                confidence=0.0,
                concerns=["Pressure calculation failed"],
            )

        # Step 2: Generate plating schedule
        plating_schedule = self._generate_plating_schedule(
            pressures, hull_params, stiffener_spacing, frame_spacing
        )

        if plating_schedule is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="Failed to generate plating schedule.",
                confidence=0.0,
                concerns=["Plating calculation failed"],
            )

        # Step 3: Calculate stiffeners
        stiffeners = self._calculate_stiffeners(pressures, stiffener_spacing, frame_spacing)

        # Check compliance
        non_compliant_plates = []
        non_compliant_stiffeners = []

        for zone_name, result in plating_schedule.zones.items():
            if not result.is_compliant:
                non_compliant_plates.append(zone_name)

        for zone, result in stiffeners.items():
            if not result.is_compliant:
                non_compliant_stiffeners.append(zone.value)

        if non_compliant_plates:
            concerns.append(f"Non-compliant plating in zones: {non_compliant_plates}")

        if non_compliant_stiffeners:
            concerns.append(f"Non-compliant stiffeners in zones: {non_compliant_stiffeners}")

        # Build structural design output
        plating_data = {}
        for zone_name, result in plating_schedule.zones.items():
            plating_data[zone_name] = self._plating_result_to_dict(result)

        stiffener_data = {}
        for zone, result in stiffeners.items():
            stiffener_data[zone.value] = self._stiffener_result_to_dict(result)

        # Get material properties for summary
        material_props = get_alloy_properties(self.alloy)

        structural_design = {
            "material": {
                "alloy": self.alloy.value,
                "yield_strength_MPa": material_props.yield_strength,
                "haz_yield_strength_MPa": material_props.haz_yield_strength,
                "haz_factor": material_props.haz_factor,
                "density_kg_m3": material_props.density,
            },
            "spacing": {
                "stiffener_spacing_mm": stiffener_spacing,
                "frame_spacing_mm": frame_spacing,
            },
            "plating": plating_data,
            "stiffeners": stiffener_data,
            "summary": {
                "bottom_thickness_mm": plating_schedule.bottom_thickness,
                "side_thickness_mm": plating_schedule.side_thickness,
                "deck_thickness_mm": plating_schedule.deck_thickness,
                "average_thickness_mm": round(plating_schedule.average_thickness, 1),
                "estimated_plate_weight_kg": round(plating_schedule.total_plate_weight, 0),
                "all_plating_compliant": len(non_compliant_plates) == 0,
                "all_stiffeners_compliant": len(non_compliant_stiffeners) == 0,
            },
            "rule_reference": "ABS HSNC 2023 Part 3, Chapter 3",
            "proposed_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Write to memory
        self.memory.write("structural_design", structural_design, validate=False)

        # Update system state
        self.memory.update_system_state(
            current_phase=DesignPhase.STRUCTURE,
            status="structure_proposed",
        )

        # Log decision
        self.log_decision({
            "action": "structure_proposed",
            "alloy": self.alloy.value,
            "bottom_thickness_mm": plating_schedule.bottom_thickness,
            "side_thickness_mm": plating_schedule.side_thickness,
            "plate_weight_kg": round(plating_schedule.total_plate_weight, 0),
            "zones_calculated": len(plating_data),
        })

        # Calculate confidence
        confidence = 0.85
        if concerns:
            confidence -= 0.15 * min(len(concerns), 3)

        # Build response content
        content = (
            f"Structural: {self.alloy.value} | "
            f"Bottom={plating_schedule.bottom_thickness}mm, Side={plating_schedule.side_thickness}mm | "
            f"Frames @ {frame_spacing}mm | "
            f"Plate wt={plating_schedule.total_plate_weight/1000:.1f}t"
        )

        return AgentResponse(
            agent_id=self.agent_id,
            content=content,
            confidence=max(0.1, confidence),
            reasoning=f"Designed per ABS HSNC 2023 with {self.alloy.value} alloy",
            proposals=[structural_design],
            concerns=concerns,
            metadata={
                "alloy": self.alloy.value,
                "bottom_thickness_mm": plating_schedule.bottom_thickness,
                "side_thickness_mm": plating_schedule.side_thickness,
                "deck_thickness_mm": plating_schedule.deck_thickness,
                "plate_weight_kg": round(plating_schedule.total_plate_weight, 0),
                "frame_spacing_mm": frame_spacing,
                "stiffener_spacing_mm": stiffener_spacing,
            },
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Optional hull_params/mission or empty to read from memory

        Returns:
            AgentResponse with structural design proposal
        """
        hull_params = input_data.get("hull_params") if input_data else None
        mission = input_data.get("mission") if input_data else None
        stiffener_spacing = input_data.get("stiffener_spacing", DEFAULT_STIFFENER_SPACING) if input_data else DEFAULT_STIFFENER_SPACING
        frame_spacing = input_data.get("frame_spacing", DEFAULT_FRAME_SPACING) if input_data else DEFAULT_FRAME_SPACING

        return self.design_structure(
            hull_params=hull_params,
            mission=mission,
            stiffener_spacing=stiffener_spacing,
            frame_spacing=frame_spacing,
        )


# Convenience function
def create_structural_engineer(
    memory_path: str = "memory",
    alloy: AluminumAlloy = None,
    **kwargs
) -> StructuralEngineerAgent:
    """Create a Structural Engineer agent instance."""
    return StructuralEngineerAgent(memory_path=memory_path, alloy=alloy, **kwargs)
