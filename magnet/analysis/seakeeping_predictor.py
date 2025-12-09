"""
analysis/seakeeping_predictor.py - Seakeeping analysis predictor
BRAVO OWNS THIS FILE.

Section 35: Seakeeping Analysis - v1.1 with input verification
"""

from typing import Dict, Any, List, TYPE_CHECKING
import math

from .seakeeping import (
    SeakeepingResults, MotionResponse, OperabilityResult,
    SEA_STATES, NORDFORSK_CRITERIA
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class SeakeepingPredictor:
    """Seakeeping analysis predictor."""

    REQUIRED_FIELDS = {
        "hull.lwl": "Waterline length",
        "hull.beam": "Beam",
        "hull.draft": "Draft",
        "stability.gm_transverse_m": "Metacentric height (GM)",
        "mission.cruise_speed_kts": "Cruise speed",
    }

    def __init__(self, state: 'StateManager'):
        self.state = state

    def _verify_inputs(self) -> List[str]:
        """Verify required inputs exist."""
        missing = []
        for field, desc in self.REQUIRED_FIELDS.items():
            val = self.state.get(field)
            if val is None or val == 0:
                missing.append(f"{field} ({desc})")
        return missing

    def analyze(self) -> SeakeepingResults:
        """Perform seakeeping analysis."""

        results = SeakeepingResults()

        periods = self._calculate_natural_periods()
        results.roll_period_s = periods["roll_period_s"]
        results.pitch_period_s = periods["pitch_period_s"]
        results.heave_period_s = periods["heave_period_s"]

        for ss in range(0, 6):
            hs = SEA_STATES[ss]["hs_m"]
            responses = self._calculate_motions(ss, hs, periods)
            operability = self._assess_operability(ss, hs, responses)
            results.operability_by_ss.append(operability)

            # Store responses at Sea State 3 (design condition)
            if ss == 3:
                results.responses = responses

        # Determine max operational sea state
        results.max_operational_ss = 0
        for op in results.operability_by_ss:
            if op.operable:
                results.max_operational_ss = op.sea_state
            else:
                for crit, met in op.criteria_met.items():
                    if not met:
                        results.limiting_criterion = crit
                        break
                break

        # Calculate operability index at SS4
        ss4_op = next((o for o in results.operability_by_ss if o.sea_state == 4), None)
        results.operability_index = ss4_op.percent_met if ss4_op else 0

        return results

    def _calculate_natural_periods(self) -> Dict[str, float]:
        """Calculate natural periods."""

        lwl = self.state.get("hull.lwl", 23)
        beam = self.state.get("hull.beam", 6)
        draft = self.state.get("hull.draft", 1.5)
        gm = self.state.get("stability.gm_transverse_m", 1.0)

        # Roll period (simplified formula)
        if gm > 0:
            k = 0.35 * beam  # Radius of gyration approx
            roll_period = 2 * math.pi * k / math.sqrt(9.81 * gm)
        else:
            roll_period = 0.8 * beam  # Fallback estimate

        # Pitch period (simplified)
        pitch_period = 0.5 * math.sqrt(lwl)

        # Heave period (simplified)
        heave_period = 2.4 * math.sqrt(draft)

        return {
            "roll_period_s": roll_period,
            "pitch_period_s": pitch_period,
            "heave_period_s": heave_period,
        }

    def _calculate_motions(
        self,
        sea_state: int,
        hs_m: float,
        periods: Dict,
    ) -> List[MotionResponse]:
        """Calculate motion responses."""

        responses = []
        lwl = self.state.get("hull.lwl", 23)
        speed_kts = self.state.get("mission.cruise_speed_kts", 25)

        # Define response locations
        locations = {
            "bridge": {"x": 0.85 * lwl, "z": 5.0},
            "bow": {"x": lwl, "z": 2.0},
            "midship": {"x": 0.5 * lwl, "z": 2.0},
            "stern": {"x": 0, "z": 2.0},
        }

        for loc_name, loc in locations.items():
            # Simplified motion calculations
            roll_amp = min(hs_m * 3.0, 25)
            pitch_amp = min(hs_m * 1.5 * (1 + speed_kts / 50), 12)
            heave_amp = hs_m * 0.5

            omega_roll = 2 * math.pi / periods["roll_period_s"]
            omega_pitch = 2 * math.pi / periods["pitch_period_s"]

            # Accelerations
            x_from_cg = loc["x"] - 0.5 * lwl
            vert_accel = (omega_pitch ** 2 * math.radians(pitch_amp) * abs(x_from_cg)) / 9.81
            vert_accel += hs_m * 0.05 * (1 + speed_kts / 30)

            lat_accel = (omega_roll ** 2 * math.radians(roll_amp) * loc["z"]) / 9.81

            # Motion sickness incidence (simplified)
            freq_hz = 1 / periods["heave_period_s"]
            if 0.1 < freq_hz < 0.5:
                msi = 50 * vert_accel / (0.2 + (freq_hz - 0.2) ** 2)
            else:
                msi = 30 * vert_accel
            msi = min(msi, 100)

            responses.append(MotionResponse(
                location=loc_name,
                heave_amplitude_m=heave_amp,
                pitch_amplitude_deg=pitch_amp,
                roll_amplitude_deg=roll_amp,
                vertical_accel_g=vert_accel,
                lateral_accel_g=lat_accel,
                msi_percent=msi,
            ))

        return responses

    def _assess_operability(
        self,
        sea_state: int,
        hs_m: float,
        responses: List[MotionResponse],
    ) -> OperabilityResult:
        """Assess operability against NORDFORSK criteria."""

        bridge = next((r for r in responses if r.location == "bridge"), responses[0])
        bow = next((r for r in responses if r.location == "bow"), responses[0])

        criteria_met = {
            "bridge_vertical_accel": bridge.vertical_accel_g <= NORDFORSK_CRITERIA["bridge_vertical_accel_g"],
            "bridge_lateral_accel": bridge.lateral_accel_g <= NORDFORSK_CRITERIA["bridge_lateral_accel_g"],
            "roll_amplitude": bridge.roll_amplitude_deg <= NORDFORSK_CRITERIA["roll_amplitude_deg"],
            "pitch_amplitude": bridge.pitch_amplitude_deg <= NORDFORSK_CRITERIA["pitch_amplitude_deg"],
            "msi": bridge.msi_percent <= NORDFORSK_CRITERIA["msi_percent"],
            "bow_vertical_accel": bow.vertical_accel_g <= NORDFORSK_CRITERIA["bow_vertical_accel_g"],
        }

        return OperabilityResult(
            sea_state=sea_state,
            hs_m=hs_m,
            criteria_met=criteria_met,
        )
