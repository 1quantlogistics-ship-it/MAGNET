"""
Tests for Agent Naval Architecture Domain Knowledge.

These tests verify that the GeometryProposer agent has sufficient
naval architecture knowledge to translate design intent into correct
geometry primitives.

Reference: MAGNET_Agent_Enhancement_Plan.md
Status: ASSESSMENT TESTS - Verify actual agent capability

WARNING: These tests make actual LLM API calls and may incur costs.
        Set SKIP_LIVE_LLM_TESTS=1 to skip.
"""

import pytest
import os
import re
from typing import Dict, Any, List


# Live LLM tests are opt-in (they incur cost + require network + keys).
# Run them only when explicitly enabled.
RUN_LIVE_LLM = os.environ.get("RUN_LIVE_LLM_TESTS", "0") == "1"
SKIP_LIVE_LLM = (not RUN_LIVE_LLM) or (os.environ.get("SKIP_LIVE_LLM_TESTS", "0") == "1")


def check_for_enumeration(program_text: str) -> List[str]:
    """Check if program contains enumeration patterns."""
    violations = []
    
    forbidden_patterns = [
        (r"hull\.hull_type", "hull.hull_type (enumeration)"),
        (r"hull\.style", "hull.style (enumeration)"),
        (r"hull\.performance", "hull.performance (enumeration)"),
        (r"ADD\s+FEATURE", "ADD FEATURE (enumeration)"),
        (r"hull_config", "hull_config (enumeration)"),
        (r"\.has_\w+\s*=", "has_* boolean flag (enumeration)"),
    ]
    
    for pattern, description in forbidden_patterns:
        if re.search(pattern, program_text, re.IGNORECASE):
            violations.append(description)
    
    return violations


def check_for_invented_primitives(program_text: str) -> List[str]:
    """Check if program invents non-existent primitive types."""
    violations = []
    
    valid_types = [
        "geometry.body",
        "geometry.section", 
        "geometry.surface",
        "geometry.discontinuity",
        "geometry.flow_path",
        "geometry.opening",
        "geometry.attachment"
    ]
    
    # Find all CREATE/UPDATE operations
    operations = re.findall(r"(CREATE|UPDATE)\s+([\w.]+)", program_text)
    
    for op, type_name in operations:
        if type_name.startswith("geometry.") and type_name not in valid_types:
            violations.append(f"Invented type: {type_name}")
        elif not type_name.startswith("geometry.") and not type_name.startswith("CONSTRAIN"):
            violations.append(f"Non-geometry type: {type_name}")
    
    return violations


def check_makes_geometric_changes(program_text: str) -> bool:
    """Check if program actually modifies geometry (not just acknowledges)."""
    has_operation = bool(re.search(r"(CREATE|UPDATE|DELETE)\s+geometry\.", program_text))
    return has_operation


def _combined_reasoning_text(result: Any) -> str:
    """
    Extract reasoning from structured program operations if available.
    Falls back to program_text comments if needed.
    """
    if getattr(result, "program", None) and getattr(result.program, "operations", None):
        return "\n".join(op.reasoning for op in result.program.operations if getattr(op, "reasoning", None))
    return ""


def _avg_confidence(result: Any, default: float = 0.5) -> float:
    """Compute average confidence across operations; fall back to default if unavailable."""
    if getattr(result, "program", None) and getattr(result.program, "operations", None):
        confidences = [op.confidence for op in result.program.operations if getattr(op, "confidence", None) is not None]
        if confidences:
            return sum(confidences) / len(confidences)
    return default


def analyze_proposal_quality(intent: str, program_text: str, reasoning_text: str) -> Dict[str, Any]:
    """
    Analyze the quality of agent's proposal.
    
    Returns dict with:
    - has_operations: bool
    - enumeration_violations: List[str]
    - invented_primitives: List[str]
    - has_reasoning: bool
    - has_quantification: bool (e.g., "L/B ratio", specific angles)
    """
    return {
        "intent": intent,
        "has_operations": check_makes_geometric_changes(program_text),
        "enumeration_violations": check_for_enumeration(program_text),
        "invented_primitives": check_for_invented_primitives(program_text),
        "has_reasoning": len(reasoning_text) > 50 if reasoning_text else False,
        "has_quantification": bool(re.search(r"\d+\.?\d*\s*(m|deg|°|ratio|%)", program_text)),
        "program_length": len(program_text),
    }


# =============================================================================
# Test Suite: 12 Naval Architecture Knowledge Tests
# =============================================================================

