"""
performance/envelope_generator.py - Operational envelope generation
BRAVO OWNS THIS FILE.

Section 40: Operational Envelope - v1.1 with standardized fields
"""

from typing import Dict, Any, List, TYPE_CHECKING

from .envelope import OperationalEnvelope, OperationalLimit, SpeedSeaStatePoint

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


SEA_STATE_HS = {0: 0, 1: 0.1, 2: 0.5, 3: 1.25, 4: 2.5, 5: 4.0, 6: 6.0}


class EnvelopeGenerator:
    """Generate operational envelope - v1.1."""

    def __init__(self, state: 'StateManager'):
        self.state = state

    def generate(self) -> OperationalEnvelope:
        envelope = OperationalEnvelope(
            envelope_id=f"ENV-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        envelope.limits = self._collect_limits()
        envelope.speed_sea_state = self._generate_speed_sea_state()

        # v1.1 FIX: Use canonical _kts with fallback
        cruise_speed = self.state.get("mission.cruise_speed_kts", 0)
        if cruise_speed is None or cruise_speed <= 0:
            cruise_speed = self.state.get("mission.cruise_speed_knots", 25)

        envelope.design_speed_kts = cruise_speed
        envelope.design_sea_state = 3
        envelope.max_operational_sea_state = self.state.get("analysis.max_sea_state", 4) or 4

        envelope.endurance_at_cruise_hr = self._calculate_endurance()
        envelope.range_at_cruise_nm = self._calculate_range()

        return envelope

    def _collect_limits(self) -> List[OperationalLimit]:
        limits = []

        # v1.1 FIX: Use canonical _kts with fallback
        max_speed = self.state.get("mission.max_speed_kts", 0)
        if max_speed is None or max_speed <= 0:
            max_speed = self.state.get("mission.max_speed_knots", 35)

        limits.append(OperationalLimit(
            limit_id="LIM-SPEED-MAX", limit_type="speed",
            value=max_speed, unit="kts", source="design",
        ))

        max_ss = self.state.get("analysis.max_sea_state", 4) or 4
        limits.append(OperationalLimit(
            limit_id="LIM-SS-MAX", limit_type="sea_state",
            value=max_ss, unit="SS", source="seakeeping",
        ))

        range_nm = self.state.get("fuel.range_at_cruise_nm", 500) or 500
        limits.append(OperationalLimit(
            limit_id="LIM-RANGE", limit_type="range",
            value=range_nm, unit="nm", source="design",
        ))

        limits.append(OperationalLimit(
            limit_id="LIM-WIND", limit_type="wind",
            value=25, unit="kts", source="regulatory",
        ))

        return limits

    def _generate_speed_sea_state(self) -> List[SpeedSeaStatePoint]:
        points = []

        # v1.1 FIX: Use canonical _kts with fallback
        max_speed = self.state.get("mission.max_speed_kts", 0)
        if max_speed is None or max_speed <= 0:
            max_speed = self.state.get("mission.max_speed_knots", 35)

        cruise_speed = self.state.get("mission.cruise_speed_kts", 0)
        if cruise_speed is None or cruise_speed <= 0:
            cruise_speed = self.state.get("mission.cruise_speed_knots", 25)

        max_operational_ss = self.state.get("analysis.max_sea_state", 4) or 4
        fuel_rate_cruise = self.state.get("propulsion.fuel_rate_cruise_l_hr", 200) or 200
        usable_fuel_m3 = self.state.get("fuel.usable_fuel_m3", 5) or 5
        usable_fuel = usable_fuel_m3 * 1000

        for ss in range(0, max_operational_ss + 1):
            hs = SEA_STATE_HS.get(ss, 0)

            if ss == 0:
                speed = max_speed
                limiting = "none"
            elif ss == 1:
                speed = max_speed * 0.95
                limiting = "voluntary"
            elif ss == 2:
                speed = max_speed * 0.85
                limiting = "comfort"
            elif ss == 3:
                speed = cruise_speed
                limiting = "acceleration"
            elif ss == 4:
                speed = cruise_speed * 0.8
                limiting = "slamming"
            else:
                speed = cruise_speed * 0.6
                limiting = "structural"

            fuel_rate = fuel_rate_cruise * (speed / cruise_speed) ** 2.5 if cruise_speed > 0 else fuel_rate_cruise
            endurance = usable_fuel / fuel_rate if fuel_rate > 0 else 0
            range_nm = endurance * speed

            points.append(SpeedSeaStatePoint(
                sea_state=ss, hs_m=hs, max_speed_kts=speed,
                limiting_factor=limiting, fuel_rate_l_hr=fuel_rate, range_nm=range_nm,
            ))

        return points

    def _calculate_endurance(self) -> float:
        usable_fuel_m3 = self.state.get("fuel.usable_fuel_m3", 5) or 5
        usable_fuel_l = usable_fuel_m3 * 1000
        fuel_rate = self.state.get("propulsion.fuel_rate_cruise_l_hr", 200) or 200
        if fuel_rate <= 0:
            return 0
        return usable_fuel_l / fuel_rate

    def _calculate_range(self) -> float:
        endurance = self._calculate_endurance()

        cruise_speed = self.state.get("mission.cruise_speed_kts", 0)
        if cruise_speed is None or cruise_speed <= 0:
            cruise_speed = self.state.get("mission.cruise_speed_knots", 25)

        return endurance * cruise_speed
