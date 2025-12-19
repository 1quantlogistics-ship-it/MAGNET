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


# =============================================================================
# Module 65.1: Compound Intent Extraction
# =============================================================================

# Enum mappings for broad-first extraction
# Maps enum value strings to their state paths
ENUM_TO_PATH: Dict[str, Tuple[str, str]] = {
    # HullType enum → hull.hull_type
    "monohull": ("hull.hull_type", "monohull"),
    "catamaran": ("hull.hull_type", "catamaran"),
    "trimaran": ("hull.hull_type", "trimaran"),
    "swath": ("hull.hull_type", "swath"),
    "planing": ("hull.hull_type", "planing"),
    "semi_planing": ("hull.hull_type", "semi_planing"),
    "displacement": ("hull.hull_type", "displacement"),
    "semi_displacement": ("hull.hull_type", "semi_displacement"),
    "foil_assisted": ("hull.hull_type", "foil_assisted"),
    "air_cushion": ("hull.hull_type", "air_cushion"),
    # MaterialType enum → structural_design.hull_material
    "aluminum": ("structural_design.hull_material", "aluminum"),
    "aluminium": ("structural_design.hull_material", "aluminum"),  # UK spelling
    "steel": ("structural_design.hull_material", "steel"),
    "composite": ("structural_design.hull_material", "composite"),
    "frp": ("structural_design.hull_material", "frp"),
    "grp": ("structural_design.hull_material", "grp"),
    "cfrp": ("structural_design.hull_material", "cfrp"),
    "wood": ("structural_design.hull_material", "wood"),
    "titanium": ("structural_design.hull_material", "titanium"),
    # VesselType enum → mission.vessel_type
    "patrol": ("mission.vessel_type", "patrol"),
    "ferry": ("mission.vessel_type", "ferry"),
    "workboat": ("mission.vessel_type", "workboat"),
    "yacht": ("mission.vessel_type", "yacht"),
    "fishing": ("mission.vessel_type", "fishing"),
    "cargo": ("mission.vessel_type", "cargo"),
    "military": ("mission.vessel_type", "military"),
    "research": ("mission.vessel_type", "research"),
    "tug": ("mission.vessel_type", "tug"),
    "passenger": ("mission.vessel_type", "passenger"),
    "offshore": ("mission.vessel_type", "offshore"),
    "pilot": ("mission.vessel_type", "pilot"),
    "sar": ("mission.vessel_type", "sar"),
    "crew_boat": ("mission.vessel_type", "crew_boat"),
    "landing_craft": ("mission.vessel_type", "landing_craft"),
}

# Known unsupported concepts (for user feedback)
UNSUPPORTED_CONCEPTS = {
    "pod": "ext.payload.pods",
    "pods": "ext.payload.pods",
    "container": "ext.cargo.containers",
    "containers": "ext.cargo.containers",
    "teu": "ext.cargo.teu",
    "lane": "ext.cargo.lane_meters",
    "lanes": "ext.cargo.lane_meters",
    "vehicle": "ext.cargo.vehicles",
    "vehicles": "ext.cargo.vehicles",
    "car": "ext.cargo.vehicles",
    "cars": "ext.cargo.vehicles",
    "truck": "ext.cargo.vehicles",
    "trucks": "ext.cargo.vehicles",
}


def extract_compound_intent(text: str) -> Dict:
    """
    Extract all recognizable parameters from broad user input.

    Module 65.1: Multi-pass extraction for compound mode.
    Parser is single-action internally; we run multiple passes.

    Args:
        text: Natural language input (e.g., "60m aluminum catamaran ferry")

    Returns:
        Dict with:
          - proposed_actions: List of Action-like dicts
          - unsupported_mentions: List of detected but unsupported concepts
    """
    text_lower = text.lower().strip()
    proposed_actions = []
    used_paths = set()

    # Pass 1: Explicit patterns ("set X to Y", "make X Y")
    explicit_actions = _extract_explicit_patterns(text_lower)
    for action in explicit_actions:
        if action.path not in used_paths:
            proposed_actions.append(action)
            used_paths.add(action.path)

    # Pass 2: Implicit numeric patterns ("60m", "12 meters", "25 knots")
    numeric_actions = _extract_all_numeric_patterns(text_lower)
    for action in numeric_actions:
        if action.path not in used_paths:
            proposed_actions.append(action)
            used_paths.add(action.path)

    # Pass 3: Enum values ("catamaran", "aluminum", "ferry")
    enum_actions = _extract_all_enum_mentions(text_lower)
    for action in enum_actions:
        if action.path not in used_paths:
            proposed_actions.append(action)
            used_paths.add(action.path)

    # Detect unsupported concepts
    unsupported = _detect_unsupported_mentions(text_lower, used_paths)

    return {
        "proposed_actions": proposed_actions,
        "unsupported_mentions": unsupported,
    }


