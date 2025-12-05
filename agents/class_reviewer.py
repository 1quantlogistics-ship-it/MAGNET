"""
MAGNET Class Reviewer Agent
============================

The Class Reviewer agent validates designs against classification society requirements.

Responsibilities:
- Review structural design against ABS HSNC 2023
- Validate stability results against IMO A.749
- Check hull parameters against physical bounds
- Vote on proposals in consensus system
- Flag non-compliance issues

Communication Flow (from Operations Guide):
1. Other agents write proposals to memory
2. Orchestrator triggers Class Reviewer
3. Class Reviewer validates against classification rules
4. Class Reviewer submits vote (approve/reject/abstain)
5. Supervisor reviews Class Reviewer decisions
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import AgentVoteSchema, VoteType

# Import ALPHA's validation module
try:
    from validation.semantic import (
        SemanticValidator,
        ValidationResult,
        ValidationSeverity,
        ValidationIssue,
        validate_design,
    )
    from validation.bounds import (
        BoundsValidator,
        BoundsCheckResult,
        check_bounds,
    )
    ALPHA_VALIDATION_AVAILABLE = True
except ImportError:
    ALPHA_VALIDATION_AVAILABLE = False


class ComplianceStandard(Enum):
    """Classification society standards."""
    ABS_HSNC = "ABS HSNC 2023"
    DNV_HSLC = "DNV-RU-HSLC"
    LLOYDS_SSC = "LR SSC 2023"
    IMO_A749 = "IMO A.749"


class ClassReviewerAgent(BaseAgent):
    """
    Class Reviewer Agent - Classification Compliance.

    Validates designs against classification society requirements:
    - ABS HSNC 2023 for high-speed naval craft
    - IMO A.749 for intact stability
    - Physical bounds checking
    - Mission-hull compatibility
    """

    REVIEWER_PROMPT = """You are the Class Reviewer Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to validate designs against classification society requirements.

## Your Responsibilities:
1. Review structural design against ABS HSNC 2023
2. Validate stability results against IMO A.749
3. Check hull parameters against physical bounds
4. Vote on proposals (approve/reject/abstain)
5. Flag non-compliance issues with specific rule references

## Validation Standards:
- ABS HSNC 2023: High-Speed Naval Craft rules
- IMO A.749: Intact Stability Code
- Physical bounds: Engineering feasibility checks

## Output Format:
Respond with review findings followed by JSON with REVIEW_JSON: marker.

Example output:
```
Review of hull design against ABS HSNC 2023:
- GM = 1.23m meets IMO A.749 requirement (>0.15m)
- Plate thickness 8mm compliant with ABS 3-3-2/5.1
- Hull slenderness 6.8 appropriate for 35 kt design speed

REVIEW_JSON:
{
  "standard": "ABS HSNC 2023",
  "compliant": true,
  "findings": [
    {"rule": "ABS 3-3-2/5.1", "status": "PASS", "notes": "Plate thickness compliant"},
    {"rule": "IMO A.749", "status": "PASS", "notes": "GM > 0.15m"}
  ],
  "vote": "APPROVE",
  "confidence": 0.85
}
```

## Decision Guidelines:

### APPROVE when:
- All classification requirements met
- No errors, only minor warnings
- Design is technically sound

### REJECT when:
- Critical safety requirements not met
- Stability criteria failed
- Structural scantlings insufficient

