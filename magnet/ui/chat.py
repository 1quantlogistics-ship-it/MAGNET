"""
ui/chat.py - Chat interface aligned with Conductor v1.1 API

Module 54: UI Components

v1.1: Aligned with Conductor v1.1 API for agent orchestration.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
import re
import uuid
import logging

from pydantic import BaseModel, Field

from .utils import get_state_value, set_state_value, get_phase_status

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.kernel.conductor import Conductor
    from magnet.agents.llm_client import LLMClient

logger = logging.getLogger("ui.chat")


class MessageRole(Enum):
    """Role of a chat message."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class ChatMessage:
    """A single chat message."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


@dataclass
class ChatSession:
    """A chat session with message history."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: MessageRole, content: str, **metadata) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata,
        )
        self.messages.append(message)
        return message

    def get_history(self, limit: int = 50) -> List[ChatMessage]:
        """Get recent message history."""
        return self.messages[-limit:]

    def clear(self) -> None:
        """Clear message history."""
        self.messages.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "messages": [m.to_dict() for m in self.messages[-20:]],
        }


class MissionUpdate(BaseModel):
    """Parameters extracted from natural language design request."""
    vessel_type: Optional[str] = Field(None, description="workboat/patrol/ferry/planing/catamaran")
    max_speed_kts: Optional[float] = Field(None, description="Max speed in knots")
    loa_m: Optional[float] = Field(None, description="LOA in meters (convert feet: ft * 0.3048)")
    crew: Optional[int] = Field(None, description="Crew count")
    range_nm: Optional[float] = Field(None, description="Range in nautical miles")


