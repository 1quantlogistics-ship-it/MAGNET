"""
MAGNET Compliance Module (Module 10)

Validates vessel designs against regulatory requirements from classification
societies (ABS, DNV, LR), flag state rules (USCG, MCA), and international
conventions (SOLAS, HSC Code, MARPOL).

Version 1.1 - Production-Ready with Module 01 v1.8 integration.
"""

from .enums import (
    RegulatoryFramework,
    RuleCategory,
    FindingSeverity,
    ComplianceStatus,
)

from .rule_schema import (
    RuleReference,
    RuleRequirement,
    Finding,
)

from .rule_library import (
    RuleLibrary,
    RULE_LIBRARY,
)

from .checkers import (
    RuleChecker,
    StabilityRuleChecker,
    StructuralRuleChecker,
    FreeboardRuleChecker,
    get_checker,
    RULE_CHECKERS,
)

from .engine import (
    ComplianceEngine,
    ComplianceReport,
)

from .validators import (
    ComplianceValidator,
    StabilityComplianceValidator,
    determinize_dict,
    get_compliance_validator_definition,
    get_stability_compliance_definition,
    register_compliance_validators,
)

__all__ = [
    # Enumerations
    "RegulatoryFramework",
    "RuleCategory",
    "FindingSeverity",
    "ComplianceStatus",

    # Rule Schema
    "RuleReference",
    "RuleRequirement",
    "Finding",

    # Rule Library
    "RuleLibrary",
    "RULE_LIBRARY",

    # Checkers
    "RuleChecker",
    "StabilityRuleChecker",
    "StructuralRuleChecker",
    "FreeboardRuleChecker",
    "get_checker",
    "RULE_CHECKERS",

    # Engine
    "ComplianceEngine",
    "ComplianceReport",

    # Validators
    "ComplianceValidator",
    "StabilityComplianceValidator",
    "determinize_dict",
    "get_compliance_validator_definition",
    "get_stability_compliance_definition",
    "register_compliance_validators",
]
