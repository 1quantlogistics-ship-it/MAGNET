"""
MAGNET Unit Converter v1.0

Deterministic unit conversion for action validation.
All conversions are explicit and reversible.
"""

from typing import Tuple


class UnitConversionError(Exception):
    """Raised when a unit conversion is not supported."""
    pass


# Conversion factors: (from_unit, to_unit) -> multiplier
# value_in_to_unit = value_in_from_unit * multiplier
UNIT_CONVERSIONS = {
    # Power
    ("MW", "kW"): 1000.0,
    ("kW", "MW"): 0.001,
    ("hp", "kW"): 0.7457,
    ("kW", "hp"): 1.341,
    ("MW", "hp"): 1341.0,
    ("hp", "MW"): 0.0007457,

    # Length
    ("m", "ft"): 3.28084,
    ("ft", "m"): 0.3048,
    ("m", "mm"): 1000.0,
    ("mm", "m"): 0.001,
    ("ft", "in"): 12.0,
    ("in", "ft"): 1/12.0,
    ("m", "in"): 39.3701,
    ("in", "m"): 0.0254,

    # Distance (nautical)
    ("nm", "km"): 1.852,
    ("km", "nm"): 0.539957,
    ("nm", "m"): 1852.0,
    ("m", "nm"): 0.000539957,

    # Speed
    ("kts", "m/s"): 0.514444,
    ("m/s", "kts"): 1.94384,
    ("kts", "km/h"): 1.852,
    ("km/h", "kts"): 0.539957,
    ("kts", "mph"): 1.15078,
    ("mph", "kts"): 0.868976,

    # Mass
    ("mt", "kg"): 1000.0,
    ("kg", "mt"): 0.001,
    ("mt", "lb"): 2204.62,
    ("lb", "mt"): 0.000453592,
    ("kg", "lb"): 2.20462,
    ("lb", "kg"): 0.453592,

    # Volume
    ("m3", "l"): 1000.0,
    ("l", "m3"): 0.001,
    ("m3", "gal"): 264.172,
    ("gal", "m3"): 0.00378541,
    ("l", "gal"): 0.264172,
    ("gal", "l"): 3.78541,

    # Area
    ("m2", "ft2"): 10.7639,
    ("ft2", "m2"): 0.092903,

    # Pressure
    ("kPa", "psi"): 0.145038,
    ("psi", "kPa"): 6.89476,
    ("bar", "kPa"): 100.0,
    ("kPa", "bar"): 0.01,

    # Angle
    ("deg", "rad"): 0.0174533,
    ("rad", "deg"): 57.2958,
}


class UnitConverter:
    """
    Deterministic unit converter.

    All conversions use explicit factors. No implicit conversions.
    """

    @staticmethod
    def normalize(value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert value from one unit to another.

        Args:
            value: The numeric value to convert
            from_unit: Source unit (e.g., "MW")
            to_unit: Target unit (e.g., "kW")

        Returns:
            Converted value

        Raises:
            UnitConversionError: If conversion not supported
        """
        if from_unit == to_unit:
            return value

        # Normalize unit strings (case-insensitive for common units)
        from_key = from_unit.strip()
        to_key = to_unit.strip()

        key = (from_key, to_key)
        if key not in UNIT_CONVERSIONS:
            # Try case-insensitive lookup
            key_upper = (from_key.upper(), to_key.upper())
            key_lower = (from_key.lower(), to_key.lower())

            if key_upper in UNIT_CONVERSIONS:
                key = key_upper
            elif key_lower in UNIT_CONVERSIONS:
                key = key_lower
            else:
                raise UnitConversionError(
                    f"Unknown conversion: {from_unit} -> {to_unit}. "
                    f"Supported conversions: {list(UNIT_CONVERSIONS.keys())}"
                )

        return value * UNIT_CONVERSIONS[key]

    @staticmethod
    def can_convert(from_unit: str, to_unit: str) -> bool:
        """
        Check if a conversion is supported.

        Args:
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            True if conversion is supported
        """
        if from_unit == to_unit:
            return True

        from_key = from_unit.strip()
        to_key = to_unit.strip()

        key = (from_key, to_key)
        if key in UNIT_CONVERSIONS:
            return True

        # Try case-insensitive
        key_upper = (from_key.upper(), to_key.upper())
        key_lower = (from_key.lower(), to_key.lower())

        return key_upper in UNIT_CONVERSIONS or key_lower in UNIT_CONVERSIONS

    @staticmethod
    def get_supported_units() -> set:
        """
        Get all supported unit names.

        Returns:
            Set of unit strings
        """
        units = set()
        for from_u, to_u in UNIT_CONVERSIONS.keys():
            units.add(from_u)
            units.add(to_u)
        return units


def clamp_to_bounds(
    value: float,
    min_value: float = None,
    max_value: float = None
) -> Tuple[float, bool]:
    """
    Clamp a value to bounds.

    Args:
        value: Value to clamp
        min_value: Minimum allowed (None = no min)
        max_value: Maximum allowed (None = no max)

    Returns:
        Tuple of (clamped_value, was_clamped)
    """
    clamped = value
    was_clamped = False

    if min_value is not None and value < min_value:
        clamped = min_value
        was_clamped = True

    if max_value is not None and value > max_value:
        clamped = max_value
        was_clamped = True

    return clamped, was_clamped
