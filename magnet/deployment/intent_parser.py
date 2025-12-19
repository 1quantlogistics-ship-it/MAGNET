"""
MAGNET Intent Parser - Keyword-Only

Module 63: Parses natural language to Actions using REFINABLE_SCHEMA keywords only.
NO LLM, NO fuzzy matching, NO synonym expansion.

v1.0: Initial implementation
"""

import re
from typing import List, Optional, Tuple
from magnet.kernel.intent_protocol import Action, ActionType
from magnet.core.refinable_schema import REFINABLE_SCHEMA, RefinableField


# =============================================================================
# KEYWORD TO PATH MAPPING (Single Source of Truth)
# =============================================================================

# Build keyword → path mapping from REFINABLE_SCHEMA
from typing import Dict
KEYWORD_TO_PATH: Dict[str, str] = {}
for path, field in REFINABLE_SCHEMA.items():
    # Add path itself as keyword (e.g., "hull.loa" → "hull.loa")
    KEYWORD_TO_PATH[path.lower()] = path
    # Add short name (e.g., "loa" → "hull.loa")
    short_name = path.split(".")[-1]
    if short_name not in KEYWORD_TO_PATH:
        KEYWORD_TO_PATH[short_name.lower()] = path
    # Add all keywords from schema
    for kw in field.keywords:
        KEYWORD_TO_PATH[kw.lower()] = path


# Recognized units for parsing
UNITS = {
    "m": "m", "meters": "m", "meter": "m",
    "ft": "ft", "feet": "ft", "foot": "ft",
    "kts": "kts", "knots": "kts", "knot": "kts",
    "kw": "kW", "kilowatt": "kW", "kilowatts": "kW",
    "mw": "MW", "megawatt": "MW", "megawatts": "MW",
    "hp": "hp", "horsepower": "hp",
    "nm": "nm", "nautical miles": "nm",
    "km": "km", "kilometers": "km",
    "deg": "deg", "degrees": "deg", "degree": "deg",
    "rad": "rad", "radians": "rad",
}


def parse_intent_to_actions(text: str) -> List[Action]:
    """
    Parse natural language text to Action objects.

    Uses strict keyword matching from REFINABLE_SCHEMA only.
    Returns empty list if no recognized patterns found.

    Recognized patterns:
    - "set {param} to {value} [{unit}]"
    - "make {param} {value} [{unit}]"
    - "change {param} to {value} [{unit}]"
    - "increase {param} by {amount} [{unit}]"
    - "decrease {param} by {amount} [{unit}]"
    - "{param} = {value} [{unit}]"
    - "{param} {value} [{unit}]" (implicit set)

    Args:
        text: Natural language input

    Returns:
        List of Action objects (empty if no match)
    """
    text_lower = text.lower().strip()
    actions = []

    # Try each pattern
    action = _try_set_pattern(text_lower) or \
             _try_increase_pattern(text_lower) or \
             _try_decrease_pattern(text_lower) or \
             _try_implicit_set(text_lower)

    if action:
        actions.append(action)

    return actions


def _try_set_pattern(text: str) -> Optional[Action]:
    """
    Match: "set {param} to {value} [{unit}]"
    Also: "make/change {param} to {value}"
    Also: "{param} = {value}"
    """
    patterns = [
        r"(?:set|make|change)\s+(.+?)\s+to\s+([\d.]+)\s*(\w*)",
        r"(.+?)\s*=\s*([\d.]+)\s*(\w*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            param_text, value_str, unit_str = match.groups()
            path = _find_path(param_text)
            if path:
                value = _parse_value(value_str, path)
                unit = _parse_unit(unit_str)
                return Action(
                    action_type=ActionType.SET,
                    path=path,
                    value=value,
                    unit=unit,
                )

    return None


def _try_increase_pattern(text: str) -> Optional[Action]:
    """Match: "increase {param} by {amount} [{unit}]" """
    pattern = r"increase\s+(.+?)\s+by\s+([\d.]+)\s*(\w*)"
    match = re.search(pattern, text)

    if match:
        param_text, amount_str, unit_str = match.groups()
        path = _find_path(param_text)
        if path:
            amount = float(amount_str)
            unit = _parse_unit(unit_str)
            return Action(
                action_type=ActionType.INCREASE,
                path=path,
                amount=amount,
                unit=unit,
            )

    return None


def _try_decrease_pattern(text: str) -> Optional[Action]:
    """Match: "decrease {param} by {amount} [{unit}]" """
    pattern = r"decrease\s+(.+?)\s+by\s+([\d.]+)\s*(\w*)"
    match = re.search(pattern, text)

    if match:
        param_text, amount_str, unit_str = match.groups()
        path = _find_path(param_text)
        if path:
            amount = float(amount_str)
            unit = _parse_unit(unit_str)
            return Action(
                action_type=ActionType.DECREASE,
                path=path,
                amount=amount,
                unit=unit,
            )

    return None


def _try_implicit_set(text: str) -> Optional[Action]:
    """
    Match: "{param} {value} [{unit}]"
    Implicit set when param keyword followed by number.
    """
    # Find first keyword match
    for keyword, path in KEYWORD_TO_PATH.items():
        if keyword in text:
            # Look for number after keyword
            pattern = rf"{re.escape(keyword)}\s+([\d.]+)\s*(\w*)"
            match = re.search(pattern, text)
            if match:
                value_str, unit_str = match.groups()
                value = _parse_value(value_str, path)
                unit = _parse_unit(unit_str)
                return Action(
                    action_type=ActionType.SET,
                    path=path,
                    value=value,
                    unit=unit,
                )

    return None


def _find_path(param_text: str) -> Optional[str]:
    """
    Find REFINABLE_SCHEMA path from parameter text.

    Uses exact keyword matching only.
    """
    param_lower = param_text.strip().lower()

    # Direct match
    if param_lower in KEYWORD_TO_PATH:
        return KEYWORD_TO_PATH[param_lower]

    # Check if any keyword is contained in param text
    for keyword, path in sorted(KEYWORD_TO_PATH.items(), key=lambda x: -len(x[0])):
        # Prefer longer matches first
        if keyword in param_lower:
            return path

    return None


def _parse_value(value_str: str, path: str) -> any:
    """Parse value string to appropriate type based on schema."""
    field = REFINABLE_SCHEMA.get(path)
    if not field:
        return float(value_str)

    if field.type == "int":
        return int(float(value_str))
    elif field.type == "bool":
        return value_str.lower() in ("true", "1", "yes")
    else:
        return float(value_str)


def _parse_unit(unit_str: str) -> Optional[str]:
    """Parse unit string to canonical form."""
    if not unit_str:
        return None

    unit_lower = unit_str.lower().strip()
    return UNITS.get(unit_lower)


def get_guidance_message() -> str:
    """
    Return guidance for unrecognized input.
    """
    return (
        "Try commands like:\n"
        "  • set hull length to 30 meters\n"
        "  • increase beam by 0.5 m\n"
        "  • decrease draft by 0.2 ft\n"
        "  • set max speed to 25 kts\n"
        "  • change power to 500 kW"
    )
