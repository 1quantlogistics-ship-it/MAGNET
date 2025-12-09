"""
performance/predictor.py - Performance prediction
BRAVO OWNS THIS FILE.

Section 39: Performance Prediction - v1.1 with standardized field names
"""

from typing import Dict, Any, List, TYPE_CHECKING
import math

from .resistance import SpeedPowerPoint, PropulsiveEfficiency

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class PerformancePredictor:
    """Predict vessel performance - v1.1."""

    def __init__(self, state: 'StateManager'):
        self.state = state

    def predict(self) -> Dict[str, Any]:
        loa = self.state.get("hull.loa", 25)
        lwl = self.state.get("hull.lwl", 23)
        beam = self.state.get("hull.beam", 6)
        draft = self.state.get("hull.draft", 1.5)

        displacement_mt = self.state.get("weight.full_load_displacement_mt", 0)
        if displacement_mt is None or displacement_mt <= 0:
            displacement_mt = self.state.get("weight.displacement_mt", 100)

        wetted_surface = self.state.get("hull.wetted_surface_m2", 0)
        if wetted_surface is None or wetted_surface <= 0:
            wetted_surface = lwl * (2 * draft + beam) * 0.85

        # v1.1 FIX: Use canonical _kts field names with fallback
        max_speed = self.state.get("mission.max_speed_kts", 0)
        if max_speed is None or max_speed <= 0:
            max_speed = self.state.get("mission.max_speed_knots", 35)

        cruise_speed = self.state.get("mission.cruise_speed_kts", 0)
        if cruise_speed is None or cruise_speed <= 0:
            cruise_speed = self.state.get("mission.cruise_speed_knots", 25)

        efficiency = self._estimate_efficiency()

        curve = []
        for speed in range(5, int(max_speed) + 5, 2):
            point = self._calculate_point(
                speed, lwl, beam, draft, displacement_mt,
                wetted_surface, efficiency
            )
            curve.append(point)

        cruise_point = next((p for p in curve if p.speed_kts >= cruise_speed), curve[-1])
        max_point = next((p for p in curve if p.speed_kts >= max_speed), curve[-1])

        sea_margin = 0.15

        return {
            "curve": [p.to_dict() for p in curve],
            "efficiency": efficiency.to_dict(),
            "cruise_speed_kts": cruise_speed,
            "cruise_power_kw": cruise_point.brake_power_kw,
            "cruise_power_with_margin_kw": cruise_point.brake_power_kw * (1 + sea_margin),
            "max_speed_kts": max_speed,
            "max_power_kw": max_point.brake_power_kw,
            "max_power_with_margin_kw": max_point.brake_power_kw * (1 + sea_margin),
            "sea_margin_percent": sea_margin * 100,
        }

    def _estimate_efficiency(self) -> PropulsiveEfficiency:
        prop_type = self.state.get("propulsion.propulsion_type", "propeller")

        if prop_type == "waterjet":
            return PropulsiveEfficiency(
                hull_efficiency=1.0,
                relative_rotative=1.0,
                propeller_efficiency=0.68,
                transmission_efficiency=0.96,
            )
        else:
            return PropulsiveEfficiency(
                hull_efficiency=1.05,
                relative_rotative=1.0,
                propeller_efficiency=0.65,
                transmission_efficiency=0.97,
            )

    def _calculate_point(
        self,
        speed_kts: float,
        lwl: float,
        beam: float,
        draft: float,
        displacement_mt: float,
        wetted_surface: float,
        efficiency: PropulsiveEfficiency,
    ) -> SpeedPowerPoint:
        speed_m_s = speed_kts * 0.5144

        fn = speed_m_s / math.sqrt(9.81 * lwl)

        kinematic_visc = 1.19e-6
        rn = speed_m_s * lwl / kinematic_visc

        # ITTC '57 friction line
        cf = 0.075 / (math.log10(rn) - 2) ** 2 if rn > 0 else 0.003
        rf = 0.5 * 1025 * speed_m_s ** 2 * wetted_surface * cf / 1000

        # Residuary resistance
        if fn > 0.5:
            # Planing regime (simplified Savitsky)
            cl = displacement_mt * 1000 * 9.81 / (0.5 * 1025 * speed_m_s ** 2 * beam ** 2) if speed_m_s > 0 else 0
            dl_ratio = 0.05 + 0.1 * cl
            rr = dl_ratio * displacement_mt * 9.81 / 1000
        else:
            rr = 0.5 * 1025 * speed_m_s ** 2 * wetted_surface * 0.001 * fn ** 2 / 1000

        ra = (rf + rr) * 0.05  # Appendages

        frontal_area = beam * 3
        r_air = 0.5 * 1.225 * speed_m_s ** 2 * frontal_area * 0.8 / 1000

        rt = rf + rr + ra + r_air
        pe = rt * speed_m_s
        pd = pe / efficiency.propulsive_coefficient if efficiency.propulsive_coefficient > 0 else pe
        pb = pd / efficiency.transmission_efficiency if efficiency.transmission_efficiency > 0 else pd

        return SpeedPowerPoint(
            speed_kts=speed_kts,
            froude_number=fn,
            resistance_kn=rt,
            effective_power_kw=pe,
            delivered_power_kw=pd,
            brake_power_kw=pb,
        )
