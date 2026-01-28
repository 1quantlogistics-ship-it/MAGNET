"""
Chat-based iterative naval architecture design loop.

THIS IS THE NEW PATH — separate from intent_protocol.py.

Two systems coexist:
1. OLD: intent_protocol.py → parameter refinement → legacy synthesis
2. NEW: geometry_proposer.py → program_executor.py → compiler.py → HullGeometry

This module uses the NEW path exclusively. It does NOT map to intent_protocol.

Phase 6 Enhancement (MAGNET_Merge_Implementation_Plan.md):
- Uses CycleExecutor for propose→validate→revise loop
- Uses NarrativeGenerator for feedback
- Uses ClarificationManager for agent-human interaction

Reference: MAGNET_System_State_Analysis.md Parts XIII-XVI
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import json
import logging
import uuid

if TYPE_CHECKING:
    from magnet.protocol.cycle_executor import CycleExecutor
    from magnet.agents.clarification import ClarificationManager

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Message:
    """A message in the design conversation."""
    role: str  # "user" | "assistant" | "system" | "feedback"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignIteration:
    """One iteration of the design loop."""
    iteration_number: int
    user_request: str
    proposed_program: Optional[str] = None
    execution_result: Optional[Any] = None  # ExecutionResult
    metrics: Dict[str, float] = field(default_factory=dict)
    deltas: Dict[str, float] = field(default_factory=dict)
    feedback_to_user: str = ""
    success: bool = False


@dataclass
class ConversationState:
    """Full state of a design conversation."""
    conversation_id: str
    messages: List[Message] = field(default_factory=list)
    iterations: List[DesignIteration] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    current_geometry: Any = None
    metrics_history: List[Dict[str, float]] = field(default_factory=list)


# =============================================================================
# FEEDBACK GENERATION
# =============================================================================

def generate_feedback(
    result: Any,  # ExecutionResult
    previous_metrics: Optional[Dict[str, float]],
    iteration_num: int,
) -> str:
    """
    Generate human-readable feedback from validation results.
    """
    lines = []
    lines.append(f"## Iteration {iteration_num} Results\n")
    
    if not result.success:
        lines.append("**⚠️ Execution had issues:**")
        for err in result.errors:
            lines.append(f"- {err}")
        lines.append("")
    
    # Geometry summary
    if result.geometry:
        lines.append("### Geometry")
        lines.append(f"- Volume: {abs(result.geometry.volume):.1f} m³")
        n_sections = len(result.geometry.sections) if result.geometry.sections else 0
        lines.append(f"- Sections: {n_sections}")
        n_bodies = len(getattr(result.geometry, 'bodies', {}))
        if n_bodies > 1:
            lines.append(f"- Bodies: {n_bodies}")
        lines.append("")
    
    # Hydrostatics
    hydro = result.validation.get("hydrostatics", {})
    if hydro:
        lines.append("### Stability")
        gm = hydro.get("gm_m")
        if gm is not None:
            status = "✅" if gm >= 0.5 else "⚠️" if gm >= 0.15 else "❌"
            lines.append(f"- GM: {gm:.2f}m {status}")
            
            if previous_metrics and "gm_m" in previous_metrics:
                delta = gm - previous_metrics["gm_m"]
                direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
                lines.append(f"  (Δ {delta:+.2f}m {direction})")
        
        bm = hydro.get("bm_transverse_m")
        if bm:
            lines.append(f"- BM: {bm:.2f}m")
        
        method = hydro.get("method", "")
        if method:
            lines.append(f"- Method: {method}")
        lines.append("")
    
    # Constraint violations
    violations = result.validation.get("constraint_violations", [])
    if violations:
        lines.append("### ⚠️ Constraint Violations")
        for v in violations:
            lines.append(f"- {v.get('path', 'constraint')}: {v.get('actual'):.2f} (need {v.get('required')})")
        lines.append("")
    
    # Suggestions
    if hydro.get("gm_m") is not None:
        gm = hydro["gm_m"]
        if gm < 0.5:
            lines.append("### 💡 Suggestions")
            if gm < 0:
                lines.append("- Vessel is unstable! Consider: wider beam, lower VCG, or add ballast")
            else:
                lines.append("- GM is low. Consider: increasing beam or lowering center of gravity")
            lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# DESIGN CONVERSATION (Uses NEW path exclusively)
# =============================================================================

class DesignConversation:
    """
    Chat-based iterative design loop using the NEW geometry primitives path.
    
    THIS BYPASSES intent_protocol.py ENTIRELY.
    
    Phase 6 Enhancement:
    - Uses CycleExecutor for propose→validate→revise loop with transactions
    - Uses NarrativeGenerator for rich feedback
    - Uses ClarificationManager for agent-human interaction when confidence is low
    
    Flow:
    1. User provides natural language OR direct geometry DSL
    2. If natural language + LLM enabled: GeometryProposer translates to DSL
    3. If confidence < threshold: Request clarification via ClarificationManager
    4. DSL → CycleExecutor → program_executor → HullGeometry
    5. Validation runs (hydrostatics, resistance)
    6. NarrativeGenerator creates feedback with EnrichedDeltas
    7. User iterates
    
    No family/type priors. Pure geometry primitives.
    
    Reference: MAGNET_Merge_Implementation_Plan.md Phase 6
    """
    
    # Confidence threshold for requesting clarification
    CONFIDENCE_THRESHOLD = 0.6
    
    def __init__(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        use_llm: bool = True,
        clarification_manager: Optional["ClarificationManager"] = None,
        confidence_threshold: float = 0.6,
    ):
        """
        Initialize a design conversation.
        
        Args:
            initial_state: Starting state (hull parameters for validation context)
            conversation_id: Unique ID for this conversation
            use_llm: If True, use GeometryProposer for natural language translation
            clarification_manager: Optional ClarificationManager for human-in-the-loop
            confidence_threshold: Below this, request clarification
        """
        self._conversation_id = conversation_id or str(uuid.uuid4())
        self._state = ConversationState(
            conversation_id=self._conversation_id,
            current_state=initial_state or {"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
        )
        self._use_llm = use_llm
        self._clarification_manager = clarification_manager
        self._confidence_threshold = confidence_threshold
        self._pending_clarification: Optional[str] = None
    
    async def chat(
        self,
        user_message: str,
        constraints: Optional[List[str]] = None,
        vision_context: Optional[Dict[str, Any]] = None,
    ) -> DesignIteration:
        """
        Process a user message and return results.
        
        Accepts either:
        - Natural language (if use_llm=True): "Create a 25m twin hull vessel"
        - Direct DSL: "CREATE geometry.body main { body_type: \"hull\" }"
        - Clarification response (if pending clarification)
        
        Args:
            user_message: User's message (natural language or DSL)
            constraints: Optional design constraints
            vision_context: Optional vision interpreter results for reconciliation
        
        Returns:
            DesignIteration with results and feedback
        """
        from magnet.kernel.program_executor import execute_program, ExecutionResult
        
        iteration_num = len(self._state.iterations) + 1
        
        # Record user message
        self._state.messages.append(Message(
            role="user",
            content=user_message,
        ))
        
        # Check if this is a clarification response
        if self._pending_clarification:
            return await self._handle_clarification_response(user_message, iteration_num)
        
        # Step 1: Get program text (either direct DSL or via LLM)
        program_text, confidence = await self._get_program_text_with_confidence(user_message, constraints)
        
        # Step 1.5: Check if clarification needed (Phase 6 enhancement)
        if confidence < self._confidence_threshold and self._clarification_manager:
            return await self._request_clarification(
                user_message, 
                confidence, 
                iteration_num,
            )
        
        if not program_text:
            iteration = DesignIteration(
                iteration_number=iteration_num,
                user_request=user_message,
                proposed_program=None,
                execution_result=None,
                metrics={},
                deltas={},
                feedback_to_user="Could not translate request to geometry. Try providing direct DSL or be more specific.",
                success=False,
            )
            self._state.iterations.append(iteration)
            return iteration
        
        # Step 1.6: Agent Reconciliation (if vision context provided)
        if vision_context:
            reconciliation_issue = self._check_vision_dsl_reconciliation(
                program_text, vision_context
            )
            if reconciliation_issue and self._clarification_manager:
                return await self._request_reconciliation_clarification(
                    reconciliation_issue,
                    program_text,
                    vision_context,
                    iteration_num,
                )
        
        # Step 2: Execute via program_executor (NEW PATH)
        # This bypasses intent_protocol entirely
        result = execute_program(
            program_text=program_text,
            initial_state=self._state.current_state,
            validate=True,
        )
        
        # Step 3: Extract metrics and compute deltas
        current_metrics = self._extract_metrics(result)
        previous_metrics = self._state.metrics_history[-1] if self._state.metrics_history else None
        deltas = self._compute_deltas(current_metrics, previous_metrics)
        
        # Step 4: Update state if successful
        if result.success:
            self._update_state(result)
        
        # Record metrics
        self._state.metrics_history.append(current_metrics)
        
        # Step 5: Generate feedback using NarrativeGenerator (Phase 6)
        feedback = self._generate_narrative_feedback(result, previous_metrics, iteration_num)
        
        # Record feedback
        self._state.messages.append(Message(
            role="feedback",
            content=feedback,
        ))
        
        # Create iteration record
        iteration = DesignIteration(
            iteration_number=iteration_num,
            user_request=user_message,
            proposed_program=program_text,
            execution_result=result,
            metrics=current_metrics,
            deltas=deltas,
            feedback_to_user=feedback,
            success=result.success,
        )
        self._state.iterations.append(iteration)
        
        return iteration

    async def _request_clarification(
        self,
        original_message: str,
        confidence: float,
        iteration_num: int,
    ) -> DesignIteration:
        """
        Request clarification when confidence is low.
        
        Phase 6: ClarificationManager integration.
        """
        from magnet.agents.clarification import ClarificationRequest, AgentPriority
        
        # Store pending state
        self._pending_clarification = original_message
        
        # Create clarification request
        if self._clarification_manager:
            try:
                request = ClarificationRequest(
                    agent_id="geometry_proposer",
                    message=f"I'm {confidence:.0%} confident about this request. Could you clarify:\n\n"
                            f"'{original_message}'\n\n"
                            f"What specific geometry would you like? Options:\n"
                            f"- Single hull with specific dimensions\n"
                            f"- Multiple hull bodies (specify count and spacing)\n"
                            f"- Specific surface features (steps, chines)\n"
                            f"- Or provide direct DSL",
                    options=["Single hull", "Twin hull", "Triple hull", "Provide dimensions", "Use DSL"],
                    priority=AgentPriority.NORMAL,
                    context={"original_message": original_message, "confidence": confidence},
                )
                self._clarification_manager.add_request(request)
            except Exception as e:
                logger.warning(f"Could not create clarification request: {e}")
        
        feedback = (
            f"## Clarification Needed (Iteration {iteration_num})\n\n"
            f"I'm only {confidence:.0%} confident about your request:\n"
            f"> {original_message}\n\n"
            f"Please clarify:\n"
            f"- How many hull bodies? (1, 2, 3+)\n"
            f"- What are the approximate dimensions?\n"
            f"- Any special features? (steps, chines, openings)\n\n"
            f"Or provide direct geometry DSL."
        )
        
        iteration = DesignIteration(
            iteration_number=iteration_num,
            user_request=original_message,
            proposed_program=None,
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user=feedback,
            success=False,
        )
        self._state.iterations.append(iteration)
        
        return iteration

    async def _handle_clarification_response(
        self,
        response: str,
        iteration_num: int,
    ) -> DesignIteration:
        """
        Handle user's response to clarification request.
        """
        # Combine original message with clarification
        original = self._pending_clarification
        self._pending_clarification = None
        
        combined_message = f"{original}\n\nClarification: {response}"
        
        # Re-process with combined context
        return await self.chat(combined_message)

    def _generate_narrative_feedback(
        self,
        result: Any,
        previous_metrics: Optional[Dict[str, float]],
        iteration_num: int,
    ) -> str:
        """
        Generate feedback using NarrativeGenerator (Phase 6).
        
        Falls back to generate_feedback() if NarrativeGenerator unavailable.
        """
        try:
            from magnet.explain.narrative import NarrativeGenerator
            from magnet.explain.schemas import ExplanationLevel
            from magnet.kernel.enriched_delta import EnrichedDelta
            
            # Create enriched deltas
            deltas = []
            if previous_metrics and result.validation:
                current_metrics = self._extract_metrics(result)
                for key in current_metrics:
                    if key in previous_metrics:
                        deltas.append(EnrichedDelta.from_values(
                            parameter=key,
                            old_value=previous_metrics[key],
                            new_value=current_metrics[key],
                        ))
            
            narrator = NarrativeGenerator()
            narrative = narrator.generate_geometry_narrative(
                exec_result=result,
                deltas=deltas,
                level=ExplanationLevel.STANDARD,
            )
            
            return f"## Iteration {iteration_num}\n\n{narrative}"
            
        except Exception as e:
            logger.debug(f"NarrativeGenerator unavailable, using fallback: {e}")
            return generate_feedback(result, previous_metrics, iteration_num)

    async def _get_program_text_with_confidence(
        self,
        user_message: str,
        constraints: Optional[List[str]],
    ) -> tuple[Optional[str], float]:
        """
        Get program text with confidence score.
        
        Returns:
            Tuple of (program_text, confidence)
        """
        # Check if already DSL
        dsl_keywords = ["CREATE geometry.", "UPDATE ", "DELETE ", "LOFT ", "CONSTRAIN ", "SET "]
        if any(kw in user_message for kw in dsl_keywords):
            # Direct DSL has high confidence
            if constraints:
                constraint_lines = [f"CONSTRAIN {c}" for c in constraints]
                return user_message + "\n" + "\n".join(constraint_lines), 1.0
            return user_message, 1.0
        
        # Natural language - need LLM translation
        if not self._use_llm:
            logger.warning("Natural language input but use_llm=False")
            return None, 0.0
        
        try:
            from magnet.agents.geometry_proposer import propose_geometry
            
            # Build context from conversation state
            context = self._build_llm_context()
            full_intent = f"{user_message}\n\n{context}"
            
            # Build validation history from previous iterations (last 5)
            validation_history = self._build_validation_history()
            
            result = await propose_geometry(
                intent=full_intent,
                current_state=self._state.current_state,
                validation_history=validation_history,
            )
            
            if result.success:
                program_text = result.program_text
                confidence = getattr(result, 'confidence', 0.7)  # Default confidence
                
                # Add any additional constraints
                if constraints:
                    constraint_lines = [f"CONSTRAIN {c}" for c in constraints]
                    program_text = program_text + "\n" + "\n".join(constraint_lines)
                return program_text, confidence
            else:
                logger.warning(f"GeometryProposer failed: {result.error}")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            return None, 0.0
    
    
    def _build_llm_context(self) -> str:
        """Build context for LLM from conversation state."""
        parts = []
        
        # Current geometry state
        resources = self._state.current_state.get("resources", {})
        if resources:
            bodies = [r for r in resources.values() 
                     if r.get("_type") == "geometry.body" and not r.get("_deleted")]
            sections = [r for r in resources.values() 
                       if r.get("_type") == "geometry.section" and not r.get("_deleted")]
            
            if bodies or sections:
                parts.append("## Current Geometry")
                parts.append(f"- Bodies: {len(bodies)}")
                parts.append(f"- Sections: {len(sections)}")
        
        # Latest metrics
        if self._state.metrics_history:
            latest = self._state.metrics_history[-1]
            if latest:
                parts.append("\n## Latest Validation")
                for key, value in latest.items():
                    parts.append(f"- {key}: {value:.3f}")
        
        return "\n".join(parts) if parts else ""
    
    def _build_validation_history(self) -> List[Dict[str, Any]]:
        """
        Build validation history from previous iterations (last 5).
        
        Returns:
            List of validation attempts with results
        """
        history = []
        
        # Get last 5 iterations (most recent first)
        recent_iterations = list(reversed(self._state.iterations[-5:]))
        
        for iteration in recent_iterations:
            if iteration.execution_result is None:
                continue
            
            attempt = {
                "iteration_num": iteration.iteration_number,
                "success": iteration.success,
                "errors": iteration.execution_result.errors or [],
                "validation": iteration.execution_result.validation or {},
            }
            
            history.append(attempt)
        
        return history
    
    def _check_vision_dsl_reconciliation(
        self, program_text: str, vision_context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if vision interpreter results agree with DSL program.
        
        Args:
            program_text: Generated DSL program
            vision_context: Vision interpreter results with body_count, dimensions
        
        Returns:
            Issue description if disagreement, None if agreement
        """
        # Extract body count from vision
        vision_body_count = vision_context.get("body_count", 1)
        
        # Extract body count from DSL (count CREATE geometry.body statements)
        dsl_body_count = program_text.count("CREATE geometry.body")
        
        # Check for disagreement
        if dsl_body_count != vision_body_count:
            return f"Vision interpreter detected {vision_body_count} hull bodies, but the generated design has {dsl_body_count} bodies. This may indicate a misinterpretation."
        
        # Could add more checks here (dimensions, etc.)
        
        return None
    
    async def _request_reconciliation_clarification(
        self,
        issue: str,
        program_text: str,
        vision_context: Dict[str, Any],
        iteration_num: int,
    ) -> DesignIteration:
        """
        Request clarification when vision and DSL disagree.
        
        Args:
            issue: Description of the disagreement
            program_text: The DSL program that was generated
            vision_context: Vision interpreter results
            iteration_num: Current iteration number
        
        Returns:
            DesignIteration with clarification request
        """
        from magnet.agents.clarification import AgentPriority
        
        request = self._clarification_manager.create_request(
            agent_id="geometry_reconciliation",
            message=f"{issue}\n\nWhich interpretation is correct?",
            options=[
                f"Vision is correct ({vision_context.get('body_count')} bodies)",
                f"Generated design is correct ({program_text.count('CREATE geometry.body')} bodies)",
                "Let me clarify the sketch",
            ],
            priority=AgentPriority.DEFAULT,
            context={
                "issue": issue,
                "vision_body_count": vision_context.get("body_count"),
                "dsl_body_count": program_text.count("CREATE geometry.body"),
                "program_text": program_text[:500],  # First 500 chars
            },
        )
        
        self._pending_clarification = request.request_id
        
        return DesignIteration(
            iteration_number=iteration_num,
            user_request=f"[Reconciliation needed]",
            proposed_program=program_text,
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user=f"⚠️ Agent reconciliation needed:\n\n{issue}\n\nPlease clarify before proceeding.",
            success=False,
        )
    
    def _extract_metrics(self, result: Any) -> Dict[str, float]:
        """Extract metrics from execution result."""
        metrics = {}
        
        if result.geometry:
            metrics["volume"] = abs(result.geometry.volume)
        
        hydro = result.validation.get("hydrostatics", {})
        if hydro:
            if "gm_m" in hydro and hydro["gm_m"] is not None:
                metrics["gm_m"] = hydro["gm_m"]
            if "bm_transverse_m" in hydro:
                metrics["bm_m"] = hydro["bm_transverse_m"]
            if "displacement_m3" in hydro:
                metrics["displacement_m3"] = hydro["displacement_m3"]
        
        resistance = result.validation.get("resistance", {})
        if resistance and "resistance_kn" in resistance:
            metrics["resistance_kn"] = resistance["resistance_kn"]
        
        return metrics
    
    def _compute_deltas(
        self,
        current: Dict[str, float],
        previous: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        """Compute deltas between current and previous metrics."""
        if not previous:
            return {}
        
        deltas = {}
        for key in current:
            if key in previous:
                deltas[key] = current[key] - previous[key]
        return deltas
    
    def _update_state(self, result: Any) -> None:
        """Update conversation state from execution result."""
        # Update resources from actions
        for action in result.actions:
            if action.op == "SET":
                parts = action.path.split(".")
                if len(parts) >= 2 and parts[0] == "resources":
                    if "resources" not in self._state.current_state:
                        self._state.current_state["resources"] = {}
                    self._state.current_state["resources"][parts[1]] = action.value
        
        # Store geometry
        self._state.current_geometry = result.geometry
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of conversation state."""
        return {
            "conversation_id": self._conversation_id,
            "iterations": len(self._state.iterations),
            "messages": len(self._state.messages),
            "current_metrics": self._state.metrics_history[-1] if self._state.metrics_history else {},
            "has_geometry": self._state.current_geometry is not None,
        }
    
    def save_checkpoint(self) -> Dict[str, Any]:
        """
        Save current conversation state as a checkpoint.
        
        Returns:
            Serialized checkpoint data
        """
        checkpoint = {
            "conversation_id": self._conversation_id,
            "timestamp": datetime.now().isoformat(),
            "iteration_count": len(self._state.iterations),
            "state": {
                "messages": [
                    {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                    for m in self._state.messages
                ],
                "iterations": [
                    {
                        "iteration_number": it.iteration_number,
                        "user_request": it.user_request,
                        "proposed_program": it.proposed_program,
                        "metrics": it.metrics,
                        "deltas": it.deltas,
                        "feedback_to_user": it.feedback_to_user,
                        "success": it.success,
                    }
                    for it in self._state.iterations
                ],
                "current_state": self._state.current_state.copy(),
                "metrics_history": [m.copy() for m in self._state.metrics_history],
            },
        }
        
        return checkpoint
    
    def rollback_to(self, iteration_num: int) -> bool:
        """
        Roll back conversation to a specific iteration.
        
        Args:
            iteration_num: Iteration number to roll back to
        
        Returns:
            True if rollback successful, False if iteration not found
        """
        if iteration_num < 1 or iteration_num > len(self._state.iterations):
            return False
        
        # Keep only iterations up to iteration_num
        self._state.iterations = self._state.iterations[:iteration_num]
        
        # Keep only metrics up to iteration_num
        self._state.metrics_history = self._state.metrics_history[:iteration_num]
        
        # Restore state from last iteration
        if self._state.iterations:
            last_iteration = self._state.iterations[-1]
            if last_iteration.execution_result and last_iteration.success:
                # Rebuild state from successful iterations
                self._rebuild_state_from_iterations()
        
        # Clear pending clarification
        self._pending_clarification = None
        
        return True
    
    def _rebuild_state_from_iterations(self) -> None:
        """Rebuild current state from iteration history."""
        # Start fresh
        self._state.current_state = {"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}}
        
        # Replay successful iterations
        for iteration in self._state.iterations:
            if iteration.success and iteration.execution_result:
                self._update_state(iteration.execution_result)
                if iteration.execution_result.geometry:
                    self._state.current_geometry = iteration.execution_result.geometry
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get full conversation history."""
        return [
            {
                "iteration": i.iteration_number,
                "request": i.user_request,
                "success": i.success,
                "metrics": i.metrics,
                "deltas": i.deltas,
            }
            for i in self._state.iterations
        ]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def quick_design(
    intent: str,
    initial_state: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
) -> DesignIteration:
    """
    Quick one-shot design from intent.
    
    Example:
        result = await quick_design("Create a 25m patrol vessel with twin hulls")
        print(result.feedback_to_user)
    """
    conversation = DesignConversation(initial_state=initial_state, use_llm=use_llm)
    return await conversation.chat(intent)


def create_conversation(
    initial_state: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
) -> DesignConversation:
    """Create a new design conversation using the NEW geometry path."""
    return DesignConversation(initial_state=initial_state, use_llm=use_llm)

