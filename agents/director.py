"""
MAGNET Director Agent
=====================

The Director agent is the first point of contact for user requests.
It interprets natural language design requirements and creates the mission.json file.

Responsibilities:
- Parse user requirements into structured mission parameters
- Validate mission feasibility at high level
- Write mission.json to memory
- Trigger next phase (Naval Architect)

Communication Flow (from Operations Guide):
1. User submits design request via chat interface
2. Orchestrator routes to Director agent for mission interpretation
3. Director writes mission.json and triggers Naval Architect
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import MissionSchema, DesignPhase


class DirectorAgent(BaseAgent):
    """
    Director Agent - Mission Interpretation.

    Parses natural language design requirements into structured mission parameters.
    First agent in the design spiral.
    """

    DIRECTOR_PROMPT = """You are the Director Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to interpret user design requirements and create structured mission specifications for naval vessels.

## Your Responsibilities:
1. Parse natural language descriptions of vessel requirements
2. Extract key parameters: vessel type, dimensions, speed, range, crew, payload
3. Identify classification requirements (ABS, DNV, etc.)
4. Identify military specifications if applicable
5. Create structured mission.json for the design team

## Output Format:
You must respond with a JSON object containing the mission parameters. Include your reasoning before the JSON.

Example output:
```
Based on the user's requirements for a fast patrol boat, I've extracted the following mission parameters:
- Vessel Type: Patrol catamaran for coastal operations
- Length: 22 meters based on stated requirements
- Speed: 35 knots design speed for pursuit capability
- Range: 500 nm for extended patrol missions

MISSION_JSON:
{
  "mission_id": "MAGNET-001",
  "vessel_type": "patrol_catamaran",
  "loa_m": 22.0,
  "beam_m": 8.5,
  "design_speed_kts": 35,
  "cruise_speed_kts": 25,
  "crew": 8,
  "endurance_nm": 500,
  "payload_kg": 5000,
  "classification": "ABS_HSNC",
  "constraints": {
    "max_draft_m": 1.8,
    "min_freeboard_m": 0.9
  }
}
```

## Key Parameters to Extract:
- mission_id: Generate as MAGNET-XXX
- vessel_type: catamaran, monohull, trimaran, etc.
- loa_m: Length overall in meters
- beam_m: Beam in meters
- design_speed_kts: Maximum design speed
- cruise_speed_kts: Economical cruise speed
- crew: Number of crew
- endurance_nm: Range in nautical miles
- payload_kg: Payload capacity
- classification: ABS_HSNC, DNV_HSLC, etc.
- military_spec: MIL-DTL-901E_GRADE_A, etc. (if applicable)
- constraints: Hard limits (max_draft, min_freeboard, etc.)

## Estimation Guidelines:
If user doesn't specify exact values, use naval architecture heuristics:
- Catamaran beam typically 40-50% of LOA
- Draft typically 5-8% of LOA
- Cruise speed typically 70% of design speed
- Crew scales with vessel size and mission