### ABSTAIN when:
- Insufficient data to make determination
- Outside scope of classification review
"""

    def __init__(
        self,
        agent_id: str = "class_reviewer_001",
        memory_path: str = "memory",
        standards: List[ComplianceStandard] = None,
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="class_reviewer",
            memory_path=memory_path,
            **kwargs
        )
        self.standards = standards or [
            ComplianceStandard.ABS_HSNC,
            ComplianceStandard.IMO_A749,
        ]

    @property
    def system_prompt(self) -> str:
        return self.REVIEWER_PROMPT

    def _read_design_data(self) -> Dict[str, Optional[Dict]]:
        """Read all relevant design data from memory."""
        return {
            "mission": self.memory.read("mission"),
            "hull_params": self.memory.read("hull_params"),
            "stability_results": self.memory.read("stability_results"),
            "structural_design": self.memory.read("structural_design"),
            "propulsion_config": self.memory.read("propulsion_config"),
            "resistance_results": self.memory.read("resistance_results"),
        }

    def _run_semantic_validation(
        self,
        mission: Optional[Dict],
        hull: Optional[Dict],
        stability: Optional[Dict],
    ) -> Optional[ValidationResult]:
        """Run semantic validation using ALPHA's validator."""
        if not ALPHA_VALIDATION_AVAILABLE:
            return None

        return validate_design(
            mission=mission,
            hull=hull,
            stability=stability,
        )

    def _run_bounds_validation(
        self,
        mission: Optional[Dict],
        hull: Optional[Dict],
        stability: Optional[Dict],
        resistance: Optional[Dict],
    ) -> Optional[List[BoundsCheckResult]]:
        """Run bounds validation using ALPHA's validator."""
        if not ALPHA_VALIDATION_AVAILABLE:
            return None

        is_valid, results = check_bounds(
            mission=mission,
            hull=hull,
            stability=stability,
            resistance=resistance,
        )
        return results

    def _check_structural_compliance(
        self,
        structural: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """Check structural design for compliance."""
        findings = []

        if structural is None:
            findings.append({
                "rule": "ABS HSNC 3-3",
                "status": "INCOMPLETE",
                "severity": "info",
                "notes": "Structural design not yet completed",
            })
            return findings

        # Check material compliance
        material = structural.get("material", {})
        alloy = material.get("alloy", "")

        if "5083" in alloy or "5086" in alloy or "5456" in alloy:
            findings.append({
                "rule": "ABS HSNC 2-4-1/3.1",
                "status": "PASS",
                "severity": "ok",
                "notes": f"Alloy {alloy} approved for primary structure",
            })
        elif "6061" in alloy or "6063" in alloy or "6082" in alloy:
            findings.append({
                "rule": "ABS HSNC 2-4-1/1.3",
                "status": "FAIL",
                "severity": "error",
                "notes": f"Alloy {alloy} PROHIBITED for hull structure (severe HAZ degradation)",
            })
        else:
            findings.append({
                "rule": "ABS HSNC 2-4-1",
                "status": "WARNING",
                "severity": "warning",
                "notes": f"Alloy {alloy} - verify classification approval",
            })

        # Check plating compliance
        summary = structural.get("summary", {})

        if summary.get("all_plating_compliant", False):
            findings.append({
                "rule": "ABS HSNC 3-3-2/5.1",
                "status": "PASS",
                "severity": "ok",
                "notes": "All plating meets minimum thickness requirements",
            })
        else:
            findings.append({
                "rule": "ABS HSNC 3-3-2/5.1",
                "status": "FAIL",
                "severity": "error",
                "notes": "Some plating zones do not meet minimum thickness",
            })

        if summary.get("all_stiffeners_compliant", False):
            findings.append({
                "rule": "ABS HSNC 3-3-3/5.1",
                "status": "PASS",
                "severity": "ok",
                "notes": "All stiffeners meet section modulus requirements",
            })
        else:
            findings.append({
                "rule": "ABS HSNC 3-3-3/5.1",
                "status": "FAIL",
                "severity": "error",
                "notes": "Some stiffeners do not meet section modulus requirements",
            })

        return findings

    def _check_stability_compliance(
        self,
        stability: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """Check stability results for IMO A.749 compliance."""
        findings = []

        if stability is None:
            findings.append({
                "rule": "IMO A.749",
                "status": "INCOMPLETE",
                "severity": "info",
                "notes": "Stability analysis not yet completed",
            })
            return findings

        # GM check
        gm = stability.get("GM", 0)
        if gm >= 0.15:
            findings.append({
                "rule": "IMO A.749 3.1.2.1",
                "status": "PASS",
                "severity": "ok",
                "notes": f"GM = {gm:.3f}m (required >= 0.15m)",
            })
        else:
            findings.append({
                "rule": "IMO A.749 3.1.2.1",
                "status": "FAIL",
                "severity": "error",
                "notes": f"GM = {gm:.3f}m is below minimum 0.15m",
            })

        # IMO criteria passed flag
        if stability.get("imo_criteria_passed", False):
            findings.append({
                "rule": "IMO A.749",
                "status": "PASS",
                "severity": "ok",
                "notes": "All IMO intact stability criteria met",
            })
        else:
            findings.append({
                "rule": "IMO A.749",
                "status": "FAIL",
                "severity": "error",
                "notes": "One or more IMO stability criteria not met",
            })

            # Detail failed criteria
            criteria = stability.get("imo_criteria_details", {})
            for name, details in criteria.items():
                if not details.get("passed", True):
                    findings.append({
                        "rule": f"IMO A.749 ({name})",
                        "status": "FAIL",
                        "severity": "error",
                        "notes": f"{name}: {details.get('value', 'N/A')} (required: {details.get('required', 'N/A')})",
                    })

        return findings

    def _determine_vote(
        self,
        findings: List[Dict[str, Any]],
        semantic_result: Optional[ValidationResult],
        bounds_violations: List[BoundsCheckResult],
    ) -> tuple[VoteType, float, List[str]]:
        """Determine vote based on review findings."""
        errors = []
        warnings = []

        # Count structural/stability findings
        for f in findings:
            if f.get("severity") == "error" or f.get("status") == "FAIL":
                errors.append(f.get("notes", ""))
            elif f.get("severity") == "warning":
                warnings.append(f.get("notes", ""))

        # Add semantic validation errors
        if semantic_result:
            for issue in semantic_result.errors:
                errors.append(str(issue))
            for issue in semantic_result.warnings:
                warnings.append(str(issue))

        # Add bounds violations
        for violation in bounds_violations:
            if not violation.in_bounds:
                if violation.severity == "error":
                    errors.append(violation.message)
                else:
                    warnings.append(violation.message)

        # Determine vote
        if len(errors) > 0:
            vote = VoteType.REJECT
            confidence = 0.9  # High confidence in rejection
        elif len(warnings) > 3:
            vote = VoteType.REVISE
            confidence = 0.5  # Too many warnings to approve
        elif len(warnings) > 0:
            vote = VoteType.APPROVE
            confidence = 0.7  # Approve with reservations
        else:
            vote = VoteType.APPROVE
            confidence = 0.9  # Full approval

        concerns = errors + warnings[:3]  # Top concerns

        return vote, confidence, concerns

    def review_design(
        self,
        design_data: Optional[Dict[str, Dict]] = None,
    ) -> AgentResponse:
        """
        Review current design against classification requirements.

        Args:
            design_data: Optional dict of design data (reads from memory if not provided)

        Returns:
            AgentResponse with review findings and vote
        """
        # Read from memory if not provided
        if design_data is None:
            design_data = self._read_design_data()

        mission = design_data.get("mission")
        hull = design_data.get("hull_params")
        stability = design_data.get("stability_results")
        structural = design_data.get("structural_design")
        resistance = design_data.get("resistance_results")

        all_findings = []
        concerns = []

        # Run semantic validation
        semantic_result = self._run_semantic_validation(mission, hull, stability)

        # Run bounds validation
        bounds_results = self._run_bounds_validation(mission, hull, stability, resistance) or []
        bounds_violations = [b for b in bounds_results if not b.in_bounds]

        # Check structural compliance
        structural_findings = self._check_structural_compliance(structural)
        all_findings.extend(structural_findings)

        # Check stability compliance
        stability_findings = self._check_stability_compliance(stability)
        all_findings.extend(stability_findings)

        # Determine vote
        vote, confidence, vote_concerns = self._determine_vote(
            all_findings, semantic_result, bounds_violations
        )
        concerns.extend(vote_concerns)

        # Count passed/failed
        passed_count = sum(1 for f in all_findings if f.get("status") == "PASS")
        failed_count = sum(1 for f in all_findings if f.get("status") == "FAIL")
        incomplete_count = sum(1 for f in all_findings if f.get("status") == "INCOMPLETE")

        # Build review output
        review_output = {
            "standards": [s.value for s in self.standards],
            "vote": vote.value,
            "confidence": confidence,
            "summary": {
                "passed": passed_count,
                "failed": failed_count,
                "incomplete": incomplete_count,
                "warnings": len(bounds_violations),
            },
            "structural_findings": structural_findings,
            "stability_findings": stability_findings,
            "bounds_violations": [
                {"field": v.field, "message": v.message, "severity": v.severity}
                for v in bounds_violations
            ],
            "semantic_validation": semantic_result.to_dict() if semantic_result else None,
            "reviewed_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Write review to memory
        self.memory.write("reviews", review_output, validate=False)

        # Submit vote
        vote_schema = AgentVoteSchema(
            agent_id=self.agent_id,
            proposal_id="current_design",
            vote=vote,
            confidence=confidence,
            reasoning=f"Classification review: {passed_count} passed, {failed_count} failed",
            concerns=concerns[:5],
        )
        self.memory.append_vote(vote_schema)

        # Log decision
        self.log_decision({
            "action": "classification_review",
            "vote": vote.value,
            "passed": passed_count,
            "failed": failed_count,
            "confidence": confidence,
        })

        # Build response content
        vote_emoji = {"approve": "✓", "reject": "✗", "abstain": "○"}.get(vote.value, "?")
        content = (
            f"Classification Review [{vote_emoji} {vote.value.upper()}]: "
            f"{passed_count} passed, {failed_count} failed | "
            f"Standards: {', '.join(s.value for s in self.standards)}"
        )

        return AgentResponse(
            agent_id=self.agent_id,
            content=content,
            confidence=confidence,
            reasoning=f"Reviewed against {len(self.standards)} classification standards",
            proposals=[review_output],
            concerns=concerns,
            metadata={
                "vote": vote.value,
                "passed": passed_count,
                "failed": failed_count,
                "incomplete": incomplete_count,
                "standards": [s.value for s in self.standards],
            },
        )

    def vote_on_proposal(
        self,
        proposal_id: str,
        proposal_data: Dict[str, Any],
    ) -> AgentVoteSchema:
        """
        Vote on a specific proposal.

        Args:
            proposal_id: Unique proposal identifier
            proposal_data: Proposal content to review

        Returns:
            AgentVoteSchema with vote decision
        """
        # For now, run full design review
        response = self.review_design({"proposal": proposal_data})

        vote = VoteType(response.metadata.get("vote", "abstain"))

        return AgentVoteSchema(
            agent_id=self.agent_id,
            proposal_id=proposal_id,
            vote=vote,
            confidence=response.confidence,
            reasoning=response.reasoning,
            concerns=response.concerns,
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Optional design data or empty to read from memory

        Returns:
            AgentResponse with classification review
        """
        design_data = input_data if input_data else None
        return self.review_design(design_data)


# Convenience function
def create_class_reviewer(
    memory_path: str = "memory",
    standards: List[ComplianceStandard] = None,
    **kwargs
) -> ClassReviewerAgent:
    """Create a Class Reviewer agent instance."""
    return ClassReviewerAgent(memory_path=memory_path, standards=standards, **kwargs)
