"""
MAGNET Compliance Rule Schema (v1.1)

Rule definition data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .enums import RuleCategory, RegulatoryFramework, FindingSeverity

if TYPE_CHECKING:
    pass


@dataclass
class RuleReference:
    """Reference to regulatory text."""
    framework: str
    section: str
    paragraph: Optional[str] = None
    table: Optional[str] = None
    figure: Optional[str] = None
    edition_year: int = 2024

    def to_citation(self) -> str:
        """Generate citation string."""
        parts = [self.framework, self.section]
        if self.paragraph:
            parts.append(self.paragraph)
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "framework": self.framework,
            "section": self.section,
            "paragraph": self.paragraph,
            "edition_year": self.edition_year,
            "citation": self.to_citation(),
        }


@dataclass
class RuleRequirement:
    """Single regulatory requirement definition."""

    rule_id: str
    name: str
    description: str
    category: RuleCategory
    framework: RegulatoryFramework
    references: List[RuleReference] = field(default_factory=list)

    # Applicability
    vessel_types: List[str] = field(default_factory=list)
    min_length_m: Optional[float] = None
    max_length_m: Optional[float] = None
    service_restrictions: List[str] = field(default_factory=list)

    # Evaluation
    required_inputs: List[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    formula: Optional[str] = None
    limit_value: Optional[float] = None
    limit_type: str = "minimum"  # minimum, maximum, exact

    # Metadata
    mandatory: bool = True
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "framework": self.framework.value,
            "acceptance_criteria": self.acceptance_criteria,
            "mandatory": self.mandatory,
        }


@dataclass
class Finding:
    """Compliance finding from rule evaluation."""

    finding_id: str
    rule_id: str
    rule_name: str
    severity: FindingSeverity
    status: str  # pass, fail, incomplete, error, review_required
    message: str
    actual_value: Optional[Any] = None
    required_value: Optional[Any] = None
    margin: Optional[float] = None
    margin_percent: Optional[float] = None
    references: List[RuleReference] = field(default_factory=list)
    remediation_guidance: Optional[str] = None
    affected_parameters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status,
            "message": self.message,
            "actual_value": self.actual_value,
            "required_value": self.required_value,
            "margin": self.margin,
            "margin_percent": self.margin_percent,
            "references": [r.to_dict() for r in self.references],
            "remediation_guidance": self.remediation_guidance,
        }
