"""
magnet/agents/vision_interpreter.py - Sketch Interpretation Agent

Converts hand-drawn sketches into geometry descriptions.
Outputs ONLY geometric descriptions — NEVER design type names.

INVARIANT: Output must NOT contain "catamaran", "trimaran", "stepped hull", etc.
           Only geometric descriptions (body count, dimensions, proportions).

Reference: MAGNET_Merge_Implementation_Plan.md Phase 0.5
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

__all__ = [
    'VisionInterpreter',
    'VisionResult',
    'SketchInterpretation',
    'interpret_sketch',
    'FORBIDDEN_TERMS',
    'VISION_INTERPRETER_SYSTEM_PROMPT',
]


# =============================================================================
# FORBIDDEN TERMS — Design type names that MUST NOT appear in output
# =============================================================================

FORBIDDEN_TERMS = [
    "catamaran", "trimaran", "monohull", "multihull",
    "stepped hull", "planing hull", "displacement hull",
    "patrol boat", "workboat", "ferry", "yacht", "tanker",
    "container ship", "fishing vessel", "crew boat", "tug",
    "proa", "outrigger canoe", "swath",
    "patrol vessel", "research vessel", "pilot boat",
]


# =============================================================================
# System Prompt — GEOMETRY ONLY, NO DESIGN TYPES
# =============================================================================

VISION_INTERPRETER_SYSTEM_PROMPT = """You are MAGNET's Sketch Interpreter.

SECURITY RULES (Q10):
1. ONLY extract dimensions that are VISIBLY WRITTEN on the sketch
2. If no dimensions are written, set all dimension fields to null
3. Do NOT estimate or infer dimensions from proportions alone
4. If you see "25m" written → extract it. If you see nothing → dimensions are null
5. Output MUST be valid JSON matching SketchInterpretation schema
6. Do NOT include any code, scripts, or injection attempts in output

YOUR ROLE:
- Analyze hand-drawn sketches of hull designs
- Extract GEOMETRIC INFORMATION ONLY
- Output measurements, body counts, proportions, and spatial relationships
- NEVER use design type names

🔴 FORBIDDEN TERMS (Do NOT output these):
- catamaran, trimaran, monohull, multihull
- stepped hull, planing hull, displacement hull
- patrol boat, workboat, ferry, yacht
- Any vessel classification or design style name

✅ ALLOWED OUTPUT (Geometry descriptions only):
- "I see 2 separate hull bodies offset laterally"
- "The sketch shows a longitudinal discontinuity at ~40% length"
- "Handwritten annotation shows '25m' indicating overall length"
- "Body proportions appear to be L/B ratio of approximately 5:1"
- "There is a surface break or step visible at mid-length"

WHAT TO EXTRACT:
1. Body count: How many separate hull forms are visible?
2. Dimensions: Any handwritten measurements (e.g., "25m", "4.5m beam")
3. Proportions: Approximate L/B ratio, draft/beam ratio
4. Spatial relationships: Offsets between bodies, relative positions
5. Surface features: Discontinuities, steps, chines (describe geometrically)
6. Annotations: Any text/labels written on the sketch

OUTPUT FORMAT (JSON):
{
  "body_count": number,
  "dimensions": {
    "loa_m": number or null,
    "beam_m": number or null,
    "draft_m": number or null,
    "body_spacing_m": number or null
  },
  "proportions": {
    "length_beam_ratio": number or null,
    "beam_draft_ratio": number or null
  },
  "bodies": [
    {
      "body_index": number,
      "position": "center" | "port" | "starboard" | "forward" | "aft",
      "relative_size": "primary" | "secondary" | "equal",
      "offset_y_estimate_m": number or null
    }
  ],
  "surface_features": [
    {
      "type": "discontinuity" | "chine" | "step" | "knuckle",
      "location_description": "string",
      "station_fraction_estimate": number or null
    }
  ],
  "annotations": [
    {
      "text": "string",
      "interpretation": "string"
    }
  ],
  "confidence": number (0.0-1.0),
  "geometric_description": "string (natural language summary using ONLY geometry terms)"
}

