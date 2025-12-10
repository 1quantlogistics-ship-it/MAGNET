"""
separation_rule.py - System separation rules v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Defines separation requirements between different system types.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple, FrozenSet
from enum import Enum
import logging

__all__ = [
    'SeparationType',
    'SeparationRule',
    'SeparationRuleSet',
    'DEFAULT_SEPARATION_RULES',
    'get_separation_requirement',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SeparationType(Enum):
    """Types of separation requirements."""

    PROHIBITED = "prohibited"         # Cannot be co-routed at all
    PHYSICAL = "physical"             # Must have physical separation (barrier)
    DISTANCE = "distance"             # Minimum distance required
    LEVEL = "level"                   # Must be on different deck levels
    CONDUIT = "conduit"               # Must be in separate conduits
    PREFERRED = "preferred"           # Separation preferred but not required
    NONE = "none"                     # No separation required


# =============================================================================
# SEPARATION RULE
# =============================================================================

@dataclass
class SeparationRule:
    """
    Rule defining separation requirements between two system types.

    Attributes:
        rule_id: Unique identifier
        system_a: First system type
        system_b: Second system type
        separation_type: Type of separation required
        min_distance_m: Minimum distance if applicable
        max_parallel_length_m: Max length systems can run parallel
        requires_barrier: Whether physical barrier is needed
        allowed_co_routing_spaces: Space types where co-routing is allowed
        prohibited_co_routing_spaces: Space types where co-routing is prohibited
        regulation_ref: Reference to applicable regulation
        notes: Additional notes
    """

    rule_id: str
    system_a: str
    system_b: str
    separation_type: SeparationType

    # Distance requirements
    min_distance_m: float = 0.0
    max_parallel_length_m: float = -1.0  # -1 = unlimited

    # Barrier requirements
    requires_barrier: bool = False
    barrier_type: Optional[str] = None  # "A-class", "steel", "insulated"

    # Space-specific rules
    allowed_co_routing_spaces: FrozenSet[str] = field(default_factory=frozenset)
    prohibited_co_routing_spaces: FrozenSet[str] = field(default_factory=frozenset)

    # Regulatory
    regulation_ref: str = ""
    severity: str = "mandatory"  # "mandatory", "recommended", "advisory"

    # Metadata
    notes: str = ""

    def applies_to(self, sys_type_a: str, sys_type_b: str) -> bool:
        """Check if rule applies to a pair of systems."""
        return (
            (self.system_a == sys_type_a and self.system_b == sys_type_b) or
            (self.system_a == sys_type_b and self.system_b == sys_type_a)
        )

    def check_distance(self, distance_m: float) -> Tuple[bool, str]:
        """Check if distance meets requirement."""
        if self.separation_type == SeparationType.NONE:
            return True, ""

        if self.min_distance_m <= 0:
            return True, ""

        if distance_m >= self.min_distance_m:
            return True, ""

        return (
            False,
            f"Distance {distance_m:.2f}m less than required {self.min_distance_m:.2f}m"
        )

    def check_parallel_length(self, length_m: float) -> Tuple[bool, str]:
        """Check if parallel routing length is acceptable."""
        if self.max_parallel_length_m < 0:
            return True, ""

        if length_m <= self.max_parallel_length_m:
            return True, ""

        return (
            False,
            f"Parallel length {length_m:.2f}m exceeds max {self.max_parallel_length_m:.2f}m"
        )

    def is_co_routing_allowed(self, space_type: str) -> bool:
        """Check if co-routing is allowed in a space type."""
        if self.separation_type == SeparationType.PROHIBITED:
            return False

        if space_type in self.prohibited_co_routing_spaces:
            return False

        if self.allowed_co_routing_spaces:
            return space_type in self.allowed_co_routing_spaces

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "system_a": self.system_a,
            "system_b": self.system_b,
            "separation_type": self.separation_type.value,
            "min_distance_m": self.min_distance_m,
            "max_parallel_length_m": self.max_parallel_length_m,
            "requires_barrier": self.requires_barrier,
            "barrier_type": self.barrier_type,
            "allowed_co_routing_spaces": list(self.allowed_co_routing_spaces),
            "prohibited_co_routing_spaces": list(self.prohibited_co_routing_spaces),
            "regulation_ref": self.regulation_ref,
            "severity": self.severity,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeparationRule":
        """Deserialize from dictionary."""
        return cls(
            rule_id=data["rule_id"],
            system_a=data["system_a"],
            system_b=data["system_b"],
            separation_type=SeparationType(data["separation_type"]),
            min_distance_m=data.get("min_distance_m", 0.0),
            max_parallel_length_m=data.get("max_parallel_length_m", -1.0),
            requires_barrier=data.get("requires_barrier", False),
            barrier_type=data.get("barrier_type"),
            allowed_co_routing_spaces=frozenset(data.get("allowed_co_routing_spaces", [])),
            prohibited_co_routing_spaces=frozenset(data.get("prohibited_co_routing_spaces", [])),
            regulation_ref=data.get("regulation_ref", ""),
            severity=data.get("severity", "mandatory"),
            notes=data.get("notes", ""),
        )


# =============================================================================
# SEPARATION RULE SET
# =============================================================================

@dataclass
class SeparationRuleSet:
    """
    Collection of separation rules for routing validation.

    Provides lookup and validation methods for system separation.
    """

    rules: List[SeparationRule] = field(default_factory=list)

    # Index for fast lookup: (system_a, system_b) -> rule
    _rule_index: Dict[Tuple[str, str], SeparationRule] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self):
        """Build index after initialization."""
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the rule lookup index."""
        self._rule_index.clear()
        for rule in self.rules:
            key1 = (rule.system_a, rule.system_b)
            key2 = (rule.system_b, rule.system_a)
            self._rule_index[key1] = rule
            self._rule_index[key2] = rule

    def add_rule(self, rule: SeparationRule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)
        key1 = (rule.system_a, rule.system_b)
        key2 = (rule.system_b, rule.system_a)
        self._rule_index[key1] = rule
        self._rule_index[key2] = rule

    def get_rule(self, system_a: str, system_b: str) -> Optional[SeparationRule]:
        """Get separation rule for two systems."""
        return self._rule_index.get((system_a, system_b))

    def check_separation(
        self,
        system_a: str,
        system_b: str,
        distance_m: float,
        parallel_length_m: float = 0.0,
        space_type: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Check if separation requirements are met.

        Args:
            system_a: First system type
            system_b: Second system type
            distance_m: Distance between systems
            parallel_length_m: Length of parallel routing
            space_type: Type of space where systems meet

        Returns:
            (is_valid, list of violations)
        """
        rule = self.get_rule(system_a, system_b)

        if rule is None:
            return True, []

        violations = []

        # Check separation type
        if rule.separation_type == SeparationType.PROHIBITED:
            violations.append(
                f"Co-routing of {system_a} and {system_b} is prohibited"
            )
            return False, violations

        # Check distance
        is_valid, msg = rule.check_distance(distance_m)
        if not is_valid:
            violations.append(msg)

        # Check parallel length
        is_valid, msg = rule.check_parallel_length(parallel_length_m)
        if not is_valid:
            violations.append(msg)

        # Check space-specific rules
        if space_type and not rule.is_co_routing_allowed(space_type):
            violations.append(
                f"Co-routing of {system_a} and {system_b} not allowed in {space_type}"
            )

        return len(violations) == 0, violations

    def get_min_distance(self, system_a: str, system_b: str) -> float:
        """Get minimum required distance between two systems."""
        rule = self.get_rule(system_a, system_b)
        if rule is None:
            return 0.0
        return rule.min_distance_m

    def is_prohibited(self, system_a: str, system_b: str) -> bool:
        """Check if co-routing is prohibited."""
        rule = self.get_rule(system_a, system_b)
        if rule is None:
            return False
        return rule.separation_type == SeparationType.PROHIBITED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeparationRuleSet":
        """Deserialize from dictionary."""
        rules = [SeparationRule.from_dict(r) for r in data.get("rules", [])]
        return cls(rules=rules)


# =============================================================================
# DEFAULT RULES
# =============================================================================

DEFAULT_SEPARATION_RULES = SeparationRuleSet(rules=[
    # Fuel system separations
    SeparationRule(
        rule_id="fuel_electrical_hv",
        system_a="fuel",
        system_b="electrical_hv",
        separation_type=SeparationType.PHYSICAL,
        min_distance_m=0.5,
        requires_barrier=True,
        barrier_type="steel",
        regulation_ref="SOLAS II-1/45",
        notes="Fuel lines must be separated from HV electrical by steel barrier",
    ),
    SeparationRule(
        rule_id="fuel_electrical_lv",
        system_a="fuel",
        system_b="electrical_lv",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.3,
        regulation_ref="Class Rules",
    ),
    SeparationRule(
        rule_id="fuel_hvac",
        system_a="fuel",
        system_b="hvac_supply",
        separation_type=SeparationType.PROHIBITED,
        regulation_ref="SOLAS II-2/4.2",
        notes="Fuel lines cannot be co-routed with HVAC supply",
    ),
    SeparationRule(
        rule_id="fuel_freshwater",
        system_a="fuel",
        system_b="freshwater",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.3,
        regulation_ref="Class Rules",
        notes="Prevent contamination risk",
    ),

    # Electrical separations
    SeparationRule(
        rule_id="electrical_hv_lv",
        system_a="electrical_hv",
        system_b="electrical_lv",
        separation_type=SeparationType.CONDUIT,
        min_distance_m=0.15,
        regulation_ref="IEC 60092",
        notes="HV and LV must be in separate conduits or separated",
    ),
    SeparationRule(
        rule_id="electrical_fire_detection",
        system_a="electrical_hv",
        system_b="fire_detection",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.1,
        regulation_ref="Class Rules",
        notes="Prevent electromagnetic interference",
    ),

    # Water system separations
    SeparationRule(
        rule_id="freshwater_blackwater",
        system_a="freshwater",
        system_b="black_water",
        separation_type=SeparationType.PROHIBITED,
        regulation_ref="MARPOL Annex IV",
        notes="Freshwater and sewage cannot be co-routed",
    ),
    SeparationRule(
        rule_id="freshwater_greywater",
        system_a="freshwater",
        system_b="grey_water",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.2,
        regulation_ref="Class Rules",
    ),
    SeparationRule(
        rule_id="freshwater_bilge",
        system_a="freshwater",
        system_b="bilge",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.15,
        regulation_ref="Class Rules",
    ),

    # Steam separations
    SeparationRule(
        rule_id="steam_fuel",
        system_a="steam",
        system_b="fuel",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.3,
        requires_barrier=True,
        barrier_type="insulated",
        regulation_ref="Class Rules",
        notes="Hot steam near fuel requires insulation",
    ),
    SeparationRule(
        rule_id="steam_electrical",
        system_a="steam",
        system_b="electrical_hv",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.3,
        regulation_ref="IEC 60092",
    ),

    # HVAC separations
    SeparationRule(
        rule_id="hvac_supply_exhaust",
        system_a="hvac_supply",
        system_b="hvac_exhaust",
        separation_type=SeparationType.DISTANCE,
        min_distance_m=0.3,
        regulation_ref="Class Rules",
        notes="Prevent cross-contamination",
    ),

    # Firefighting (generally unrestricted)
    SeparationRule(
        rule_id="firefighting_any",
        system_a="firefighting",
        system_b="fuel",
        separation_type=SeparationType.PREFERRED,
        min_distance_m=0.1,
        regulation_ref="SOLAS II-2",
        notes="Firefighting systems have access priority",
    ),
])


def get_separation_requirement(
    system_a: str,
    system_b: str,
    rule_set: Optional[SeparationRuleSet] = None,
) -> Optional[SeparationRule]:
    """
    Get separation requirement for two system types.

    Args:
        system_a: First system type
        system_b: Second system type
        rule_set: Rule set to use (defaults to DEFAULT_SEPARATION_RULES)

    Returns:
        SeparationRule if one exists, None otherwise
    """
    if rule_set is None:
        rule_set = DEFAULT_SEPARATION_RULES

    return rule_set.get_rule(system_a, system_b)