def _extract_explicit_patterns(text: str) -> List[Action]:
    """
    Extract all explicit set/make/change patterns.

    Returns list of all matches (not just first).
    """
    actions = []
    patterns = [
        r"(?:set|make|change)\s+(.+?)\s+to\s+([\d.]+)\s*(\w*)",
        r"(.+?)\s*=\s*([\d.]+)\s*(\w*)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            param_text, value_str, unit_str = match.groups()
            path = _find_path(param_text)
            if path:
                value = _parse_value(value_str, path)
                unit = _parse_unit(unit_str)
                actions.append(Action(
                    action_type=ActionType.SET,
                    path=path,
                    value=value,
                    unit=unit,
                ))

    return actions


def _extract_all_numeric_patterns(text: str) -> List[Action]:
    """
    Extract all implicit numeric patterns like "60m", "12 meters", "25 knots".

    Numeric patterns have precedence over enum patterns.
    """
    actions = []

    # Pattern: number followed by unit (e.g., "60m", "12 meters", "25 kts")
    # This catches standalone measurements
    pattern = r"(\d+(?:\.\d+)?)\s*(m|meters?|ft|feet|kts|knots?|kw|mw|hp|nm|km)\b"

    for match in re.finditer(pattern, text, re.IGNORECASE):
        value_str, unit_str = match.groups()
        unit = _parse_unit(unit_str)

        # Determine path based on unit
        path = _infer_path_from_unit(unit, text)
        if path:
            value = _parse_value(value_str, path)
            actions.append(Action(
                action_type=ActionType.SET,
                path=path,
                value=value,
                unit=unit,
            ))

    return actions


def _infer_path_from_unit(unit: str, context: str) -> Optional[str]:
    """
    Infer which path to set based on unit and context.

    For Module 65.1: Simple heuristics, no LLM.
    """
    context_lower = context.lower()

    if unit == "m":
        # Check context for hints
        if "length" in context_lower or "loa" in context_lower:
            return "hull.loa"
        if "beam" in context_lower or "width" in context_lower:
            return "hull.beam"
        if "draft" in context_lower or "draught" in context_lower:
            return "hull.draft"
        if "depth" in context_lower:
            return "hull.depth"
        # Default: length is most common first mention
        return "hull.loa"

    if unit == "ft":
        # Same logic for feet
        if "length" in context_lower or "loa" in context_lower:
            return "hull.loa"
        if "beam" in context_lower or "width" in context_lower:
            return "hull.beam"
        if "draft" in context_lower or "draught" in context_lower:
            return "hull.draft"
        if "depth" in context_lower:
            return "hull.depth"
        return "hull.loa"

    if unit in ("kts", "knots"):
        if "cruise" in context_lower or "cruising" in context_lower:
            return "mission.cruise_speed_kts"
        return "mission.max_speed_kts"

    if unit in ("kW", "MW", "hp"):
        return "propulsion.total_installed_power_kw"

    if unit == "nm":
        return "mission.range_nm"

    if unit == "km":
        return "mission.range_nm"  # Will need conversion

    return None


def _extract_all_enum_mentions(text: str) -> List[Action]:
    """
    Extract all enum value mentions like "catamaran", "aluminum", "ferry".

    Processed after numeric patterns (lower precedence).
    """
    actions = []

    for enum_value, (path, canonical_value) in ENUM_TO_PATH.items():
        # Word boundary match to avoid partial matches
        pattern = rf"\b{re.escape(enum_value)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            actions.append(Action(
                action_type=ActionType.SET,
                path=path,
                value=canonical_value,
                unit=None,
            ))

    return actions


def _detect_unsupported_mentions(text: str, used_paths: set) -> List[Dict]:
    """
    Detect concepts mentioned in text that aren't supported in schema.

    Returns list of {text, concept, status, future} dicts.
    """
    unsupported = []

    for keyword, future_path in UNSUPPORTED_CONCEPTS.items():
        # Look for keyword with optional number before/after
        pattern = rf"(\d+\s*)?\b{re.escape(keyword)}\b(\s*\d+)?"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matched_text = match.group(0).strip()
            unsupported.append({
                "text": matched_text,
                "concept": keyword,
                "status": "no_schema_field",
                "future": future_path,
            })

    return unsupported