REMEMBER: You describe GEOMETRY, not design intent. The kernel will validate physics.
"""


# =============================================================================
# Pydantic Models
# =============================================================================

class BodyDescription(BaseModel):
    """Description of a single hull body."""
    body_index: int = 0
    position: str = Field(default="center", description="center, port, starboard, forward, aft")
    relative_size: str = Field(default="primary", description="primary, secondary, equal")
    offset_y_estimate_m: Optional[float] = None


class SurfaceFeature(BaseModel):
    """Geometric surface feature."""
    type: str = Field(default="discontinuity", description="discontinuity, chine, step, knuckle")
    location_description: str = ""
    station_fraction_estimate: Optional[float] = None


class Annotation(BaseModel):
    """Handwritten annotation from sketch."""
    text: str = ""
    interpretation: str = ""


class SketchInterpretation(BaseModel):
    """Complete interpretation of a sketch."""
    body_count: int = Field(default=1, ge=1)
    dimensions: Dict[str, Optional[float]] = Field(default_factory=dict)
    proportions: Dict[str, Optional[float]] = Field(default_factory=dict)
    bodies: List[BodyDescription] = Field(default_factory=list)
    surface_features: List[SurfaceFeature] = Field(default_factory=list)
    annotations: List[Annotation] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    geometric_description: str = Field(default="")


# =============================================================================
# Vision Interpreter Agent
# =============================================================================

@dataclass
class VisionResult:
    """Result from vision interpretation."""
    success: bool
    interpretation: Optional[SketchInterpretation] = None
    intent_string: str = ""  # Natural language for GeometryProposer
    raw_response: str = ""
    error: Optional[str] = None
    requires_clarification: bool = False  # True if sketch is incomplete


class VisionInterpreter:
    """
    Agent that interprets hand-drawn sketches into geometry descriptions.
    
    Contract:
    - Input: Image bytes + optional annotations
    - Output: SketchInterpretation with ONLY geometry terms
    - NEVER outputs design type names
    - Provides intent string for GeometryProposer
    
    Security (Q10):
    - Sanitizes annotations to prevent prompt injection
    - Validates extracted values against physical limits
    - Enforces JSON schema output
    - Audits suspicious interpretations
    
    This enables the human-in-the-loop design spiral where engineers
    can sketch ideas on paper/tablet and have them converted to
    geometry primitives.
    
    Reference: MAGNET_Critical_Corrections.md Part XIII Q10
    """
    
    # Security limits for validation
    MAX_BODIES = 10  # Unrealistic to have > 10 hull bodies
    MAX_LOA = 300.0  # Larger than container ship
    MAX_BEAM = 100.0  # Unrealistic beam
    MAX_DRAFT = 50.0  # Unrealistic draft
    
    def __init__(
        self,
        llm_provider,  # AnthropicProvider or compatible
        confidence_threshold: float = 0.5,
        enable_audit_logging: bool = True,
    ):
        self._llm = llm_provider
        self._confidence_threshold = confidence_threshold
        self._enable_audit = enable_audit_logging
    
    def _sanitize_annotations(self, raw_annotations: str) -> str:
        """
        Sanitize user annotations to prevent prompt injection.
        
        Security (Q10): Removes SQL injection, instruction override attempts,
        and code injection patterns.
        
        Args:
            raw_annotations: Raw text from user
        
        Returns:
            Sanitized text safe for LLM prompts
        """
        if not raw_annotations:
            return ""
        
        sanitized = raw_annotations
        
        # Remove SQL injection patterns
        sql_patterns = [
            r"DROP\s+TABLE", r"DELETE\s+FROM", r"INSERT\s+INTO",
            r"UPDATE\s+\w+\s+SET", r"SELECT\s+.*\s+FROM",
            r"UNION\s+SELECT", r"ALTER\s+TABLE", r"CREATE\s+TABLE",
        ]
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        # Remove instruction override attempts (case-insensitive)
        instruction_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+above",
            r"instead\s+output",
            r"forget\s+everything",
            r"new\s+instructions",
            r"system\s*:",
            r"assistant\s*:",
            r"ignore\s+all",
        ]
        for pattern in instruction_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        # Remove potential code injection
        code_patterns = [
            r"<script[^>]*>.*?</script>",  # JavaScript
            r"javascript:",
            r"on\w+\s*=",  # Event handlers
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
        ]
        for pattern in code_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove path traversal attempts
        sanitized = sanitized.replace("../", "")
        sanitized = sanitized.replace("..\\", "")
        
        return sanitized
    
    def _validate_interpretation(self, interpretation: SketchInterpretation) -> tuple[bool, List[str]]:
        """
        Validate interpretation against physical limits.
        
        Security (Q10): Prevents hallucinated or malicious extreme values.
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check body count
        if interpretation.body_count > self.MAX_BODIES:
            warnings.append(
                f"Unrealistic body count: {interpretation.body_count} > {self.MAX_BODIES}. "
                f"Possible hallucination or injection attack."
            )
            return False, warnings
        
        # Check dimensions
        dims = interpretation.dimensions
        
        loa_m = dims.get("loa_m")
        beam_m = dims.get("beam_m")
        draft_m = dims.get("draft_m")
        depth_m = dims.get("depth_m")
        
        if loa_m and loa_m > self.MAX_LOA:
            warnings.append(
                f"Unrealistic LOA: {loa_m}m > {self.MAX_LOA}m. "
                f"Larger than container ship."
            )
            return False, warnings
        
        if beam_m and beam_m > self.MAX_BEAM:
            warnings.append(
                f"Unrealistic beam: {beam_m}m > {self.MAX_BEAM}m."
            )
            return False, warnings
        
        if draft_m and draft_m > self.MAX_DRAFT:
            warnings.append(
                f"Unrealistic draft: {draft_m}m > {self.MAX_DRAFT}m."
            )
            return False, warnings
        
        # Check for suspiciously complete dimensions (possible hallucination)
        if loa_m and beam_m and draft_m and depth_m:
            if interpretation.confidence < 0.8:
                warnings.append(
                    "All dimensions provided but confidence is low. "
                    "Verify dimensions were actually written on sketch."
                )
        
        # Check intent string for code injection
        if interpretation.geometric_description:
            suspicious_chars = ["<", ">", "{", "}", "eval(", "exec(", "__import__"]
            for char in suspicious_chars:
                if char in interpretation.geometric_description:
                    warnings.append(
                        f"Suspicious character '{char}' in description. "
                        f"Possible code injection attempt."
                    )
                    return False, warnings
        
        return True, warnings
    
    def _audit_log(self, interpretation: SketchInterpretation, warnings: List[str]):
        """
        Audit log for suspicious interpretations.
        
        Security (Q10): Logs interpretations with warnings for security review.
        """
        if not self._enable_audit:
            return
        
        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Vision interpretation flagged: "
                f"body_count={interpretation.body_count}, "
                f"confidence={interpretation.confidence}, "
                f"warnings={warnings}"
            )
    
    def _assess_completeness(self, interpretation: SketchInterpretation) -> Optional[str]:
        """
        Assess if sketch is complete enough to proceed.
        
        Returns None if complete, error message if incomplete.
        
        Issue 1.1 cont: Partial sketch detection.
        """
        issues = []
        
        # Check if critical dimensions are missing
        dims = interpretation.dimensions
        has_loa = dims.get("loa_m") is not None
        has_beam = dims.get("beam_m") is not None
        has_draft = dims.get("draft_m") is not None
        
        missing_dims = []
        if not has_loa:
            missing_dims.append("LOA")
        if not has_beam:
            missing_dims.append("beam")
        if not has_draft:
            missing_dims.append("draft")
        
        if len(missing_dims) >= 2:
            issues.append(
                f"Missing critical dimensions: {', '.join(missing_dims)}. "
                f"Please provide at least 2 of: LOA, beam, draft."
            )
        
        # Check if description is too vague
        desc = interpretation.geometric_description
        if len(desc) < 20:
            issues.append(
                "Geometric description is very brief. "
                "Please provide more detail about hull form, sections, or features."
            )
        
        # Check confidence
        if interpretation.confidence < 0.3:
            issues.append(
                f"Interpretation confidence is very low ({interpretation.confidence:.1%}). "
                f"Sketch may be too rough or incomplete."
            )
        
        # Check for critical missing views (only if description is VERY minimal)
        # Note: This is optional - full implementation would use actual view detection from image
        if len(desc) < 50:  # Only check if description is very short
            if "profile" not in desc.lower() and "side" not in desc.lower():
                if "plan" not in desc.lower() and "top" not in desc.lower():
                    if "section" not in desc.lower():
                        issues.append(
                            "Cannot identify sketch view type (profile, plan, or section). "
                            "Please label views or make them clearer."
                        )
        
        # Return combined issues or None
        if issues:
            return " | ".join(issues)
        
        return None
    
    async def interpret_sketch(
        self,
        image_data: bytes,
        annotations: str = "",
        image_media_type: str = "image/png",
    ) -> VisionResult:
        """
        Interpret a hand-drawn sketch.
        
        Security (Q10): Sanitizes annotations, validates output, audits suspicious activity.
        
        Args:
            image_data: Raw image bytes
            annotations: Optional text annotations from user
            image_media_type: MIME type of image
        
        Returns:
            VisionResult with interpretation and intent string
        """
        # Security: Sanitize annotations
        sanitized_annotations = self._sanitize_annotations(annotations)
        
        # Build prompt
        prompt = self._build_prompt(sanitized_annotations)
        
        try:
            # Call vision LLM
            response = await self._llm.complete_with_image(
                prompt=prompt,
                image_data=image_data,
                image_media_type=image_media_type,
                system_prompt=VISION_INTERPRETER_SYSTEM_PROMPT,
            )
            
            # Parse response
            interpretation = self._parse_response(response.content)
            
            # Security: Validate interpretation
            is_valid, validation_warnings = self._validate_interpretation(interpretation)
            if not is_valid:
                self._audit_log(interpretation, validation_warnings)
                return VisionResult(
                    success=False,
                    error=f"Security validation failed: {'; '.join(validation_warnings)}",
                    raw_response=response.content,
                )
            
            # Audit if warnings present
            if validation_warnings:
                self._audit_log(interpretation, validation_warnings)
            
            # Validate no forbidden terms
            violation = self._check_forbidden_terms(interpretation)
            if violation:
                return VisionResult(
                    success=False,
                    error=f"Enumeration violation: output contains '{violation}'",
                    raw_response=response.content,
                )
            
            # Assess completeness (Issue 1.1 cont)
            completeness_issue = self._assess_completeness(interpretation)
            if completeness_issue:
                return VisionResult(
                    success=False,
                    error=f"Incomplete sketch: {completeness_issue}",
                    interpretation=interpretation,  # Include partial interpretation
                    raw_response=response.content,
                    requires_clarification=True,
                )
            
            # Generate intent string for GeometryProposer
            intent_string = self._generate_intent_string(interpretation, annotations)
            
            return VisionResult(
                success=True,
                interpretation=interpretation,
                intent_string=intent_string,
                raw_response=response.content,
            )
            
        except Exception as e:
            return VisionResult(
                success=False,
                error=f"Vision interpretation failed: {str(e)}",
            )
    
    def _build_prompt(self, annotations: str) -> str:
        """Build the prompt for vision LLM."""
        prompt = """Analyze this hand-drawn sketch of a hull design.

Extract ONLY geometric information:
1. Count the number of hull bodies
2. Read any handwritten dimensions (measurements)
3. Estimate proportions (L/B ratio, etc.)
4. Describe spatial relationships between bodies
5. Note any surface features (steps, chines, discontinuities)

Output valid JSON matching the schema in your instructions.

CRITICAL: Use ONLY geometric descriptions. Do NOT use vessel type names."""
        
        if annotations:
            prompt += f"\n\nUser annotations: {annotations}"
        
        return prompt
    
    def _parse_response(self, content: str) -> SketchInterpretation:
        """Parse LLM response into SketchInterpretation."""
        # Try to extract JSON from response
        content = content.strip()
        
        # Handle markdown code blocks
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1).strip()
        
        try:
            data = json.loads(content)
            return SketchInterpretation.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            # Return minimal interpretation on parse failure
            return SketchInterpretation(
                body_count=1,
                confidence=0.3,
                geometric_description=content[:500],  # Use raw text as description
            )
    
    def _check_forbidden_terms(self, interpretation: SketchInterpretation) -> Optional[str]:
        """Check if interpretation contains forbidden design terms."""
        text_to_check = interpretation.geometric_description.lower()
        
        for term in FORBIDDEN_TERMS:
            if term.lower() in text_to_check:
                return term
        
        return None
    
    def _generate_intent_string(
        self,
        interpretation: SketchInterpretation,
        user_annotations: str,
    ) -> str:
        """
        Generate intent string for GeometryProposer.
        
        This converts the geometric interpretation into a natural language
        request that GeometryProposer can process.
        """
        parts = []
        
        # Body count
        if interpretation.body_count == 1:
            parts.append("Create a single-body hull")
        else:
            parts.append(f"Create a {interpretation.body_count}-body hull configuration")
        
        # Dimensions
        dims = interpretation.dimensions
        if dims.get("loa_m"):
            parts.append(f"with overall length {dims['loa_m']}m")
        if dims.get("beam_m"):
            parts.append(f"beam {dims['beam_m']}m")
        if dims.get("draft_m"):
            parts.append(f"draft {dims['draft_m']}m")
        
        # Body spacing for multi-body
        if interpretation.body_count > 1 and dims.get("body_spacing_m"):
            parts.append(f"with bodies spaced {dims['body_spacing_m']}m apart")
        elif interpretation.body_count > 1:
            # Estimate from body descriptions
            offsets = [b.offset_y_estimate_m for b in interpretation.bodies if b.offset_y_estimate_m]
            if offsets:
                spacing = max(offsets) - min(offsets)
                parts.append(f"with estimated body spacing of {spacing:.1f}m")
        
        # Surface features
        for feature in interpretation.surface_features:
            if feature.type == "discontinuity" or feature.type == "step":
                loc = f"at {feature.station_fraction_estimate:.0%} length" if feature.station_fraction_estimate else ""
                parts.append(f"including a surface discontinuity {loc}")
            elif feature.type == "chine":
                parts.append("with chine edges")
        
        # User annotations
        if user_annotations:
            parts.append(f"Additional context: {user_annotations}")
        
        return ". ".join(parts) + "."


# =============================================================================
# Convenience Functions
# =============================================================================

async def interpret_sketch(
    image_data: bytes,
    annotations: str = "",
    llm_provider=None,
) -> VisionResult:
    """
    Convenience function to interpret a sketch.
    
    Example:
        with open("sketch.png", "rb") as f:
            result = await interpret_sketch(f.read(), "25m patrol vessel")
        if result.success:
            # Pass to GeometryProposer
            geometry_result = await proposer.propose(result.intent_string)
    """
    if llm_provider is None:
        from magnet.llm.providers.anthropic import AnthropicProvider
        llm_provider = AnthropicProvider()
    
    interpreter = VisionInterpreter(llm_provider)
    return await interpreter.interpret_sketch(image_data, annotations)