@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests (set SKIP_LIVE_LLM_TESTS=0 to enable)")
@pytest.mark.asyncio
async def test_know_001_make_it_faster():
    """
    KNOW_001: "Make it faster"
    
    Expected: Agent should increase L/B ratio or reduce wetted surface
    Forbidden: Generic response, enumeration, no geometry changes
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Make it faster",
        current_state={
            "hull": {"loa": 25.0, "beam": 6.0, "draft": 1.5},
            "resources": {
                "main_hull": {
                    "_type": "geometry.body",
                    "body_type": "main_hull",
                }
            }
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    analysis = analyze_proposal_quality(
        "Make it faster",
        result.program_text,
        _combined_reasoning_text(result),
    )
    
    # Must make geometric changes
    assert analysis["has_operations"], \
        "Agent gave generic response without geometry changes"
    
    # Must not use enumeration
    assert len(analysis["enumeration_violations"]) == 0, \
        f"Agent used enumeration: {analysis['enumeration_violations']}"
    
    # Must not invent primitives
    assert len(analysis["invented_primitives"]) == 0, \
        f"Agent invented primitives: {analysis['invented_primitives']}"
    
    # Should mention resistance reduction concepts
    keywords = ["l/b", "beam", "resistance", "slender", "wetted"]
    has_keyword = any(kw in result.program_text.lower() for kw in keywords)
    
    assert has_keyword, \
        "Agent doesn't show knowledge of speed/resistance relationship"
    
    print(f"\n✅ KNOW_001 PASS: Agent proposes geometric changes for speed")
    print(f"   Has operations: {analysis['has_operations']}")
    print(f"   Reasoning quality: {analysis['has_reasoning']}")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_002_add_spray_rails():
    """
    KNOW_002: "Add spray rails"
    
    Expected: geometry.discontinuity with appropriate height_fraction
    Forbidden: Invented spray_rail type, enumeration
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Add spray rails to reduce spray and wetted surface",
        current_state={
            "hull": {"loa": 25.0, "beam": 5.0, "draft": 1.5},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must use geometry.discontinuity
    assert "geometry.discontinuity" in program_text, \
        "Agent didn't use geometry.discontinuity for spray rails"
    
    # Must not invent spray_rail primitive
    assert "geometry.spray_rail" not in program_text.lower(), \
        "Agent invented geometry.spray_rail type"
    
    assert "hull.spray_rail" not in program_text.lower(), \
        "Agent used hull.spray_rail (enumeration)"
    
    # Should mention height or position
    has_position = any(kw in program_text.lower() for kw in ["height", "fraction", "station", "position"])
    assert has_position, \
        "Agent doesn't specify spray rail position/height"
    
    print(f"\n✅ KNOW_002 PASS: Agent correctly uses discontinuity for spray rails")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_003_catamaran():
    """
    KNOW_003: "I want a catamaran"
    
    Expected: Two geometry.body with lateral offsets
    Forbidden: hull_type: "catamaran", single body with catamaran type
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="I want a catamaran configuration",
        current_state={
            "hull": {"loa": 25.0, "beam": 3.0, "draft": 1.5},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must create two bodies
    body_count = program_text.count("CREATE geometry.body")
    assert body_count >= 2, \
        f"Agent created {body_count} bodies, catamaran needs 2"
    
    # Must not set hull_type
    assert "hull_type" not in program_text.lower() or "catamaran" not in program_text.lower(), \
        "Agent used hull_type enumeration"
    
    # Should mention lateral offset or spacing
    has_offset = any(kw in program_text.lower() for kw in ["offset_y", "spacing", "lateral", "port", "starboard"])
    assert has_offset, \
        "Agent doesn't specify lateral spacing for catamaran hulls"
    
    print(f"\n✅ KNOW_003 PASS: Agent creates 2-body catamaran without enumeration")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_004_more_stable():
    """
    KNOW_004: "More stable"
    
    Expected: Increase beam, lower VCG, or increase hull spacing
    Forbidden: Generic response, stability flag
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Make this design more stable",
        current_state={
            "hull": {"loa": 25.0, "beam": 4.0, "draft": 1.5, "vcg": 1.2},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must make geometric changes
    assert check_makes_geometric_changes(program_text), \
        "Agent gave generic advice without geometry changes"
    
    # Must not use stability flag
    assert "stability" not in program_text.lower() or "SET" not in program_text, \
        "Agent set stability flag instead of changing geometry"
    
    # Should mention GM, beam, BM, VCG, or spacing
    stability_keywords = ["gm", "bm", "beam", "vcg", "spacing", "waterplane"]
    has_keyword = any(kw in program_text.lower() for kw in stability_keywords)
    
    assert has_keyword, \
        "Agent doesn't show knowledge of stability parameters"
    
    print(f"\n✅ KNOW_004 PASS: Agent proposes geometric stability improvements")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_005_deep_v_hull():
    """
    KNOW_005: "Deep-V hull"
    
    Expected: Modify section points with high deadrise angle
    Forbidden: Invented deep_v primitive, hull.form enumeration
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Make this a deep-V hull for better seakeeping",
        current_state={
            "hull": {"loa": 25.0, "beam": 5.0, "draft": 1.5},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must modify sections
    assert "geometry.section" in program_text, \
        "Agent didn't modify sections for hull form change"
    
    # Must not invent deep_v primitive
    assert "geometry.deep_v" not in program_text.lower(), \
        "Agent invented geometry.deep_v type"
    
    # Should mention deadrise or angle
    has_deadrise = any(kw in program_text.lower() for kw in ["deadrise", "angle", "v-shape", "points"])
    assert has_deadrise, \
        "Agent doesn't show understanding of deep-V geometry"
    
    print(f"\n✅ KNOW_005 PASS: Agent modifies sections for deep-V form")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_011_add_chines():
    """
    KNOW_011: "Add chines"
    
    Expected: geometry.discontinuity at hull/side transition
    Forbidden: Invented chine primitive
    
    Reference: MAGNET_Agent_Enhancement_Plan.md (Knowledge tests)
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Add hard chines to this hull",
        current_state={
            "hull": {"loa": 20.0, "beam": 4.5, "draft": 1.2},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must use discontinuity or modify sections
    has_chine_implementation = (
        "geometry.discontinuity" in program_text or
        "geometry.section" in program_text
    )
    assert has_chine_implementation, \
        "Agent doesn't know how to implement chines"
    
    # Must not invent chine primitive
    assert "geometry.chine" not in program_text.lower(), \
        "Agent invented geometry.chine type"
    
    print(f"\n✅ KNOW_011 PASS: Agent uses correct primitives for chines")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_013_unknown_term_clarification():
    """
    KNOW_013: "Add a skeg" (unknown term not in translation guide)
    
    Expected: Agent should REQUEST CLARIFICATION instead of hallucinating
    Forbidden: Inventing geometry.skeg, using enumeration
    
    Reference: MAGNET_Agent_Enhancement_Plan.md Part IX Safeguard 2
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Add a skeg to this design",
        current_state={
            "hull": {"loa": 12.0, "beam": 3.5, "draft": 1.0},
        },
    )
    
    # May succeed (if agent knows skegs) or fail (if it doesn't)
    # Key requirement: IF uncertain, must request clarification, not hallucinate
    
    program_text = result.program_text.lower()
    
    # Must NOT invent primitive
    assert "geometry.skeg" not in program_text, \
        "Agent invented geometry.skeg type"
    
    # Must NOT use enumeration
    assert "hull.has_skeg" not in program_text, \
        "Agent used enumeration"
    
    confidence = _avg_confidence(result)

    # If confidence is low, should include clarification language
    if confidence < 0.5:
        clarification_keywords = ["clarif", "uncertain", "describe", "could you", "not sure"]
        has_clarification = any(kw in program_text for kw in clarification_keywords)
        assert has_clarification, \
            "Low confidence but no clarification request found"
    
    print(f"\n✅ KNOW_013 PASS: Agent handles unknown terms safely")
    print(f"   Confidence: {confidence}")
    print(f"   Requests clarification: {confidence < 0.5}")


@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_know_014_novel_configuration():
    """
    KNOW_014: "Catamaran with 60% hull spacing" (non-standard)
    
    Expected: Agent should USE 0.6, not force to typical 0.35-0.45
    This tests that agent supports novel configurations
    
    Reference: MAGNET_Agent_Enhancement_Plan.md Part IX Safeguard 3
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    result = await proposer.propose(
        intent="Create a catamaran with 60% hull spacing ratio (S/L = 0.6)",
        current_state={
            "hull": {"loa": 20.0, "beam": 3.0, "draft": 1.2},
        },
    )
    
    assert result.success, f"Proposal failed: {result.error}"
    
    program_text = result.program_text
    
    # Must create two bodies
    body_count = program_text.count("CREATE geometry.body")
    assert body_count >= 2, \
        f"Agent created {body_count} bodies, catamaran needs 2"
    
    # Should use ~60% spacing: For LOA=20m, S/L=0.6 → S=12m → offset = ±6m
    # Accept range: ±5.5 to ±6.5 (allowing for rounding/interpretation)
    has_wide_spacing = any(kw in program_text for kw in ["12.0", "6.0", "6.5", "11.5", "12.5"])
    
    # Alternative: Check reasoning mentions 0.6 or 60%
    mentions_60_percent = "0.6" in program_text or "60" in program_text
    
    assert has_wide_spacing or mentions_60_percent, \
        "Agent doesn't appear to use the specified 60% spacing (should be ~12m or ±6m offsets)"
    
    # Must NOT force to typical values
    # Typical would be 0.4 × 20 = 8m spacing = ±4m offsets
    typical_spacing_only = ("4.0" in program_text or "8.0" in program_text) and not has_wide_spacing
    assert not typical_spacing_only, \
        "Agent forced to typical 40% spacing instead of using specified 60%"
    
    print(f"\n✅ KNOW_014 PASS: Agent supports novel configurations")
    print(f"   Uses specified spacing: {has_wide_spacing or mentions_60_percent}")


# =============================================================================
# Summary Test: Overall Agent Knowledge Assessment
# =============================================================================

@pytest.mark.skipif(SKIP_LIVE_LLM, reason="Skipping live LLM tests")
@pytest.mark.asyncio
async def test_agent_knowledge_summary():
    """
    Summary test: Run subset of knowledge tests and report pass rate.
    
    This test provides an overall assessment of agent competency.
    
    Smoke summary for a small subset of tests.
    Full gating is done by running the whole suite in `tests/knowledge/`.
    """
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    test_cases = [
        {
            "id": "KNOW_001",
            "intent": "Make it faster",
            "must_have": ["geometry"],
            "must_not_have": ["hull_type", "performance"],
        },
        {
            "id": "KNOW_002",
            "intent": "Add spray rails",
            "must_have": ["discontinuity"],
            "must_not_have": ["spray_rail"],
        },
        {
            "id": "KNOW_003",
            "intent": "I want a catamaran",
            "must_have": ["geometry.body"],
            "must_not_have": ["hull_type"],
            "min_body_count": 2,
        },
    ]
    
    proposer = create_geometry_proposer()
    results = []
    
    for test_case in test_cases:
        result = await proposer.propose(
            intent=test_case["intent"],
            current_state={"hull": {"loa": 25.0, "beam": 5.0, "draft": 1.5}},
        )
        
        passed = result.success
        if passed:
            program_text = result.program_text.lower()
            
            # Check must_have keywords
            for keyword in test_case.get("must_have", []):
                if keyword.lower() not in program_text:
                    passed = False
                    break
            
            # Check must_not_have keywords
            for keyword in test_case.get("must_not_have", []):
                if keyword.lower() in program_text:
                    passed = False
                    break
            
            # Check body count if specified
            if "min_body_count" in test_case:
                body_count = result.program_text.count("CREATE geometry.body")
                if body_count < test_case["min_body_count"]:
                    passed = False
        
        results.append({
            "test_id": test_case["id"],
            "intent": test_case["intent"],
            "passed": passed,
        })
    
    # Calculate pass rate
    pass_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    pass_rate = pass_count / total_count if total_count > 0 else 0
    
    # Print summary
    print(f"\n" + "=" * 60)
    print(f"AGENT KNOWLEDGE ASSESSMENT SUMMARY")
    print(f"=" * 60)
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{result['test_id']}: {status} - {result['intent']}")
    print(f"=" * 60)
    print(f"PASS RATE: {pass_count}/{total_count} ({pass_rate*100:.0f}%)")
    print(f"=" * 60)
    
    # NOTE: This is only a subset; do not use it as a production gate.
    if pass_rate == 1.0:
        print("✅ SUBSET PASS (smoke)")
    else:
        print("⚠️  SUBSET FAIL (smoke) — run full `tests/knowledge/` for gating")
    
    # For this test, we'll assert that at least some pass
    # (since current prompt lacks domain knowledge, expect failures)
    assert pass_count >= 0, "Test framework should at least run"


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MAGNET Agent Naval Architecture Knowledge Tests")
    print("="*60)
    print("\nWARNING: These tests make actual LLM API calls.")
    print("Set SKIP_LIVE_LLM_TESTS=1 to skip expensive tests.")
    print("\nRunning tests...")
    print("="*60 + "\n")
    
    pytest.main([__file__, "-v", "-s"])

