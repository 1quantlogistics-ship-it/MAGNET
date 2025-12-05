"""
MAGNET V1 Mission Schema (ALPHA)

Defines mission requirements for naval vessel design.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class MissionType(str, Enum):
    """Types of missions the vessel can perform."""
    ISR = "isr"                     # Intelligence, Surveillance, Reconnaissance
    MCM = "mcm"                     # Mine Countermeasures
    ASW = "asw"                     # Anti-Submarine Warfare
    LOGISTICS = "logistics"         # Contested logistics / supply
    COMMS_RELAY = "comms_relay"    # Communications relay
    MISSILE_DEFENSE = "missile_defense"  # Missile tracking/defense
    UAV_MOTHERSHIP = "uav_mothership"    # UAV/UUV/USV mothership


class OperatingEnvironment(str, Enum):
    """Operating environment classification."""
    LITTORAL = "littoral"           # Coastal/near-shore
    OPEN_OCEAN = "open_ocean"       # Blue water
    ARCTIC = "arctic"               # Ice-capable
    TROPICAL = "tropical"           # Warm water operations


class MissionSchema(BaseModel):
    """
    Mission requirements schema for naval vessel design.

    This schema captures the operational requirements that drive
    the vessel design, including performance targets, payload
    requirements, and environmental constraints.
    """

    # Identification
    mission_id: str = Field(..., description="Unique mission identifier")
    mission_name: Optional[str] = Field(None, description="Human-readable mission name")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Mission types (vessel may support multiple)
    mission_types: List[MissionType] = Field(
        ...,
        min_length=1,
        description="List of mission types the vessel must support"
    )

    # Performance requirements
    range_nm: float = Field(
        ...,
        ge=100,
        le=20000,
        description="Required range in nautical miles"
    )
    speed_max_kts: float = Field(
        ...,
        ge=5,
        le=60,
        description="Maximum speed in knots"
    )
    speed_cruise_kts: float = Field(
        ...,
        ge=5,
        le=40,
        description="Cruise speed in knots"
    )
    endurance_days: float = Field(
        ...,
        ge=1,
        le=180,
        description="Endurance at cruise speed in days"
    )

    # Payload requirements
    payload_kg: float = Field(
        ...,
        ge=0,
        le=500000,
        description="Required payload capacity in kg"
    )
    payload_volume_m3: Optional[float] = Field(
        None,
        ge=0,
        description="Required payload volume in cubic meters"
    )

    # Environmental requirements
    sea_state_operational: int = Field(
        ...,
        ge=1,
        le=9,
        description="Maximum sea state for full operations (1-9)"
    )
    sea_state_survival: int = Field(
        default=9,
        ge=1,
        le=9,
        description="Maximum sea state for survival (1-9)"
    )
    operating_environment: OperatingEnvironment = Field(
        default=OperatingEnvironment.OPEN_OCEAN,
        description="Primary operating environment"
    )

    # Autonomy level (for unmanned vessels)
    autonomy_level: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Autonomy level (0=crewed, 5=fully autonomous)"
    )

    # Additional constraints
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional mission-specific constraints"
    )

    # Priority weighting for optimization
    priority_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights for optimization objectives (e.g., {'speed': 0.3, 'range': 0.5, 'payload': 0.2})"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mission_id": "M48-ISR-001",
                "mission_name": "Pacific ISR Platform",
                "mission_types": ["isr", "comms_relay"],
                "range_nm": 15000,
                "speed_max_kts": 30,
                "speed_cruise_kts": 18,
                "endurance_days": 60,
                "payload_kg": 50000,
                "sea_state_operational": 5,
                "sea_state_survival": 9,
                "operating_environment": "open_ocean",
                "autonomy_level": 3
            }
        }