Be conservative in estimates. Flag uncertainty in your reasoning.
"""

    def __init__(
        self,
        agent_id: str = "director_001",
        memory_path: str = "memory",
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="director",
            memory_path=memory_path,
            **kwargs
        )
        self._mission_counter = 0

    @property
    def system_prompt(self) -> str:
        return self.DIRECTOR_PROMPT

    def _generate_mission_id(self) -> str:
        """Generate unique mission ID."""
        self._mission_counter += 1
        return f"MAGNET-{self._mission_counter:03d}"

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.

        Looks for MISSION_JSON: marker or code blocks.
        """
        # Try to find MISSION_JSON marker
        if "MISSION_JSON:" in response:
            json_start = response.find("MISSION_JSON:") + len("MISSION_JSON:")
            json_text = response[json_start:].strip()
        else:
            # Try to find JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{[^{}]*"mission_id"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    return None

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    def interpret_requirements(self, user_input: str) -> AgentResponse:
        """
        Interpret user requirements and create mission specification.

        Args:
            user_input: Natural language design requirements

        Returns:
            AgentResponse with mission parameters
        """
        # Build prompt with context
        prompt = f"""The user has submitted the following design requirements:

---
{user_input}
---

Please analyze these requirements and create a structured mission specification.
Include your reasoning, then provide the mission JSON with MISSION_JSON: marker.
"""

        # Generate response from LLM
        try:
            response_text = self.generate(prompt)
        except ConnectionError as e:
            # Fallback for when LLM is not available
            return self._fallback_interpretation(user_input)

        # Extract JSON from response
        mission_data = self._extract_json_from_response(response_text)

        if mission_data is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="Failed to parse mission parameters from response",
                confidence=0.0,
                reasoning=response_text,
                concerns=["Could not extract structured mission data"],
            )

        # Ensure mission_id exists
        if "mission_id" not in mission_data:
            mission_data["mission_id"] = self._generate_mission_id()

        # Validate against schema
        try:
            mission = MissionSchema(**mission_data)
        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                content=f"Mission parameters failed validation: {e}",
                confidence=0.3,
                reasoning=response_text,
                concerns=[str(e)],
            )

        # Write to memory
        self.memory.write_schema("mission", mission)

        # Update system state
        self.memory.update_system_state(
            current_phase=DesignPhase.MISSION,
            status="mission_defined",
        )

        # Log decision
        self.log_decision({
            "action": "mission_created",
            "mission_id": mission.mission_id,
            "parameters": mission_data,
        })

        return AgentResponse(
            agent_id=self.agent_id,
            content=f"Mission {mission.mission_id} created successfully",
            confidence=0.85,
            reasoning=response_text,
            proposals=[mission_data],
            metadata={"mission_id": mission.mission_id},
        )

    def _fallback_interpretation(self, user_input: str) -> AgentResponse:
        """
        Fallback interpretation when LLM is not available.

        Uses simple pattern matching for basic extraction.
        """
        # Simple pattern matching for common parameters
        mission_data = {
            "mission_id": self._generate_mission_id(),
            "vessel_type": "patrol_catamaran",
            "loa_m": 22.0,
            "beam_m": 8.5,
            "design_speed_kts": 30.0,
            "cruise_speed_kts": 20.0,
            "crew": 6,
            "endurance_nm": 300,
            "payload_kg": 3000,
            "constraints": {},
        }

        # Extract numbers from input
        length_match = re.search(r'(\d+)\s*(?:m|meter)', user_input.lower())
        if length_match:
            mission_data["loa_m"] = float(length_match.group(1))
            mission_data["beam_m"] = mission_data["loa_m"] * 0.4  # Heuristic

        speed_match = re.search(r'(\d+)\s*(?:kt|knot)', user_input.lower())
        if speed_match:
            mission_data["design_speed_kts"] = float(speed_match.group(1))
            mission_data["cruise_speed_kts"] = mission_data["design_speed_kts"] * 0.7

        range_match = re.search(r'(\d+)\s*(?:nm|nmi|nautical)', user_input.lower())
        if range_match:
            mission_data["endurance_nm"] = float(range_match.group(1))

        # Detect vessel type
        if "catamaran" in user_input.lower():
            mission_data["vessel_type"] = "patrol_catamaran"
        elif "monohull" in user_input.lower():
            mission_data["vessel_type"] = "patrol_monohull"

        # Validate and save
        try:
            mission = MissionSchema(**mission_data)
            self.memory.write_schema("mission", mission)

            self.memory.update_system_state(
                current_phase=DesignPhase.MISSION,
                status="mission_defined_fallback",
            )

            return AgentResponse(
                agent_id=self.agent_id,
                content=f"Mission {mission.mission_id} created (fallback mode - LLM unavailable)",
                confidence=0.5,
                reasoning="Used pattern matching fallback due to LLM unavailability",
                proposals=[mission_data],
                concerns=["LLM was unavailable, used basic pattern matching"],
            )
        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                content=f"Failed to create mission: {e}",
                confidence=0.0,
                concerns=[str(e)],
            )

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Must contain 'user_input' key with requirements text

        Returns:
            AgentResponse with mission interpretation
        """
        user_input = input_data.get("user_input", "")

        if not user_input:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No user input provided",
                confidence=0.0,
                concerns=["Empty input"],
            )

        return self.interpret_requirements(user_input)


# Convenience function
def create_director(memory_path: str = "memory", **kwargs) -> DirectorAgent:
    """Create a Director agent instance."""
    return DirectorAgent(memory_path=memory_path, **kwargs)
