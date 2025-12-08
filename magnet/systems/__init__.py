"""
systems/__init__.py - Modules 26-30 Systems Integration exports
ALPHA OWNS THIS FILE.

Systems Integration:
- Module 26: Propulsion System (Alpha)
- Module 27: Electrical System (Alpha)
- Module 28: HVAC System (Bravo)
- Module 29: Fuel System (Bravo)
- Module 30: Safety System (Bravo)
"""

# Section 26: Propulsion (Alpha)
from .propulsion import (
    EngineType, PropulsorType, GearboxType, ShaftMaterial, PropellerMaterial, FuelType,
    EngineSpecification, EngineLibrary,
    PropellerSpecification, WaterjetSpecification,
    GearboxSpecification, ShaftLine, PropulsionSystem,
    PropulsionSystemGenerator, PropulsionValidator,
)

# Section 27: Electrical (Alpha)
from .electrical import (
    LoadCategory, VoltageLevel,
    ElectricalLoad, GeneratorSet, BatteryBank, ElectricalSystem,
    ElectricalSystemGenerator, ElectricalValidator,
)

# Section 28: HVAC (Bravo)
from .hvac import (
    HVACZoneType, HVACZone, ACUnit, VentilationFan, HVACSystem,
    HVACSystemGenerator, HVACValidator,
)

# Section 29: Fuel (Bravo)
from .fuel import (
    TankType, FluidType, Tank, Pump, FuelSystem,
    FuelSystemGenerator, FuelValidator,
)

# Section 30: Safety (Bravo)
from .safety import (
    FireZone, FirefightingAgent,
    FireZoneDefinition, FirePump, LifeSavingAppliance, BilgeSystem, SafetySystem,
    SafetySystemGenerator, SafetyValidator,
)


__all__ = [
    # Propulsion (Section 26)
    'EngineType', 'PropulsorType', 'GearboxType', 'ShaftMaterial',
    'PropellerMaterial', 'FuelType',
    'EngineSpecification', 'EngineLibrary',
    'PropellerSpecification', 'WaterjetSpecification',
    'GearboxSpecification', 'ShaftLine', 'PropulsionSystem',
    'PropulsionSystemGenerator', 'PropulsionValidator',
    # Electrical (Section 27)
    'LoadCategory', 'VoltageLevel',
    'ElectricalLoad', 'GeneratorSet', 'BatteryBank', 'ElectricalSystem',
    'ElectricalSystemGenerator', 'ElectricalValidator',
    # HVAC (Section 28)
    'HVACZoneType', 'HVACZone', 'ACUnit', 'VentilationFan', 'HVACSystem',
    'HVACSystemGenerator', 'HVACValidator',
    # Fuel (Section 29)
    'TankType', 'FluidType', 'Tank', 'Pump', 'FuelSystem',
    'FuelSystemGenerator', 'FuelValidator',
    # Safety (Section 30)
    'FireZone', 'FirefightingAgent',
    'FireZoneDefinition', 'FirePump', 'LifeSavingAppliance', 'BilgeSystem',
    'SafetySystem', 'SafetySystemGenerator', 'SafetyValidator',
]
