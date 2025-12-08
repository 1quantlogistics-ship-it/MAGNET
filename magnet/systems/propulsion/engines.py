"""
systems/propulsion/engines.py - Main engine definitions
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EngineSpecification:
    """Main engine specification."""

    # === IDENTIFICATION ===
    engine_id: str = ""
    manufacturer: str = ""
    model: str = ""
    engine_type: str = "diesel_high_speed"

    # === POWER ===
    mcr_kw: float = 0.0
    """Maximum continuous rating (kW)."""

    mcr_rpm: float = 0.0
    """RPM at MCR."""

    service_power_kw: float = 0.0
    """Service power (typically 85-90% MCR)."""

    # === FUEL CONSUMPTION ===
    sfoc_g_kwh: float = 200.0
    """Specific fuel oil consumption at MCR (g/kWh)."""

    sfoc_service_g_kwh: float = 195.0
    """SFOC at service power."""

    fuel_type: str = "mgo"

    # === DIMENSIONS ===
    length_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0

    dry_weight_kg: float = 0.0
    wet_weight_kg: float = 0.0

    # === REQUIREMENTS ===
    cooling_water_m3_hr: float = 0.0
    combustion_air_m3_hr: float = 0.0
    exhaust_gas_m3_hr: float = 0.0
    lube_oil_capacity_l: float = 0.0

    def calculate_fuel_rate(self, power_kw: float) -> float:
        """Calculate fuel consumption rate (L/hr)."""
        if self.mcr_kw <= 0:
            return 0.0

        # Interpolate SFOC
        load_fraction = power_kw / self.mcr_kw
        sfoc = self.sfoc_service_g_kwh + (self.sfoc_g_kwh - self.sfoc_service_g_kwh) * (load_fraction - 0.85) / 0.15
        sfoc = max(self.sfoc_service_g_kwh, sfoc)

        # Convert to L/hr (assume 0.85 kg/L for MGO)
        fuel_kg_hr = sfoc * power_kw / 1000
        fuel_l_hr = fuel_kg_hr / 0.85

        return fuel_l_hr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "engine_type": self.engine_type,
            "mcr_kw": self.mcr_kw,
            "mcr_rpm": self.mcr_rpm,
            "service_power_kw": self.service_power_kw,
            "sfoc_g_kwh": self.sfoc_g_kwh,
            "fuel_type": self.fuel_type,
            "dry_weight_kg": round(self.dry_weight_kg, 0),
            "wet_weight_kg": round(self.wet_weight_kg, 0),
            "length_mm": self.length_mm,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
        }


class EngineLibrary:
    """Library of standard marine engines."""

    ENGINES: Dict[str, EngineSpecification] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, engine: EngineSpecification) -> None:
        cls.ENGINES[engine.engine_id] = engine

    @classmethod
    def get(cls, engine_id: str) -> Optional[EngineSpecification]:
        cls._ensure_initialized()
        return cls.ENGINES.get(engine_id)

    @classmethod
    def find_by_power(
        cls,
        min_power_kw: float,
        max_power_kw: float,
        engine_type: str = "diesel_high_speed",
    ) -> List[EngineSpecification]:
        """Find engines within power range."""
        cls._ensure_initialized()
        return [
            e for e in cls.ENGINES.values()
            if min_power_kw <= e.mcr_kw <= max_power_kw
            and e.engine_type == engine_type
        ]

    @classmethod
    def list_all(cls) -> List[str]:
        """List all engine IDs."""
        cls._ensure_initialized()
        return list(cls.ENGINES.keys())

    @classmethod
    def _ensure_initialized(cls) -> None:
        if not cls._initialized:
            cls._initialize_defaults()
            cls._initialized = True

    @classmethod
    def _initialize_defaults(cls) -> None:
        """Initialize default engine library."""

        # MTU Series 2000
        cls.register(EngineSpecification(
            engine_id="MTU-12V2000-M96",
            manufacturer="MTU",
            model="12V 2000 M96",
            engine_type="diesel_high_speed",
            mcr_kw=1432,
            mcr_rpm=2450,
            service_power_kw=1217,
            sfoc_g_kwh=213,
            dry_weight_kg=2150,
            wet_weight_kg=2350,
            length_mm=1942,
            width_mm=1184,
            height_mm=1282,
        ))

        cls.register(EngineSpecification(
            engine_id="MTU-16V2000-M96",
            manufacturer="MTU",
            model="16V 2000 M96",
            engine_type="diesel_high_speed",
            mcr_kw=1939,
            mcr_rpm=2450,
            service_power_kw=1648,
            sfoc_g_kwh=215,
            dry_weight_kg=2830,
            wet_weight_kg=3100,
            length_mm=2218,
            width_mm=1184,
            height_mm=1282,
        ))

        # MTU Series 4000
        cls.register(EngineSpecification(
            engine_id="MTU-16V4000-M63",
            manufacturer="MTU",
            model="16V 4000 M63",
            engine_type="diesel_high_speed",
            mcr_kw=2720,
            mcr_rpm=1800,
            service_power_kw=2312,
            sfoc_g_kwh=203,
            dry_weight_kg=6100,
            wet_weight_kg=6700,
            length_mm=3070,
            width_mm=1785,
            height_mm=1926,
        ))

        # Caterpillar
        cls.register(EngineSpecification(
            engine_id="CAT-C18-ACERT",
            manufacturer="Caterpillar",
            model="C18 ACERT",
            engine_type="diesel_high_speed",
            mcr_kw=597,
            mcr_rpm=2100,
            service_power_kw=507,
            sfoc_g_kwh=220,
            dry_weight_kg=1587,
            wet_weight_kg=1750,
            length_mm=1516,
            width_mm=1130,
            height_mm=1143,
        ))

        cls.register(EngineSpecification(
            engine_id="CAT-C32-ACERT",
            manufacturer="Caterpillar",
            model="C32 ACERT",
            engine_type="diesel_high_speed",
            mcr_kw=1193,
            mcr_rpm=2300,
            service_power_kw=1014,
            sfoc_g_kwh=218,
            dry_weight_kg=2562,
            wet_weight_kg=2800,
            length_mm=1900,
            width_mm=1268,
            height_mm=1346,
        ))

        cls.register(EngineSpecification(
            engine_id="CAT-3516C",
            manufacturer="Caterpillar",
            model="3516C",
            engine_type="diesel_high_speed",
            mcr_kw=2525,
            mcr_rpm=1800,
            service_power_kw=2146,
            sfoc_g_kwh=205,
            dry_weight_kg=7300,
            wet_weight_kg=8000,
            length_mm=3198,
            width_mm=1770,
            height_mm=2018,
        ))

        # MAN
        cls.register(EngineSpecification(
            engine_id="MAN-D2676-LE433",
            manufacturer="MAN",
            model="D2676 LE433",
            engine_type="diesel_high_speed",
            mcr_kw=588,
            mcr_rpm=2100,
            service_power_kw=500,
            sfoc_g_kwh=215,
            dry_weight_kg=1100,
            wet_weight_kg=1250,
            length_mm=1450,
            width_mm=900,
            height_mm=1050,
        ))

        cls.register(EngineSpecification(
            engine_id="MAN-D2862-LE463",
            manufacturer="MAN",
            model="D2862 LE463",
            engine_type="diesel_high_speed",
            mcr_kw=1213,
            mcr_rpm=2100,
            service_power_kw=1031,
            sfoc_g_kwh=210,
            dry_weight_kg=2100,
            wet_weight_kg=2300,
            length_mm=1874,
            width_mm=1035,
            height_mm=1255,
        ))
