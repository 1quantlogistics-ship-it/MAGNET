"""
Structural Feasibility Assessment (Advisory Only).

Provides warnings about potentially problematic geometry but NEVER blocks validation.

CRITICAL: This is ADVISORY ONLY. The kernel validates physics, not design intent.
          Structural feasibility is a design consideration, not a physical law.
          
Reference: MAGNET_Critical_Corrections.md Q7
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FeasibilityWarning:
    """A single structural feasibility warning."""
    severity: str  # "info", "warning", "concern"
    category: str  # "proportion", "taper", "structural"
    message: str
    recommendation: Optional[str] = None
    affected_parameter: Optional[str] = None


@dataclass
class FeasibilityAssessment:
    """Result of structural feasibility assessment."""
    warnings: List[FeasibilityWarning] = field(default_factory=list)
    overall_feasibility: str = "good"  # "good", "acceptable", "questionable"
    notes: List[str] = field(default_factory=list)
    
    def add_warning(
        self,
        severity: str,
        category: str,
        message: str,
        recommendation: Optional[str] = None,
        affected_parameter: Optional[str] = None,
    ) -> None:
        """Add a warning to the assessment."""
        warning = FeasibilityWarning(
            severity=severity,
            category=category,
            message=message,
            recommendation=recommendation,
            affected_parameter=affected_parameter,
        )
        self.warnings.append(warning)


def assess_structural_feasibility(
    loa: float,
    beam: float,
    draft: float,
    depth: Optional[float] = None,
    body_count: int = 1,
    hull_spacing: Optional[float] = None,
) -> FeasibilityAssessment:
    """
    Assess structural feasibility of hull geometry.
    
    **ADVISORY ONLY** - Returns warnings but NEVER blocks validation.
    
    Args:
        loa: Length overall (m)
        beam: Beam (m)
        draft: Draft (m)
        depth: Depth (m, optional)
        body_count: Number of hull bodies
        hull_spacing: Spacing between hulls for multi-body (m)
    
    Returns:
        FeasibilityAssessment with warnings (never raises exceptions)
    """
    assessment = FeasibilityAssessment()
    
    # Check L/B ratio
    lb_ratio = loa / beam if beam > 0 else 0
    
    if lb_ratio < 2.5:
        assessment.add_warning(
            severity="warning",
            category="proportion",
            message=f"L/B ratio is {lb_ratio:.1f}, which is very low (beamy hull)",
            recommendation="Consider if structural reinforcement needed for transverse bending. L/B typically 3.5-8 for conventional hulls.",
            affected_parameter="beam",
        )
    elif lb_ratio > 15:
        assessment.add_warning(
            severity="warning",
            category="proportion",
            message=f"L/B ratio is {lb_ratio:.1f}, which is very high (slender hull)",
            recommendation="Verify longitudinal strength is adequate. May require substantial longitudinals or bottom girders.",
            affected_parameter="loa",
        )
    
    # Check depth/draft ratio
    if depth:
        depth_draft_ratio = depth / draft if draft > 0 else 0
        
        if depth_draft_ratio < 1.3:
            assessment.add_warning(
                severity="concern",
                category="structural",
                message=f"Depth/draft ratio is {depth_draft_ratio:.2f}, which provides limited freeboard",
                recommendation="Consider increasing depth for structural integrity and seakeeping. Typical ratio: 1.5-2.0.",
                affected_parameter="depth",
            )
        elif depth_draft_ratio > 3.0:
            assessment.add_warning(
                severity="info",
                category="structural",
                message=f"Depth/draft ratio is {depth_draft_ratio:.2f}, which is high",
                recommendation="High topsides may require additional transverse framing for panel support.",
                affected_parameter="depth",
            )
    
    # Check beam/draft ratio
    beam_draft_ratio = beam / draft if draft > 0 else 0
    
    if beam_draft_ratio < 1.5:
        assessment.add_warning(
            severity="info",
            category="proportion",
            message=f"Beam/draft ratio is {beam_draft_ratio:.2f}, indicating a deep, narrow hull",
            recommendation="Verify lateral stability and consider potential for large roll angles.",
            affected_parameter="beam",
        )
    elif beam_draft_ratio > 5.0:
        assessment.add_warning(
            severity="warning",
            category="structural",
            message=f"Beam/draft ratio is {beam_draft_ratio:.2f}, indicating a wide, shallow hull",
            recommendation="Bottom plating may require substantial thickness or stiffening. Consider panel loads.",
            affected_parameter="draft",
        )
    
    # Multi-body specific checks
    if body_count > 1 and hull_spacing:
        spacing_loa_ratio = hull_spacing / loa if loa > 0 else 0
        
        if spacing_loa_ratio < 0.15:
            assessment.add_warning(
                severity="warning",
                category="structural",
                message=f"Hull spacing is {spacing_loa_ratio:.2%} of LOA, which is narrow for multi-body",
                recommendation="Narrow spacing may lead to wave interference and structural loads on cross-structure. Consider tunnel slamming.",
                affected_parameter="hull_spacing",
            )
        elif spacing_loa_ratio > 0.5:
            assessment.add_warning(
                severity="concern",
                category="structural",
                message=f"Hull spacing is {spacing_loa_ratio:.2%} of LOA, which is very wide",
                recommendation="Wide spacing increases structural loads on cross-beams. Verify beam scantlings and deflection limits.",
                affected_parameter="hull_spacing",
            )
    
    # Determine overall feasibility
    warning_count = len([w for w in assessment.warnings if w.severity == "warning"])
    concern_count = len([w for w in assessment.warnings if w.severity == "concern"])
    
    if concern_count > 0 or warning_count >= 3:
        assessment.overall_feasibility = "questionable"
        assessment.notes.append("Multiple structural concerns identified. Recommend detailed structural analysis.")
    elif warning_count > 0:
        assessment.overall_feasibility = "acceptable"
        assessment.notes.append("Some structural considerations noted. Review recommendations.")
    else:
        assessment.overall_feasibility = "good"
        assessment.notes.append("No significant structural feasibility concerns.")
    
    return assessment


def format_feasibility_report(assessment: FeasibilityAssessment) -> str:
    """
    Format feasibility assessment as human-readable text.
    
    Args:
        assessment: FeasibilityAssessment to format
    
    Returns:
        Formatted report string
    """
    lines = []
    
    lines.append("## Structural Feasibility Assessment (Advisory)")
    lines.append(f"Overall: {assessment.overall_feasibility.upper()}")
    lines.append("")
    
    if assessment.warnings:
        lines.append("### Warnings:")
        for warning in assessment.warnings:
            emoji = {"info": "ℹ️", "warning": "⚠️", "concern": "🔴"}.get(warning.severity, "•")
            lines.append(f"{emoji} **{warning.category}**: {warning.message}")
            if warning.recommendation:
                lines.append(f"   → {warning.recommendation}")
            lines.append("")
    
    if assessment.notes:
        lines.append("### Notes:")
        for note in assessment.notes:
            lines.append(f"- {note}")
    
    lines.append("")
    lines.append("*This is an advisory assessment only. Novel geometry is not blocked by these warnings.*")
    
    return "\n".join(lines)