class ChatHandler:
    """
    Handles chat interactions with the design system.

    v1.1: Aligned with Conductor v1.1 API
    """

    # Command patterns for natural language parsing
    COMMAND_PATTERNS = {
        "status": r"^(status|show status|what is the status)$",
        "run": r"^run\s+([\w_]+)(?:\s+phase)?$",
        "set": r"^set\s+([\w.]+)\s+(?:to\s+)?(.+)$",
        "get": r"^(?:get|show|what is)\s+([\w.]+)$",
        "approve": r"^approve(?:\s+([\w_]+))?$",
        "help": r"^(?:help|commands|\?)$",
        "validate": r"^validate(?:\s+([\w_]+))?$",
        "new": r"^new(?:\s+design)?(?:\s+(.+))?$",
        "save": r"^save(?:\s+(?:to\s+)?(.+))?$",
        "load": r"^load(?:\s+(.+))?$",
        "list": r"^list\s+([\w_]+)$",
        "snapshot": r"^snapshot(?:\s+([\w_]+))?$",
    }

    def __init__(
        self,
        state: Optional["StateManager"] = None,
        conductor: Optional["Conductor"] = None,
        llm: Optional["LLMClient"] = None,
    ):
        """
        Initialize chat handler.

        Args:
            state: StateManager instance
            conductor: Conductor instance for agent orchestration
            llm: LLMClient for natural language intent parsing
        """
        self.state = state
        self.conductor = conductor
        self.llm = llm
        self.session = ChatSession()
        self._command_handlers: Dict[str, Callable] = {
            "status": self._cmd_status,
            "run": self._cmd_run,
            "set": self._cmd_set,
            "get": self._cmd_get,
            "approve": self._cmd_approve,
            "help": self._cmd_help,
            "validate": self._cmd_validate,
            "new": self._cmd_new,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "list": self._cmd_list,
            "snapshot": self._cmd_snapshot,
        }

    def process_message(self, user_input: str) -> str:
        """
        Process a user message and return response.

        Args:
            user_input: User's message text

        Returns:
            Assistant response text
        """
        # Add user message to session
        self.session.add_message(MessageRole.USER, user_input)

        # Parse and execute command
        try:
            response = self._parse_and_execute(user_input.strip().lower())
        except Exception as e:
            logger.exception(f"Command execution failed: {e}")
            response = f"Error: {str(e)}"
            self.session.add_message(MessageRole.ERROR, response)
            return response

        # Add assistant response to session
        self.session.add_message(MessageRole.ASSISTANT, response)
        return response

    def _parse_and_execute(self, text: str) -> str:
        """Parse input and execute matching command."""

        for cmd_name, pattern in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                handler = self._command_handlers.get(cmd_name)
                if handler:
                    groups = match.groups()
                    if groups and any(g is not None for g in groups):
                        return handler(*[g for g in groups if g is not None])
                    return handler()

        # No command matched - provide helpful response
        return self._handle_unrecognized(text)

    def _handle_unrecognized(self, text: str) -> str:
        """Handle unrecognized input - attempt LLM parsing for design requests."""

        # If no LLM, fall back to help text
        if not self.llm:
            return self._help_text(text)

        # Try to parse as design request (handle async properly)
        import asyncio
        try:
            # Python 3.10+ compatible async handling
            try:
                loop = asyncio.get_running_loop()
                # Already in async context - use thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    params = pool.submit(
                        asyncio.run, self._parse_design_request(text)
                    ).result()
            except RuntimeError:
                # No running loop - safe to use asyncio.run()
                params = asyncio.run(self._parse_design_request(text))
        except Exception as e:
            logger.warning(f"LLM parse failed: {e}")
            return self._help_text(text)

        # If nothing extracted, show help
        if not any([params.vessel_type, params.max_speed_kts, params.loa_m, params.crew, params.range_nm]):
            return self._help_text(text)

        # Seed state with extracted parameters
        self._seed_mission(params)

        # Run design pipeline
        results = self._run_design_pipeline()

        # Return summary
        return self._format_design_summary(params, results)

    def _help_text(self, text: str) -> str:
        """Original help message for unrecognized input."""
        return (
            f"I didn't understand '{text}'. "
            "Try 'help' for available commands, or use commands like:\n"
            "  - status - Show design status\n"
            "  - run <phase> - Run a phase\n"
            "  - get <path> - Get a value\n"
            "  - set <path> <value> - Set a value"
        )

    async def _parse_design_request(self, text: str) -> MissionUpdate:
        """Use LLM to extract mission parameters from natural language."""
        prompt = f"""Extract ship design parameters from this request.
Convert feet to meters (ft × 0.3048). Only include explicitly mentioned values.

User: {text}

Return JSON with fields: vessel_type, max_speed_kts, loa_m, crew, range_nm
Only include fields that are explicitly mentioned or clearly implied."""

        return await self.llm.complete_json(prompt, MissionUpdate)

    def _seed_mission(self, params: MissionUpdate) -> None:
        """Apply extracted parameters to state."""
        if params.vessel_type:
            self.state.set("mission.vessel_type", params.vessel_type, "chat")
            self.state.set("hull.hull_type", params.vessel_type, "chat")
        if params.max_speed_kts:
            self.state.set("mission.max_speed_kts", params.max_speed_kts, "chat")
        if params.loa_m:
            # Note: state expects meters, MissionUpdate already converts ft→m
            self.state.set("mission.loa", params.loa_m, "chat")
        if params.crew:
            self.state.set("mission.crew_berthed", params.crew, "chat")
        if params.range_nm:
            self.state.set("mission.range_nm", params.range_nm, "chat")

    def _run_design_pipeline(self) -> list:
        """Run the golden path phases using adaptive conductor API."""
        if not self.conductor:
            return []

        # Create unique session per request to avoid state pollution
        import uuid
        session_id = f"chat_design_{uuid.uuid4().hex[:8]}"
        self.conductor.create_session(session_id)
        phases = ["mission", "hull", "weight", "stability"]  # Golden path only
        results = []

        # Match existing _cmd_run() pattern - use adaptive API
        if hasattr(self.conductor, 'run_full_design'):
            # Preferred: run all phases at once
            result = self.conductor.run_full_design(phases=phases)
            final_status = getattr(result, 'final_status', 'done')
            for phase in phases:
                results.append((phase, final_status))
        else:
            # Fallback: run phases individually
            for phase in phases:
                result = self.conductor.run_phase(phase)
                status = result.status.value if hasattr(result.status, 'value') else str(result.status)
                results.append((phase, status))

        return results

    def _format_design_summary(self, params: MissionUpdate, results: list) -> str:
        """Format design results as conversational summary."""
        lines = ["**Design Created**\n"]

        # Show what was extracted
        extracted = []
        if params.vessel_type:
            extracted.append(f"Type: {params.vessel_type}")
        if params.max_speed_kts:
            extracted.append(f"Speed: {params.max_speed_kts} kts")
        if params.loa_m:
            extracted.append(f"LOA: {params.loa_m:.1f} m")
        if params.crew:
            extracted.append(f"Crew: {params.crew}")
        if params.range_nm:
            extracted.append(f"Range: {params.range_nm} nm")

        if extracted:
            lines.append("Mission: " + ", ".join(extracted))

        # Show phase results
        lines.append("\n**Phases:**")
        for phase, status in results:
            icon = "✓" if "completed" in status.lower() or "done" in status.lower() else "✗"
            lines.append(f"  {icon} {phase}: {status}")

        # Show key outputs from state (corrected paths)
        lwl = self.state.get("hull.lwl")
        beam = self.state.get("hull.beam")
        draft = self.state.get("hull.draft")
        # Corrected: weight.lightship_mt is the actual path
        lightship = (
            self.state.get("weight.lightship_mt") or
            self.state.get("weight.lightship_weight_mt")
        )
        # Try multiple GM paths (gm_m works, gm_transverse_m is also valid)
        gm = self.state.get("stability.gm_m") or self.state.get("stability.gm_transverse_m")
        if gm is None:
            kb = self.state.get("stability.kb_m") or 0
            bm = self.state.get("stability.bm_m") or 0
            kg = self.state.get("stability.kg_m") or 0
            if kb and bm and kg:
                gm = kb + bm - kg

        lines.append("\n**Results:**")
        if lwl:
            lines.append(f"  LWL: {lwl:.2f} m")
        if beam:
            lines.append(f"  Beam: {beam:.2f} m")
        if draft:
            lines.append(f"  Draft: {draft:.2f} m")
        if lightship:
            lines.append(f"  Lightship: {lightship:.1f} tonnes")
        if gm:
            lines.append(f"  GM: {gm:.3f} m")

        return "\n".join(lines)

    def _cmd_status(self) -> str:
        """Get design status using unified accessors."""
        if not self.state:
            return "No design loaded. Use 'new' to create one."

        design_id = get_state_value(self.state, "metadata.design_id", "Unknown")
        name = get_state_value(self.state, "metadata.name", "Untitled")

        lines = [
            "**Design Status**",
            f"- Name: {name}",
            f"- ID: {design_id}",
            "",
            "**Phase Status:**",
        ]

        phases = [
            "mission", "hull_form", "structure", "propulsion",
            "systems", "weight_stability", "compliance"
        ]

        icons = {
            "pending": "○",
            "active": "◉",
            "completed": "●",
            "approved": "✓",
            "error": "✗",
            "skipped": "−",
        }

        for phase in phases:
            status = get_phase_status(self.state, phase, "pending")
            icon = icons.get(status, "?")
            lines.append(f"  {icon} {phase}: {status}")

        # Add key metrics
        lines.extend([
            "",
            "**Key Metrics:**",
        ])

        loa = get_state_value(self.state, "hull.loa")
        beam = get_state_value(self.state, "hull.beam")
        displacement = get_state_value(self.state, "hull.displacement_mt")
        gm = get_state_value(self.state, "stability.gm_transverse_m")

        if loa:
            lines.append(f"  LOA: {loa:.2f} m")
        if beam:
            lines.append(f"  Beam: {beam:.2f} m")
        if displacement:
            lines.append(f"  Displacement: {displacement:.1f} t")
        if gm:
            lines.append(f"  GM: {gm:.3f} m")

        return "\n".join(lines)

    def _cmd_run(self, phase: Optional[str] = None) -> str:
        """Run a phase using Conductor v1.1 API."""
        if not self.conductor:
            return "Conductor not initialized. Cannot run phases."

        try:
            if phase:
                # v1.1: Conductor.run_full_design() with phases parameter
                if hasattr(self.conductor, 'run_full_design'):
                    result = self.conductor.run_full_design(phases=[phase])
                elif hasattr(self.conductor, 'run_phase'):
                    result = self.conductor.run_phase(phase)
                else:
                    return f"Cannot run phase '{phase}': Conductor API not available"

                return f"Phase '{phase}' completed. Status: {getattr(result, 'final_status', 'done')}"
            else:
                # Run full design
                if hasattr(self.conductor, 'run_full_design'):
                    result = self.conductor.run_full_design()
                    return f"Design run completed. Status: {getattr(result, 'final_status', 'done')}"
                return "Full design run not available. Specify a phase: run <phase>"
        except Exception as e:
            return f"Run failed: {str(e)}"

    def _cmd_set(self, path: str, value: str) -> str:
        """Set a parameter value."""
        if not self.state:
            return "No design loaded."

        # Try to parse value
        parsed_value: Any = value
        try:
            if value.lower() in ("true", "yes"):
                parsed_value = True
            elif value.lower() in ("false", "no"):
                parsed_value = False
            elif "." in value:
                parsed_value = float(value)
            else:
                parsed_value = int(value)
        except ValueError:
            parsed_value = value  # Keep as string

        success = set_state_value(self.state, path, parsed_value, "chat")

        if success:
            return f"Set {path} = {parsed_value}"
        return f"Failed to set {path}"

    def _cmd_get(self, path: str) -> str:
        """Get a parameter value."""
        if not self.state:
            return "No design loaded."

        value = get_state_value(self.state, path)

        if value is None:
            return f"{path}: (not set)"

        if isinstance(value, float):
            return f"{path}: {value:.4f}"
        if isinstance(value, dict):
            items = [f"  {k}: {v}" for k, v in list(value.items())[:10]]
            return f"{path}:\n" + "\n".join(items)
        if isinstance(value, list):
            return f"{path}: [{len(value)} items]"

        return f"{path}: {value}"

    def _cmd_approve(self, phase: Optional[str] = None) -> str:
        """Approve a phase."""
        if not self.state:
            return "No design loaded."

        if not phase:
            # Find current completed phase to approve
            phases = ["mission", "hull_form", "structure", "propulsion", "systems", "weight_stability", "compliance"]
            for p in phases:
                status = get_phase_status(self.state, p, "pending")
                if status == "completed":
                    phase = p
                    break

        if not phase:
            return "No phase ready for approval."

        from .utils import set_phase_status
        success = set_phase_status(self.state, phase, "approved", "chat")

        if success:
            return f"Phase '{phase}' approved."
        return f"Failed to approve phase '{phase}'."

    def _cmd_help(self) -> str:
        """Show available commands."""
        return """**Available Commands:**

**Design:**
  new [name]       - Create new design
  load <path>      - Load design from file
  save [path]      - Save current design
  status           - Show design status

**Phases:**
  run <phase>      - Run a specific phase
  validate [phase] - Validate current/specific phase
  approve [phase]  - Approve completed phase

**Parameters:**
  get <path>       - Get parameter value
  set <path> <val> - Set parameter value
  list <category>  - List parameters in category

**Vision:**
  snapshot [phase] - Take hull snapshot

**Other:**
  help             - Show this help
"""

    def _cmd_validate(self, phase: Optional[str] = None) -> str:
        """Validate design or specific phase."""
        if not self.state:
            return "No design loaded."

        if not self.conductor:
            return "Conductor not available for validation."

        try:
            if hasattr(self.conductor, 'validate_phase') and phase:
                result = self.conductor.validate_phase(phase)
            elif hasattr(self.conductor, 'validate'):
                result = self.conductor.validate()
            else:
                # Use compliance data from state
                passed = get_state_value(self.state, "compliance.overall_passed", True)
                errors = get_state_value(self.state, "compliance.errors", [])
                warnings = get_state_value(self.state, "compliance.warnings", [])

                lines = [f"Validation: {'PASSED' if passed else 'FAILED'}"]
                if errors:
                    lines.append(f"  Errors: {len(errors)}")
                if warnings:
                    lines.append(f"  Warnings: {len(warnings)}")
                return "\n".join(lines)

            return f"Validation complete: {result}"
        except Exception as e:
            return f"Validation failed: {str(e)}"

    def _cmd_new(self, name: Optional[str] = None) -> str:
        """Create a new design."""
        if not self.state:
            return "State not available."

        import uuid
        from datetime import datetime

        design_id = f"MAGNET-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        design_name = name or "New Design"

        set_state_value(self.state, "metadata.design_id", design_id, "chat")
        set_state_value(self.state, "metadata.name", design_name, "chat")
        set_state_value(self.state, "metadata.created_at", datetime.now(timezone.utc).isoformat(), "chat")

        return f"Created new design: {design_name}\nID: {design_id}"

    def _cmd_save(self, path: Optional[str] = None) -> str:
        """Save current design."""
        if not self.state:
            return "No design loaded."

        from .utils import serialize_state
        import json

        data = serialize_state(self.state)

        if not path:
            design_id = get_state_value(self.state, "metadata.design_id", "design")
            path = f"{design_id}.json"

        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return f"Design saved to: {path}"
        except Exception as e:
            return f"Save failed: {str(e)}"

    def _cmd_load(self, path: str) -> str:
        """Load design from file."""
        if not self.state:
            return "State not available."

        from .utils import load_state_from_dict
        import json

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            success = load_state_from_dict(self.state, data)

            if success:
                name = get_state_value(self.state, "metadata.name", "Unknown")
                return f"Loaded design: {name}"
            return "Failed to load design data."
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Load failed: {str(e)}"

    def _cmd_list(self, category: str) -> str:
        """List parameters in a category."""
        if not self.state:
            return "No design loaded."

        data = get_state_value(self.state, category, {})

        if not data:
            return f"No data found for '{category}'"

        if isinstance(data, dict):
            lines = [f"**{category}:**"]
            for key, value in list(data.items())[:20]:
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:.4f}")
                elif isinstance(value, dict):
                    lines.append(f"  {key}: {{...}}")
                elif isinstance(value, list):
                    lines.append(f"  {key}: [{len(value)} items]")
                else:
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)

        return f"{category}: {data}"

    def _cmd_snapshot(self, phase: Optional[str] = None) -> str:
        """Take a hull snapshot."""
        try:
            from magnet.vision.router import VisionRouter, VisionRequest

            router = VisionRouter(self.state)
            request = VisionRequest(
                request_id=f"chat_snapshot_{phase or 'current'}",
                operation="snapshot",
                parameters={
                    "phase": phase or "current",
                    "view": "perspective",
                },
            )

            response = router.process_request(request)

            if response.success and response.snapshots:
                path = response.snapshots[0].image_path
                return f"Snapshot saved: {path}"
            return f"Snapshot failed: {response.error or 'unknown error'}"
        except ImportError:
            return "Vision module not available."
        except Exception as e:
            return f"Snapshot failed: {str(e)}"

    def get_session(self) -> ChatSession:
        """Get current chat session."""
        return self.session

    def new_session(self) -> ChatSession:
        """Start a new chat session."""
        self.session = ChatSession()
        return self.session
