# CORTEX: Generative Design Implementation Specification

**Version:** 1.0  
**Status:** Implementation Ready  
**Date:** January 2026  
**Prerequisite:** CORTEX_CONTROL_PLANE_IMPLEMENTATION.md (shared infrastructure)

---

## Executive Summary

This document specifies the implementation of CORTEX's generative design system—the architecture for creating new physical artifacts from requirements through recursive decomposition, pattern instantiation, and validation.

**Existing MAGNET Assets Reused:**
- `magnet/routing/` — Path optimization, compartment graphs (70% reusable)
- `magnet/validators/` — Validation framework and aggregator (90% reusable)
- `magnet/agents/geometry_proposer.py` — Thinking/action pass pattern (80% reusable)
- `magnet/kernel/stdlib/compiler.py` — Geometry compilation (100% reusable)
- `magnet/webgl/exporter.py` — Export to glTF/STL/OBJ (100% reusable)

---

## 1. Hierarchical Agent Architecture

### 1.1 Level Definitions

```python
# cortex/generative/levels.py

from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod


class DesignLevelName(Enum):
    MISSION = "mission"
    SYSTEMS = "systems"
    COMPONENTS = "components"
    ROUTING = "routing"
    DETAILS = "details"


@dataclass
class Tool:
    """Tool available to an agent at a given level."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class Validator:
    """Validator that must pass before descending to next level."""
    name: str
    validate: Callable[["ArtifactGraph", str], "ValidationResult"]
    blocking: bool = True  # If True, failure prevents descent


@dataclass
class DesignLevel:
    """
    Definition of a single level in the design hierarchy.
    
    Each level receives context from its parent, produces outputs for children,
    and must pass validators before the orchestrator descends.
    """
    name: DesignLevelName
    
    # What this level receives from parent
    inputs: List[str] = field(default_factory=list)
    # Examples:
    #   mission: ["user_requirements", "hull_envelope"]
    #   systems: ["space_allocation", "performance_requirements"]
    #   components: ["system_specs", "zone_assignments"]
    #   routing: ["placed_components", "connection_requirements"]
    #   details: ["validated_routes", "support_requirements"]
    
    # What this level produces for children
    outputs: List[str] = field(default_factory=list)
    # Examples:
    #   mission: ["space_allocation", "system_requirements", "weight_budget"]
    #   systems: ["system_specs", "component_lists", "interface_points"]
    #   components: ["placed_components", "clearance_reports"]
    #   routing: ["routes", "fittings", "penetrations"]
    #   details: ["supports", "labels", "access_panels"]
    
    # Validators that must pass before descending
    validators: List[Validator] = field(default_factory=list)
    
    # Tools available at this level
    tools: List[Tool] = field(default_factory=list)
    
    # System prompt for the agent at this level
    system_prompt: str = ""
    
    # Maximum iterations at this level before escalation
    max_iterations: int = 10
    
    # Whether user approval is required before descending
    requires_approval: bool = False


# Pre-configured level definitions
DESIGN_LEVELS: Dict[DesignLevelName, DesignLevel] = {
    DesignLevelName.MISSION: DesignLevel(
        name=DesignLevelName.MISSION,
        inputs=["user_requirements", "hull_envelope"],
        outputs=["space_allocation", "system_requirements", "weight_budget", "power_budget"],
        max_iterations=5,
        requires_approval=True,
    ),
    DesignLevelName.SYSTEMS: DesignLevel(
        name=DesignLevelName.SYSTEMS,
        inputs=["space_allocation", "system_requirements", "weight_budget"],
        outputs=["system_specs", "component_lists", "interface_points", "routing_requirements"],
        max_iterations=8,
        requires_approval=False,
    ),
    DesignLevelName.COMPONENTS: DesignLevel(
        name=DesignLevelName.COMPONENTS,
        inputs=["system_specs", "component_lists", "zone_assignments"],
        outputs=["placed_components", "clearance_reports", "connection_points"],
        max_iterations=15,
        requires_approval=False,
    ),
    DesignLevelName.ROUTING: DesignLevel(
        name=DesignLevelName.ROUTING,
        inputs=["placed_components", "connection_points", "routing_requirements"],
        outputs=["routes", "fittings", "penetrations", "support_locations"],
        max_iterations=20,
        requires_approval=False,
    ),
    DesignLevelName.DETAILS: DesignLevel(
        name=DesignLevelName.DETAILS,
        inputs=["routes", "support_locations", "labeling_requirements"],
        outputs=["supports", "labels", "access_panels", "installation_sequence"],
        max_iterations=10,
        requires_approval=True,
    ),
}
```

### 1.2 Level Context

```python
# cortex/generative/context.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class LevelContext:
    """
    Context passed between levels in the design hierarchy.
    
    Immutable record of what was decided at each level.
    """
    level: DesignLevelName
    
    # Inputs received from parent level
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    # Outputs produced at this level
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Validation results
    validation_results: Dict[str, "ValidationResult"] = field(default_factory=dict)
    
    # Decisions made (for audit trail)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Iterations taken
    iterations: int = 0
    
    # Timestamp
    completed_at: Optional[datetime] = None
    
    # Whether user approved (if requires_approval)
    user_approved: bool = False
    approval_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "validation_results": {
                k: v.to_dict() for k, v in self.validation_results.items()
            },
            "decisions": self.decisions,
            "iterations": self.iterations,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "user_approved": self.user_approved,
            "approval_notes": self.approval_notes,
        }


@dataclass
class LevelResult:
    """Result of running a single level."""
    success: bool
    context: LevelContext
    errors: List[str] = field(default_factory=list)
    requires_backtrack: bool = False
    backtrack_reason: str = ""
    backtrack_to: Optional[DesignLevelName] = None
```

### 1.3 Hierarchical Design Orchestrator

```python
# cortex/generative/orchestrator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from .levels import DesignLevel, DesignLevelName, DESIGN_LEVELS
from .context import LevelContext, LevelResult
from ..artifact_graph import ArtifactGraph
from ..kernel import Kernel

logger = logging.getLogger(__name__)


@dataclass
class DesignResult:
    """Final result of generative design."""
    success: bool
    graph: ArtifactGraph
    level_contexts: Dict[DesignLevelName, LevelContext] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_iterations: int = 0
    backtracks: int = 0
    duration_seconds: float = 0.0


@dataclass 
class Requirements:
    """User requirements for generative design."""
    mission_statement: str
    vessel_type: str
    loa_m: float
    beam_m: float
    draft_m: float
    range_nm: Optional[float] = None
    speed_kt: Optional[float] = None
    passengers: Optional[int] = None
    crew: Optional[int] = None
    systems_required: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)


class HierarchicalDesignAgent:
    """
    Orchestrates generative design through hierarchical levels.
    
    Manages:
    - Level execution sequence
    - Context passing between levels
    - Validation gates
    - Backtracking on failure
    - User approval gates
    """
    
    def __init__(
        self,
        levels: Dict[DesignLevelName, DesignLevel],
        graph: ArtifactGraph,
        kernel: Kernel,
        llm_client: Any,
        approval_callback: Optional[Callable[[LevelContext], bool]] = None,
    ):
        self._levels = levels
        self._graph = graph
        self._kernel = kernel
        self._llm = llm_client
        self._approval_callback = approval_callback
        self._level_contexts: Dict[DesignLevelName, LevelContext] = {}
        self._snapshots: Dict[DesignLevelName, Any] = {}  # Graph snapshots for backtracking
    
    async def design(self, requirements: Requirements) -> DesignResult:
        """
        Execute full generative design from requirements.
        
        Descends through levels: mission → systems → components → routing → details
        Backtracks when validation fails at any level.
        """
        start_time = datetime.now()
        result = DesignResult(success=False, graph=self._graph)
        
        # Initialize mission context from requirements
        initial_context = LevelContext(
            level=DesignLevelName.MISSION,
            inputs={
                "user_requirements": requirements.__dict__,
                "hull_envelope": self._extract_hull_envelope(),
            },
        )
        
        # Execute levels in sequence
        level_sequence = [
            DesignLevelName.MISSION,
            DesignLevelName.SYSTEMS,
            DesignLevelName.COMPONENTS,
            DesignLevelName.ROUTING,
            DesignLevelName.DETAILS,
        ]
        
        current_context = initial_context
        level_idx = 0
        
        while level_idx < len(level_sequence):
            level_name = level_sequence[level_idx]
            level_def = self._levels[level_name]
            
            # Take snapshot before level execution (for backtracking)
            self._snapshots[level_name] = self._graph.snapshot()
            
            logger.info(f"Executing level: {level_name.value}")
            
            # Run the level
            level_result = await self.run_level(level_def, current_context)
            result.total_iterations += level_result.context.iterations
            
            if level_result.requires_backtrack:
                # Backtrack to specified level
                result.backtracks += 1
                backtrack_to = level_result.backtrack_to or level_sequence[max(0, level_idx - 1)]
                
                logger.warning(
                    f"Backtracking from {level_name.value} to {backtrack_to.value}: "
                    f"{level_result.backtrack_reason}"
                )
                
                # Restore graph snapshot
                if backtrack_to in self._snapshots:
                    self._graph.restore(self._snapshots[backtrack_to])
                
                # Find index of backtrack level
                level_idx = level_sequence.index(backtrack_to)
                
                # Prepare context for retry with failure info
                current_context = self._level_contexts.get(backtrack_to, initial_context)
                current_context.inputs["previous_failure"] = {
                    "level": level_name.value,
                    "reason": level_result.backtrack_reason,
                    "errors": level_result.errors,
                }
                continue
            
            if not level_result.success:
                result.errors.extend(level_result.errors)
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                return result
            
            # Store context and prepare for next level
            self._level_contexts[level_name] = level_result.context
            result.level_contexts[level_name] = level_result.context
            
            # Prepare context for next level
            if level_idx + 1 < len(level_sequence):
                next_level = level_sequence[level_idx + 1]
                next_level_def = self._levels[next_level]
                
                current_context = LevelContext(
                    level=next_level,
                    inputs=self._prepare_level_inputs(
                        next_level_def,
                        level_result.context.outputs,
                    ),
                )
            
            level_idx += 1
        
        result.success = True
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result
    
    async def run_level(
        self,
        level: DesignLevel,
        context: LevelContext,
    ) -> LevelResult:
        """
        Execute a single design level.
        
        Runs agent loop until:
        - All validators pass, OR
        - Max iterations reached, OR
        - Agent signals backtrack needed
        """
        result = LevelResult(success=False, context=context)
        
        for iteration in range(level.max_iterations):
            context.iterations = iteration + 1
            
            # Run agent turn
            agent_result = await self._run_agent_turn(level, context)
            
            if agent_result.get("backtrack"):
                result.requires_backtrack = True
                result.backtrack_reason = agent_result.get("backtrack_reason", "Validation failed")
                result.backtrack_to = agent_result.get("backtrack_to")
                return result
            
            # Update context with agent outputs
            context.outputs.update(agent_result.get("outputs", {}))
            context.decisions.append({
                "iteration": iteration,
                "actions": agent_result.get("actions", []),
                "reasoning": agent_result.get("reasoning", ""),
            })
            
            # Run validators
            all_passed = True
            for validator in level.validators:
                val_result = validator.validate(self._graph, level.name.value)
                context.validation_results[validator.name] = val_result
                
                if not val_result.passed and validator.blocking:
                    all_passed = False
                    logger.warning(f"Validator {validator.name} failed: {val_result.message}")
            
            if all_passed:
                # Check if user approval required
                if level.requires_approval:
                    if self._approval_callback:
                        approved = self._approval_callback(context)
                        context.user_approved = approved
                        if not approved:
                            result.requires_backtrack = True
                            result.backtrack_reason = "User rejected level output"
                            return result
                    else:
                        context.user_approved = True  # Auto-approve if no callback
                
                context.completed_at = datetime.now()
                result.success = True
                return result
        
        # Max iterations reached
        result.errors.append(f"Level {level.name.value} did not converge in {level.max_iterations} iterations")
        result.requires_backtrack = True
        result.backtrack_reason = "Max iterations reached without validation passing"
        return result
    
    async def _run_agent_turn(
        self,
        level: DesignLevel,
        context: LevelContext,
    ) -> Dict[str, Any]:
        """Run a single agent turn at the given level."""
        # Build messages for LLM
        messages = self._build_messages(level, context)
        
        # Call LLM with tools
        response = await self._llm.messages.create(
            model="claude-sonnet-4-20250514",
            system=level.system_prompt,
            tools=[self._tool_to_schema(t) for t in level.tools],
            messages=messages,
            max_tokens=4096,
        )
        
        # Process tool calls
        outputs = {}
        actions = []
        
        for block in response.content:
            if block.type == "tool_use":
                tool = next((t for t in level.tools if t.name == block.name), None)
                if tool:
                    try:
                        result = tool.handler(block.input, self._graph, self._kernel)
                        actions.append({
                            "tool": block.name,
                            "input": block.input,
                            "result": result,
                        })
                        if isinstance(result, dict):
                            outputs.update(result.get("outputs", {}))
                    except Exception as e:
                        logger.error(f"Tool {block.name} failed: {e}")
                        actions.append({
                            "tool": block.name,
                            "input": block.input,
                            "error": str(e),
                        })
            elif block.type == "text":
                # Check for backtrack signal
                if "BACKTRACK" in block.text:
                    return {
                        "backtrack": True,
                        "backtrack_reason": block.text,
                    }
        
        return {
            "outputs": outputs,
            "actions": actions,
            "reasoning": response.content[0].text if response.content else "",
        }
    
    def _extract_hull_envelope(self) -> Dict[str, Any]:
        """Extract hull bounding envelope from graph."""
        bounds = self._graph.get_bounds()
        return {
            "min": [bounds.min_x, bounds.min_y, bounds.min_z],
            "max": [bounds.max_x, bounds.max_y, bounds.max_z],
            "volume_m3": self._graph.compute_volume(),
        }
    
    def _prepare_level_inputs(
        self,
        level: DesignLevel,
        parent_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare inputs for a level from parent outputs."""
        inputs = {}
        for input_name in level.inputs:
            if input_name in parent_outputs:
                inputs[input_name] = parent_outputs[input_name]
        return inputs
    
    def _build_messages(
        self,
        level: DesignLevel,
        context: LevelContext,
    ) -> List[Dict[str, Any]]:
        """Build message history for LLM."""
        return [{
            "role": "user",
            "content": f"""Current level: {level.name.value}

Inputs from parent level:
{self._format_inputs(context.inputs)}

Previous decisions this level:
{self._format_decisions(context.decisions)}

Validation status:
{self._format_validations(context.validation_results)}

Continue designing. Use the available tools to make progress.
When all validators pass, the level is complete."""
        }]
    
    def _format_inputs(self, inputs: Dict[str, Any]) -> str:
        import json
        return json.dumps(inputs, indent=2, default=str)
    
    def _format_decisions(self, decisions: List[Dict]) -> str:
        if not decisions:
            return "None yet."
        return "\n".join(f"- Iteration {d['iteration']}: {d.get('reasoning', '')[:200]}" for d in decisions[-5:])
    
    def _format_validations(self, results: Dict[str, Any]) -> str:
        if not results:
            return "No validations run yet."
        return "\n".join(f"- {k}: {'PASS' if v.passed else 'FAIL'}" for k, v in results.items())
    
    def _tool_to_schema(self, tool: Tool) -> Dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
```


---

## 2. Domain Pattern Libraries

### 2.1 Pattern Schema

```python
# cortex/generative/patterns/schema.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class PatternDomain(Enum):
    FUEL = "fuel"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    HVAC = "hvac"
    PROPULSION = "propulsion"
    STRUCTURE = "structure"


@dataclass
class ParameterSpec:
    """Specification for a configurable pattern parameter."""
    name: str
    type: str  # "float", "int", "str", "bool", "enum"
    description: str
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[List[str]] = None
    unit: str = ""


@dataclass
class ComponentTemplate:
    """Template for a component in a pattern."""
    component_type: str
    quantity: int = 1
    quantity_formula: Optional[str] = None  # e.g., "ceil(capacity_gal / 400)"
    required: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    placement_zone: str = ""
    placement_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """Rule for routing connections in a pattern."""
    from_port: str
    to_port: str
    system_type: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    # Example constraints:
    # {
    #     "min_bend_radius_m": 0.1,
    #     "max_unsupported_span_m": 1.0,
    #     "slope_direction": "toward_destination",
    #     "avoid_zones": ["exhaust_zone"],
    # }


@dataclass
class Constraint:
    """Constraint that must be satisfied by the pattern."""
    name: str
    type: str  # "clearance", "capacity", "flow", "structural", "regulatory"
    expression: str  # e.g., "tank_capacity >= required_capacity"
    priority: str = "required"  # "required", "recommended", "optional"
    message: str = ""


@dataclass
class SystemPattern:
    """
    Complete pattern for a vessel system.
    
    Patterns encode domain knowledge about how systems are typically configured.
    The LLM selects patterns; the kernel instantiates them.
    """
    id: str
    name: str
    domain: PatternDomain
    description: str
    
    # Components in this pattern
    components: List[ComponentTemplate] = field(default_factory=list)
    
    # How components connect
    topology: str = ""  # DSL: "fill --> tank --> filter --> engine"
    
    # Routing rules per connection type
    routing_rules: Dict[str, RoutingRule] = field(default_factory=dict)
    
    # Constraints that must be satisfied
    constraints: List[Constraint] = field(default_factory=list)
    
    # Configurable parameters
    parameters: Dict[str, ParameterSpec] = field(default_factory=dict)
    
    # Applicability conditions
    applicable_when: Dict[str, Any] = field(default_factory=dict)
    # Example: {"engine_type": "diesel", "engine_count": 2}
    
    # Metadata
    source: str = ""  # "ABYC H-33", "manufacturer", "custom"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "description": self.description,
            "components": [c.__dict__ for c in self.components],
            "topology": self.topology,
            "routing_rules": {k: v.__dict__ for k, v in self.routing_rules.items()},
            "constraints": [c.__dict__ for c in self.constraints],
            "parameters": {k: v.__dict__ for k, v in self.parameters.items()},
        }
```

### 2.2 Pattern Registry

```python
# cortex/generative/patterns/registry.py

from typing import Dict, List, Optional, Any
from .schema import SystemPattern, PatternDomain


class PatternRegistry:
    """
    Registry of system patterns.
    
    Patterns are selected by the LLM based on requirements and instantiated by the kernel.
    """
    
    def __init__(self):
        self._patterns: Dict[str, SystemPattern] = {}
        self._by_domain: Dict[PatternDomain, List[str]] = {d: [] for d in PatternDomain}
    
    def register(self, pattern: SystemPattern) -> None:
        """Register a pattern."""
        self._patterns[pattern.id] = pattern
        self._by_domain[pattern.domain].append(pattern.id)
    
    def get(self, pattern_id: str) -> Optional[SystemPattern]:
        """Get pattern by ID."""
        return self._patterns.get(pattern_id)
    
    def list_by_domain(self, domain: PatternDomain) -> List[SystemPattern]:
        """List all patterns for a domain."""
        return [self._patterns[pid] for pid in self._by_domain.get(domain, [])]
    
    def find_applicable(
        self,
        domain: PatternDomain,
        conditions: Dict[str, Any],
    ) -> List[SystemPattern]:
        """Find patterns that match the given conditions."""
        applicable = []
        for pattern in self.list_by_domain(domain):
            if self._matches_conditions(pattern, conditions):
                applicable.append(pattern)
        return applicable
    
    def _matches_conditions(
        self,
        pattern: SystemPattern,
        conditions: Dict[str, Any],
    ) -> bool:
        """Check if pattern is applicable given conditions."""
        for key, required_value in pattern.applicable_when.items():
            if key in conditions:
                if conditions[key] != required_value:
                    return False
        return True
    
    def to_llm_summary(self, domain: Optional[PatternDomain] = None) -> str:
        """Generate summary for LLM pattern selection."""
        patterns = self.list_by_domain(domain) if domain else list(self._patterns.values())
        
        lines = ["Available patterns:"]
        for p in patterns:
            lines.append(f"\n## {p.id}: {p.name}")
            lines.append(f"Domain: {p.domain.value}")
            lines.append(f"Description: {p.description}")
            lines.append(f"Components: {len(p.components)}")
            if p.applicable_when:
                lines.append(f"Applicable when: {p.applicable_when}")
        
        return "\n".join(lines)


# Global registry instance
PATTERN_REGISTRY = PatternRegistry()
```

### 2.3 Built-in Patterns

```python
# cortex/generative/patterns/builtin.py

from .schema import (
    SystemPattern, PatternDomain, ComponentTemplate, 
    RoutingRule, Constraint, ParameterSpec
)
from .registry import PATTERN_REGISTRY


def register_builtin_patterns():
    """Register all built-in system patterns."""
    
    # ==========================================================================
    # FUEL SYSTEM PATTERNS
    # ==========================================================================
    
    PATTERN_REGISTRY.register(SystemPattern(
        id="fuel_single_gasoline",
        name="Single Engine Gasoline System",
        domain=PatternDomain.FUEL,
        description="Simple gasoline fuel system for single outboard or sterndrive",
        components=[
            ComponentTemplate(
                component_type="fuel_tank",
                quantity=1,
                properties={"material": "aluminum", "baffled": True},
                placement_zone="fuel_zone",
                placement_constraints={"below_fill": True, "accessible_top": True},
            ),
            ComponentTemplate(
                component_type="fuel_fill",
                quantity=1,
                properties={"deck_fitting": True, "grounded": True},
                placement_zone="gunwale",
                placement_constraints={"side": "starboard", "above_tank": True},
            ),
            ComponentTemplate(
                component_type="fuel_vent",
                quantity=1,
                properties={"screen": True, "flame_arrestor": False},
                placement_zone="hull_side",
                placement_constraints={"above_waterline": True, "highest_point": True},
            ),
            ComponentTemplate(
                component_type="fuel_pickup",
                quantity=1,
                properties={"with_filter": True},
                placement_constraints={"in_tank": True},
            ),
            ComponentTemplate(
                component_type="water_separator",
                quantity=1,
                properties={"model": "racor_230r"},
                placement_zone="engine_room",
                placement_constraints={"accessible": True, "vertical": True},
            ),
        ],
        topology="""
            fill --> tank
            tank --> pickup --> water_sep --> engine_inlet
            engine_outlet --> return --> tank
            tank --> vent --> hull_fitting
        """,
        routing_rules={
            "fuel_supply": RoutingRule(
                from_port="tank.outlet",
                to_port="engine.inlet",
                system_type="fuel_supply",
                constraints={
                    "min_bend_radius_factor": 3,
                    "max_unsupported_span_m": 1.0,
                    "material": "USCG_A1",
                    "antisiphon_required": True,
                },
            ),
            "fuel_vent": RoutingRule(
                from_port="tank.vent",
                to_port="hull.vent_fitting",
                system_type="fuel_vent",
                constraints={
                    "must_rise_continuously": True,
                    "loop_above_tank_m": 0.3,
                    "screen_at_exit": True,
                },
            ),
        },
        constraints=[
            Constraint(
                name="tank_capacity",
                type="capacity",
                expression="tank.capacity_gal >= required_capacity_gal",
                priority="required",
            ),
            Constraint(
                name="vent_height",
                type="regulatory",
                expression="vent.height_above_tank_m >= 0.3",
                priority="required",
                message="ABYC H-33: Vent loop must be 300mm above tank top",
            ),
        ],
        parameters={
            "tank_capacity_gal": ParameterSpec(
                name="tank_capacity_gal",
                type="float",
                description="Fuel tank capacity",
                default=100.0,
                min_value=20.0,
                max_value=500.0,
                unit="gal",
            ),
        },
        applicable_when={"fuel_type": "gasoline", "engine_count": 1},
        source="ABYC H-33",
    ))
    
    PATTERN_REGISTRY.register(SystemPattern(
        id="fuel_twin_diesel",
        name="Twin Diesel Fuel System",
        domain=PatternDomain.FUEL,
        description="Diesel system for twin engine with cross-feed capability",
        components=[
            ComponentTemplate(
                component_type="fuel_tank",
                quantity=2,
                quantity_formula="2",
                properties={"material": "aluminum", "baffled": True},
                placement_zone="fuel_zone",
                placement_constraints={"symmetric": True, "below_fill": True},
            ),
            ComponentTemplate(
                component_type="fuel_fill",
                quantity=2,
                properties={"deck_fitting": True},
                placement_zone="gunwale",
                placement_constraints={"symmetric": True},
            ),
            ComponentTemplate(
                component_type="fuel_vent",
                quantity=2,
                properties={"screen": True},
                placement_zone="hull_side",
                placement_constraints={"symmetric": True, "above_waterline": True},
            ),
            ComponentTemplate(
                component_type="fuel_manifold",
                quantity=1,
                properties={"valved": True, "cross_feed": True},
                placement_zone="engine_room",
                placement_constraints={"accessible": True, "centered": True},
            ),
            ComponentTemplate(
                component_type="primary_filter",
                quantity=2,
                properties={"model": "racor_500fg", "duplex": False},
                placement_zone="engine_room",
                placement_constraints={"accessible": True, "near_engines": True},
            ),
            ComponentTemplate(
                component_type="secondary_filter",
                quantity=2,
                properties={"on_engine": True},
            ),
            ComponentTemplate(
                component_type="fuel_cooler",
                quantity=2,
                properties={"type": "plate_heat_exchanger"},
                placement_zone="engine_room",
            ),
        ],
        topology="""
            fill_p --> tank_p --> manifold
            fill_s --> tank_s --> manifold
            manifold --> primary_1 --> secondary_1 --> engine_1
            manifold --> primary_2 --> secondary_2 --> engine_2
            engine_1 --> cooler_1 --> return_manifold --> tank_p
            engine_2 --> cooler_2 --> return_manifold --> tank_s
            tank_p --> vent_p --> hull_fitting_p
            tank_s --> vent_s --> hull_fitting_s
        """,
        routing_rules={
            "fuel_supply": RoutingRule(
                from_port="manifold.outlet",
                to_port="engine.inlet",
                system_type="fuel_supply",
                constraints={
                    "min_bend_radius_factor": 4,
                    "max_unsupported_span_m": 0.8,
                    "material": "USCG_A1",
                },
            ),
            "fuel_return": RoutingRule(
                from_port="engine.return",
                to_port="return_manifold.inlet",
                system_type="fuel_return",
                constraints={
                    "avoid_hot_surfaces": True,
                    "cooler_required": True,
                },
            ),
        },
        constraints=[
            Constraint(
                name="cross_feed_capability",
                type="regulatory",
                expression="manifold.cross_feed == True",
                priority="required",
                message="Twin diesel requires cross-feed capability",
            ),
        ],
        parameters={
            "total_capacity_gal": ParameterSpec(
                name="total_capacity_gal",
                type="float",
                description="Total fuel capacity (split between tanks)",
                default=800.0,
                min_value=200.0,
                max_value=5000.0,
                unit="gal",
            ),
        },
        applicable_when={"fuel_type": "diesel", "engine_count": 2},
        source="ABYC H-33",
    ))
    
    # ==========================================================================
    # ELECTRICAL SYSTEM PATTERNS
    # ==========================================================================
    
    PATTERN_REGISTRY.register(SystemPattern(
        id="electrical_dc_basic",
        name="Basic DC Electrical System",
        domain=PatternDomain.ELECTRICAL,
        description="12V/24V DC system with house and engine batteries",
        components=[
            ComponentTemplate(
                component_type="battery_bank",
                quantity=2,
                properties={"type": "house", "chemistry": "agm"},
                placement_zone="battery_compartment",
                placement_constraints={"ventilated": True, "accessible": True},
            ),
            ComponentTemplate(
                component_type="battery_switch",
                quantity=1,
                properties={"type": "dual_bank"},
                placement_zone="helm",
                placement_constraints={"accessible": True},
            ),
            ComponentTemplate(
                component_type="dc_panel",
                quantity=1,
                properties={"circuits": 12},
                placement_zone="helm",
                placement_constraints={"visible": True},
            ),
            ComponentTemplate(
                component_type="bus_bar",
                quantity=2,
                properties={"type": "positive"},
            ),
            ComponentTemplate(
                component_type="shunt",
                quantity=1,
                properties={"for_monitor": True},
            ),
        ],
        topology="""
            battery_house --> switch --> dc_panel --> loads
            battery_engine --> switch --> starter
            alternator --> battery_engine
            charger --> battery_house
        """,
        routing_rules={
            "dc_power": RoutingRule(
                from_port="panel.circuit",
                to_port="load.input",
                system_type="electrical_dc",
                constraints={
                    "max_voltage_drop_pct": 3.0,
                    "support_interval_m": 0.5,
                    "chafe_protection": True,
                    "separation_from_fuel_m": 0.05,
                },
            ),
        },
        constraints=[
            Constraint(
                name="voltage_drop",
                type="electrical",
                expression="voltage_drop_pct <= 3.0",
                priority="required",
            ),
        ],
        parameters={
            "system_voltage": ParameterSpec(
                name="system_voltage",
                type="enum",
                description="System voltage",
                default="12V",
                enum_values=["12V", "24V"],
            ),
            "house_capacity_ah": ParameterSpec(
                name="house_capacity_ah",
                type="float",
                description="House battery capacity",
                default=400.0,
                min_value=100.0,
                max_value=2000.0,
                unit="Ah",
            ),
        },
        applicable_when={"has_generator": False},
        source="ABYC E-11",
    ))
    
    # ==========================================================================
    # PLUMBING PATTERNS
    # ==========================================================================
    
    PATTERN_REGISTRY.register(SystemPattern(
        id="freshwater_pressurized",
        name="Pressurized Fresh Water System",
        domain=PatternDomain.PLUMBING,
        description="Fresh water with pressure pump and accumulator",
        components=[
            ComponentTemplate(
                component_type="water_tank",
                quantity=1,
                properties={"material": "polyethylene", "potable": True},
                placement_zone="below_deck",
                placement_constraints={"low_cg": True, "fill_accessible": True},
            ),
            ComponentTemplate(
                component_type="water_pump",
                quantity=1,
                properties={"type": "demand", "gpm": 3.5},
                placement_zone="utility",
                placement_constraints={"accessible": True, "below_tank": True},
            ),
            ComponentTemplate(
                component_type="accumulator",
                quantity=1,
                properties={"capacity_gal": 0.5},
                placement_zone="utility",
                placement_constraints={"near_pump": True},
            ),
            ComponentTemplate(
                component_type="water_heater",
                quantity=1,
                required=False,
                properties={"capacity_gal": 6, "type": "engine_heat_exchanger"},
            ),
            ComponentTemplate(
                component_type="deck_fill",
                quantity=1,
                properties={"labeled": True},
                placement_zone="deck",
            ),
        ],
        topology="""
            deck_fill --> tank --> pump --> accumulator --> distribution
            distribution --> galley_sink
            distribution --> head_sink
            distribution --> shower
            distribution --> heater --> hot_distribution
        """,
        routing_rules={
            "cold_water": RoutingRule(
                from_port="accumulator.outlet",
                to_port="fixture.cold_inlet",
                system_type="freshwater",
                constraints={
                    "material": "pex",
                    "min_bend_radius_factor": 6,
                    "drain_slope": True,
                },
            ),
        },
        parameters={
            "tank_capacity_gal": ParameterSpec(
                name="tank_capacity_gal",
                type="float",
                description="Fresh water tank capacity",
                default=100.0,
                min_value=20.0,
                max_value=500.0,
                unit="gal",
            ),
        },
        applicable_when={},
        source="ABYC H-23",
    ))


# Register on import
register_builtin_patterns()
```

### 2.4 Pattern Instantiation

```python
# cortex/generative/patterns/instantiate.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import uuid

from .schema import SystemPattern, ComponentTemplate
from ..artifact_graph import ArtifactGraph, Component, BoundingBox


@dataclass
class InstantiationResult:
    """Result of pattern instantiation."""
    success: bool
    components: List[Component] = field(default_factory=list)
    connections: List[Dict[str, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def instantiate_pattern(
    pattern: SystemPattern,
    parameters: Dict[str, Any],
    space_envelope: BoundingBox,
    graph: ArtifactGraph,
    zone_assignments: Optional[Dict[str, str]] = None,
) -> InstantiationResult:
    """
    Instantiate a system pattern into concrete components.
    
    Args:
        pattern: The pattern to instantiate
        parameters: Parameter values for the pattern
        space_envelope: Available space for the system
        graph: The artifact graph to add components to
        zone_assignments: Optional zone assignments for components
    
    Returns:
        InstantiationResult with created components
    """
    result = InstantiationResult(success=True)
    
    # Resolve parameter-dependent quantities
    resolved_params = _resolve_parameters(pattern, parameters)
    
    # Create components from templates
    component_map: Dict[str, List[Component]] = {}
    
    for template in pattern.components:
        # Calculate quantity
        quantity = _calculate_quantity(template, resolved_params)
        
        # Create component instances
        instances = []
        for i in range(quantity):
            component = _create_component(
                template=template,
                index=i,
                parameters=resolved_params,
                pattern_id=pattern.id,
            )
            instances.append(component)
            result.components.append(component)
        
        component_map[template.component_type] = instances
    
    # Parse topology and create connections
    connections = _parse_topology(pattern.topology, component_map)
    result.connections = connections
    
    # Add components to graph
    for component in result.components:
        try:
            graph.add_component(component)
        except Exception as e:
            result.errors.append(f"Failed to add {component.id}: {e}")
            result.success = False
    
    # Add connections to graph
    for conn in connections:
        try:
            graph.add_connection(
                from_component=conn["from_component"],
                from_port=conn["from_port"],
                to_component=conn["to_component"],
                to_port=conn["to_port"],
                connection_type=conn.get("type", "pipe"),
            )
        except Exception as e:
            result.warnings.append(f"Failed to add connection: {e}")
    
    return result


def _resolve_parameters(
    pattern: SystemPattern,
    provided: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve parameters with defaults."""
    resolved = {}
    for name, spec in pattern.parameters.items():
        if name in provided:
            resolved[name] = provided[name]
        else:
            resolved[name] = spec.default
    return resolved


def _calculate_quantity(
    template: ComponentTemplate,
    parameters: Dict[str, Any],
) -> int:
    """Calculate component quantity from template."""
    if template.quantity_formula:
        # Safe eval of formula
        try:
            import math
            result = eval(template.quantity_formula, {"__builtins__": {}}, {
                "ceil": math.ceil,
                "floor": math.floor,
                **parameters,
            })
            return int(result)
        except Exception:
            return template.quantity
    return template.quantity


def _create_component(
    template: ComponentTemplate,
    index: int,
    parameters: Dict[str, Any],
    pattern_id: str,
) -> Component:
    """Create a component instance from template."""
    suffix = f"_{index}" if index > 0 else ""
    
    return Component(
        id=f"{template.component_type}{suffix}_{uuid.uuid4().hex[:8]}",
        type=template.component_type,
        properties={
            **template.properties,
            "pattern_id": pattern_id,
            "template_index": index,
        },
        placement_zone=template.placement_zone,
        placement_constraints=template.placement_constraints,
    )


def _parse_topology(
    topology: str,
    component_map: Dict[str, List[Component]],
) -> List[Dict[str, str]]:
    """Parse topology DSL into connections."""
    connections = []
    
    for line in topology.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Parse: component_a --> component_b
        if "-->" in line:
            parts = line.split("-->")
            for i in range(len(parts) - 1):
                from_spec = parts[i].strip()
                to_spec = parts[i + 1].strip()
                
                from_comp, from_port = _parse_port_spec(from_spec)
                to_comp, to_port = _parse_port_spec(to_spec)
                
                # Resolve component references
                from_instances = component_map.get(from_comp, [])
                to_instances = component_map.get(to_comp, [])
                
                if from_instances and to_instances:
                    connections.append({
                        "from_component": from_instances[0].id,
                        "from_port": from_port,
                        "to_component": to_instances[0].id,
                        "to_port": to_port,
                    })
    
    return connections


def _parse_port_spec(spec: str) -> tuple:
    """Parse 'component.port' or 'component' into (component, port)."""
    if "." in spec:
        parts = spec.split(".", 1)
        return parts[0], parts[1]
    return spec, "default"
```


---

## 3. Space Allocation

### 3.1 Space Envelope and Zone Representation

```python
# cortex/generative/space/zones.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid


class ZoneType(Enum):
    ENGINE_ROOM = "engine_room"
    FUEL = "fuel"
    ACCOMMODATION = "accommodation"
    UTILITY = "utility"
    STORAGE = "storage"
    COCKPIT = "cockpit"
    HELM = "helm"
    LAZARETTE = "lazarette"
    FOREPEAK = "forepeak"
    MACHINERY = "machinery"


@dataclass
class BoundingBox:
    """3D axis-aligned bounding box."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    
    @property
    def volume(self) -> float:
        return (self.max_x - self.min_x) * (self.max_y - self.min_y) * (self.max_z - self.min_z)
    
    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )
    
    def contains(self, point: Tuple[float, float, float]) -> bool:
        x, y, z = point
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)
    
    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.max_x < other.min_x or self.min_x > other.max_x or
            self.max_y < other.min_y or self.min_y > other.max_y or
            self.max_z < other.min_z or self.min_z > other.max_z
        )


@dataclass
class Zone:
    """A spatial zone within the vessel."""
    id: str
    name: str
    zone_type: ZoneType
    bounds: BoundingBox
    
    # Adjacency requirements
    must_be_adjacent_to: List[str] = field(default_factory=list)
    must_not_be_adjacent_to: List[str] = field(default_factory=list)
    
    # Access requirements
    requires_access_from: List[str] = field(default_factory=list)
    
    # Environmental
    ventilation_required: bool = False
    climate_controlled: bool = False
    
    # Constraints
    min_volume_m3: Optional[float] = None
    max_weight_kg: Optional[float] = None
    
    # Metadata
    systems_allowed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "zone_type": self.zone_type.value,
            "bounds": {
                "min": [self.bounds.min_x, self.bounds.min_y, self.bounds.min_z],
                "max": [self.bounds.max_x, self.bounds.max_y, self.bounds.max_z],
            },
            "volume_m3": self.bounds.volume,
        }


@dataclass
class SpaceRequirements:
    """Requirements for space allocation."""
    zones: Dict[ZoneType, float]  # zone_type -> minimum volume m³
    adjacency_required: List[Tuple[ZoneType, ZoneType]] = field(default_factory=list)
    adjacency_forbidden: List[Tuple[ZoneType, ZoneType]] = field(default_factory=list)
    priorities: Dict[ZoneType, int] = field(default_factory=dict)  # Higher = more important


@dataclass  
class SpaceAllocation:
    """Result of space allocation."""
    zones: List[Zone]
    unallocated_volume_m3: float
    satisfaction_score: float  # 0-1, how well requirements were met
    violations: List[str] = field(default_factory=list)
```

### 3.2 Space Allocation Algorithm

```python
# cortex/generative/space/allocator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

from .zones import (
    Zone, ZoneType, BoundingBox, SpaceRequirements, SpaceAllocation
)

logger = logging.getLogger(__name__)


@dataclass
class SpaceConstraint:
    """Constraint for space allocation."""
    name: str
    check: callable  # (zones: List[Zone]) -> bool
    priority: str = "required"  # "required" or "preferred"


class SpaceAllocator:
    """
    Allocates zones within a hull envelope.
    
    Uses a priority-based bin packing approach:
    1. Sort zones by priority (engine room, fuel, accommodation)
    2. Allocate from aft to forward (typical vessel layout)
    3. Enforce adjacency constraints
    4. Iterate to improve satisfaction
    
    REUSES: magnet/routing/router/zone_manager.py concepts
    """
    
    def __init__(self, envelope: BoundingBox):
        self._envelope = envelope
        self._zones: List[Zone] = []
    
    def allocate(
        self,
        requirements: SpaceRequirements,
        constraints: Optional[List[SpaceConstraint]] = None,
    ) -> SpaceAllocation:
        """
        Allocate zones within the envelope.
        
        Args:
            requirements: Space requirements
            constraints: Additional constraints
        
        Returns:
            SpaceAllocation with zones
        """
        constraints = constraints or []
        
        # Sort zones by priority (descending)
        sorted_zones = sorted(
            requirements.zones.items(),
            key=lambda x: requirements.priorities.get(x[0], 0),
            reverse=True,
        )
        
        # Initial allocation: slice envelope longitudinally
        total_volume = self._envelope.volume
        total_requested = sum(requirements.zones.values())
        scale_factor = min(1.0, total_volume / max(total_requested, 0.001))
        
        allocated_zones: List[Zone] = []
        current_x = self._envelope.min_x
        
        for zone_type, min_volume in sorted_zones:
            # Calculate zone dimensions
            allocated_volume = min_volume * scale_factor
            zone_length = self._calculate_zone_length(allocated_volume, current_x)
            
            if current_x + zone_length > self._envelope.max_x:
                zone_length = self._envelope.max_x - current_x
            
            if zone_length <= 0:
                continue
            
            zone = Zone(
                id=f"zone_{zone_type.value}_{len(allocated_zones)}",
                name=zone_type.value.replace("_", " ").title(),
                zone_type=zone_type,
                bounds=BoundingBox(
                    min_x=current_x,
                    min_y=self._envelope.min_y,
                    min_z=self._envelope.min_z,
                    max_x=current_x + zone_length,
                    max_y=self._envelope.max_y,
                    max_z=self._envelope.max_z,
                ),
            )
            
            # Apply adjacency requirements
            zone.must_be_adjacent_to = [
                z.value for z, adj in requirements.adjacency_required 
                if adj == zone_type
            ]
            zone.must_not_be_adjacent_to = [
                z.value for z, adj in requirements.adjacency_forbidden
                if adj == zone_type
            ]
            
            allocated_zones.append(zone)
            current_x += zone_length
        
        # Check constraints and calculate satisfaction
        violations = []
        for constraint in constraints:
            if not constraint.check(allocated_zones):
                violations.append(f"Constraint '{constraint.name}' violated")
        
        # Calculate satisfaction score
        satisfaction = self._calculate_satisfaction(
            requirements, allocated_zones, violations
        )
        
        return SpaceAllocation(
            zones=allocated_zones,
            unallocated_volume_m3=max(0, total_volume - sum(z.bounds.volume for z in allocated_zones)),
            satisfaction_score=satisfaction,
            violations=violations,
        )
    
    def _calculate_zone_length(self, volume: float, start_x: float) -> float:
        """Calculate zone length given volume and starting position."""
        # Simplified: assume rectangular cross-section
        cross_section_area = (
            (self._envelope.max_y - self._envelope.min_y) *
            (self._envelope.max_z - self._envelope.min_z)
        )
        if cross_section_area <= 0:
            return 0
        return volume / cross_section_area
    
    def _calculate_satisfaction(
        self,
        requirements: SpaceRequirements,
        zones: List[Zone],
        violations: List[str],
    ) -> float:
        """Calculate how well requirements were satisfied."""
        if not requirements.zones:
            return 1.0
        
        # Volume satisfaction
        total_requested = sum(requirements.zones.values())
        total_allocated = sum(z.bounds.volume for z in zones)
        volume_satisfaction = min(1.0, total_allocated / max(total_requested, 0.001))
        
        # Constraint satisfaction
        constraint_penalty = len(violations) * 0.1
        
        return max(0.0, volume_satisfaction - constraint_penalty)
```

---

## 4. Component Placement

### 4.1 Placement Solver

```python
# cortex/generative/placement/solver.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import logging
import math

from ..artifact_graph import ArtifactGraph, Component
from ..space.zones import Zone, BoundingBox

logger = logging.getLogger(__name__)


@dataclass
class PlacementConstraint:
    """Constraint for component placement."""
    name: str
    type: str  # "clearance", "access", "structural", "proximity"
    value: Any
    required: bool = True


@dataclass
class PlacementPreference:
    """Preference (soft constraint) for placement."""
    name: str
    near: Optional[List[str]] = None  # Component IDs to be near
    away_from: Optional[List[str]] = None  # Component IDs to avoid
    weight: float = 1.0


@dataclass
class Placement:
    """Result of placement computation."""
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float]  # Euler angles
    clearances: Dict[str, float]
    score: float  # 0-1, how well placement satisfies preferences
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "orientation": list(self.orientation),
            "clearances": self.clearances,
            "score": self.score,
        }


@dataclass
class ComponentTemplate:
    """Template for a component to be placed."""
    component_type: str
    dimensions: Tuple[float, float, float]  # length, width, height
    ports: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    weight_kg: float = 0.0
    requires_access: List[str] = field(default_factory=list)  # "top", "front", "side"


class PlacementSolver:
    """
    Solves component placement as constraint satisfaction.
    
    Approach:
    1. Discretize zone into candidate positions
    2. Filter by hard constraints (clearance, access)
    3. Score by soft constraints (proximity preferences)
    4. Return best valid placement
    
    REUSES: Concepts from magnet/routing/router/zone_manager.py
    """
    
    def __init__(
        self,
        graph: ArtifactGraph,
        resolution_m: float = 0.1,
    ):
        self._graph = graph
        self._resolution = resolution_m
    
    def solve(
        self,
        component: ComponentTemplate,
        zone: Zone,
        constraints: List[PlacementConstraint],
        preferences: Optional[PlacementPreference] = None,
        existing: Optional[List[Component]] = None,
    ) -> Optional[Placement]:
        """
        Find valid placement for component in zone.
        
        Args:
            component: Component template to place
            zone: Zone to place in
            constraints: Hard constraints
            preferences: Soft preferences
            existing: Already placed components
        
        Returns:
            Placement if found, None if impossible
        """
        existing = existing or []
        
        # Generate candidate positions
        candidates = self._generate_candidates(component, zone)
        
        if not candidates:
            logger.warning(f"No candidate positions for {component.component_type} in {zone.id}")
            return None
        
        # Filter by constraints
        valid_candidates = []
        for pos in candidates:
            if self._satisfies_constraints(component, pos, constraints, existing, zone):
                valid_candidates.append(pos)
        
        if not valid_candidates:
            logger.warning(f"No valid positions for {component.component_type} after constraint filtering")
            return None
        
        # Score by preferences
        scored = []
        for pos in valid_candidates:
            score = self._score_placement(component, pos, preferences, existing)
            scored.append((pos, score))
        
        # Return best placement
        best_pos, best_score = max(scored, key=lambda x: x[1])
        
        clearances = self._compute_clearances(component, best_pos, existing, zone)
        
        return Placement(
            position=best_pos,
            orientation=(0.0, 0.0, 0.0),  # Default orientation
            clearances=clearances,
            score=best_score,
        )
    
    def _generate_candidates(
        self,
        component: ComponentTemplate,
        zone: Zone,
    ) -> List[Tuple[float, float, float]]:
        """Generate candidate positions within zone."""
        candidates = []
        
        # Component half-dimensions
        hl, hw, hh = [d / 2 for d in component.dimensions]
        
        # Iterate over grid within zone
        x = zone.bounds.min_x + hl
        while x <= zone.bounds.max_x - hl:
            y = zone.bounds.min_y + hw
            while y <= zone.bounds.max_y - hw:
                z = zone.bounds.min_z + hh
                while z <= zone.bounds.max_z - hh:
                    candidates.append((x, y, z))
                    z += self._resolution
                y += self._resolution
            x += self._resolution
        
        return candidates
    
    def _satisfies_constraints(
        self,
        component: ComponentTemplate,
        position: Tuple[float, float, float],
        constraints: List[PlacementConstraint],
        existing: List[Component],
        zone: Zone,
    ) -> bool:
        """Check if position satisfies all hard constraints."""
        bbox = self._component_bbox(component, position)
        
        for constraint in constraints:
            if not constraint.required:
                continue
            
            if constraint.type == "clearance":
                min_clearance = float(constraint.value)
                for other in existing:
                    other_bbox = self._get_component_bbox(other)
                    if other_bbox and self._distance_between(bbox, other_bbox) < min_clearance:
                        return False
            
            elif constraint.type == "access":
                direction = str(constraint.value)
                if not self._has_access(bbox, direction, existing, zone):
                    return False
            
            elif constraint.type == "structural":
                if constraint.value == "floor_mounted":
                    if position[2] > zone.bounds.min_z + 0.1:
                        return False
        
        # Check no collision with existing
        for other in existing:
            other_bbox = self._get_component_bbox(other)
            if other_bbox and bbox.intersects(other_bbox):
                return False
        
        return True
    
    def _score_placement(
        self,
        component: ComponentTemplate,
        position: Tuple[float, float, float],
        preferences: Optional[PlacementPreference],
        existing: List[Component],
    ) -> float:
        """Score placement by preferences (0-1)."""
        if not preferences:
            return 0.5
        
        score = 0.5
        
        # Near preference
        if preferences.near:
            for target_id in preferences.near:
                target = next((c for c in existing if c.id == target_id), None)
                if target and hasattr(target, 'position'):
                    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(position, target.position)))
                    # Closer = better, normalize by typical room size
                    score += preferences.weight * max(0, 1 - dist / 5.0) * 0.25
        
        # Away from preference
        if preferences.away_from:
            for target_id in preferences.away_from:
                target = next((c for c in existing if c.id == target_id), None)
                if target and hasattr(target, 'position'):
                    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(position, target.position)))
                    # Farther = better
                    score += preferences.weight * min(1, dist / 5.0) * 0.25
        
        return min(1.0, max(0.0, score))
    
    def _component_bbox(
        self,
        component: ComponentTemplate,
        position: Tuple[float, float, float],
    ) -> BoundingBox:
        """Create bounding box for component at position."""
        hl, hw, hh = [d / 2 for d in component.dimensions]
        x, y, z = position
        return BoundingBox(
            min_x=x - hl, max_x=x + hl,
            min_y=y - hw, max_y=y + hw,
            min_z=z - hh, max_z=z + hh,
        )
    
    def _get_component_bbox(self, component: Component) -> Optional[BoundingBox]:
        """Get bounding box of existing component."""
        if hasattr(component, 'bounds'):
            return component.bounds
        if hasattr(component, 'position') and hasattr(component, 'dimensions'):
            return self._component_bbox(
                ComponentTemplate(
                    component_type=component.type,
                    dimensions=component.dimensions,
                ),
                component.position,
            )
        return None
    
    def _distance_between(self, a: BoundingBox, b: BoundingBox) -> float:
        """Compute minimum distance between two bounding boxes."""
        dx = max(0, max(a.min_x - b.max_x, b.min_x - a.max_x))
        dy = max(0, max(a.min_y - b.max_y, b.min_y - a.max_y))
        dz = max(0, max(a.min_z - b.max_z, b.min_z - a.max_z))
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    
    def _has_access(
        self,
        bbox: BoundingBox,
        direction: str,
        existing: List[Component],
        zone: Zone,
    ) -> bool:
        """Check if there's access from the given direction."""
        # Simplified: check if path to zone boundary is clear
        return True  # Full implementation would ray-cast
    
    def _compute_clearances(
        self,
        component: ComponentTemplate,
        position: Tuple[float, float, float],
        existing: List[Component],
        zone: Zone,
    ) -> Dict[str, float]:
        """Compute clearances to zone boundaries and other components."""
        bbox = self._component_bbox(component, position)
        
        return {
            "forward": zone.bounds.max_x - bbox.max_x,
            "aft": bbox.min_x - zone.bounds.min_x,
            "port": bbox.min_y - zone.bounds.min_y,
            "starboard": zone.bounds.max_y - bbox.max_y,
            "above": zone.bounds.max_z - bbox.max_z,
            "below": bbox.min_z - zone.bounds.min_z,
        }
```

---

## 5. Routing Engine

### 5.1 Routing Constraints and Representation

```python
# cortex/generative/routing/constraints.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class RoutingConstraints:
    """Constraints for routing a connection."""
    system_type: str  # "fuel", "water", "electrical", "exhaust"
    
    # Geometric constraints
    min_bend_radius_m: float = 0.1
    max_unsupported_span_m: float = 1.0
    
    # Slope requirements
    required_slope: Optional[float] = None  # Positive = rises toward destination
    slope_direction: str = "any"  # "any", "toward_source", "toward_destination"
    
    # Clearance requirements
    clearance_from_heat_m: float = 0.2
    clearance_from_electrical_m: float = 0.05
    
    # Accessibility
    accessibility: str = "serviceable"  # "hidden", "serviceable", "visible"
    
    # Material/regulatory
    material: str = ""
    avoid_zones: List[str] = field(default_factory=list)


@dataclass
class Fitting:
    """A fitting in a route (elbow, tee, etc.)."""
    id: str
    fitting_type: str  # "elbow_90", "elbow_45", "tee", "reducer", "coupling"
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float]


@dataclass
class Support:
    """A support point for the route."""
    id: str
    support_type: str  # "hanger", "clamp", "bracket"
    position: Tuple[float, float, float]
    attached_to: str  # Structure element ID


@dataclass
class Route:
    """A complete route between components."""
    id: str
    system_type: str
    from_component: str
    from_port: str
    to_component: str
    to_port: str
    
    # Path geometry
    path: List[Tuple[float, float, float]] = field(default_factory=list)
    
    # Fittings and supports
    fittings: List[Fitting] = field(default_factory=list)
    supports: List[Support] = field(default_factory=list)
    
    # Metrics
    total_length_m: float = 0.0
    bend_count: int = 0
    
    # Validation
    validation_status: str = "pending"
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "system_type": self.system_type,
            "from": f"{self.from_component}.{self.from_port}",
            "to": f"{self.to_component}.{self.to_port}",
            "path": [list(p) for p in self.path],
            "total_length_m": self.total_length_m,
            "bend_count": self.bend_count,
            "fitting_count": len(self.fittings),
            "support_count": len(self.supports),
            "validation_status": self.validation_status,
        }
```

### 5.2 Routing Engine Implementation

```python
# cortex/generative/routing/engine.py
# REUSES: magnet/routing/router/path_optimizer.py, steiner_router.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
import heapq
import math
import logging
import uuid

from .constraints import RoutingConstraints, Route, Fitting, Support
from ..artifact_graph import ArtifactGraph, Component
from ..space.zones import BoundingBox

logger = logging.getLogger(__name__)


@dataclass
class RoutingRequest:
    """Request to route a connection."""
    from_component: str
    from_port: str
    to_component: str
    to_port: str
    system_type: str
    constraints: RoutingConstraints
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingResult:
    """Result of routing computation."""
    success: bool
    route: Optional[Route] = None
    alternatives: List[Route] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RoutingEngine:
    """
    Routes connections between components.
    
    Uses A* pathfinding with domain-specific cost functions.
    
    REUSES: magnet/routing/router/path_optimizer.py
            magnet/routing/graph/compartment_graph.py
    """
    
    def __init__(
        self,
        graph: ArtifactGraph,
        resolution_m: float = 0.05,
    ):
        self._graph = graph
        self._resolution = resolution_m
        self._occupancy: Set[Tuple[int, int, int]] = set()
    
    def route(self, request: RoutingRequest) -> RoutingResult:
        """
        Compute route for a connection.
        
        Args:
            request: Routing request
        
        Returns:
            RoutingResult with computed route
        """
        result = RoutingResult(success=False)
        
        # Get endpoint positions
        start = self._get_port_position(request.from_component, request.from_port)
        end = self._get_port_position(request.to_component, request.to_port)
        
        if start is None or end is None:
            result.errors.append("Could not resolve port positions")
            return result
        
        # Run A* pathfinding
        path = self._astar(start, end, request.constraints)
        
        if not path:
            result.errors.append("No valid path found")
            return result
        
        # Smooth path to respect bend radius
        smoothed_path = self._smooth_path(path, request.constraints.min_bend_radius_m)
        
        # Generate fittings at direction changes
        fittings = self._generate_fittings(smoothed_path, request.constraints)
        
        # Generate supports at intervals
        supports = self._generate_supports(
            smoothed_path,
            request.constraints.max_unsupported_span_m,
        )
        
        # Create route
        route = Route(
            id=f"route_{uuid.uuid4().hex[:8]}",
            system_type=request.system_type,
            from_component=request.from_component,
            from_port=request.from_port,
            to_component=request.to_component,
            to_port=request.to_port,
            path=smoothed_path,
            fittings=fittings,
            supports=supports,
            total_length_m=self._path_length(smoothed_path),
            bend_count=len(fittings),
            validation_status="computed",
        )
        
        # Mark path as occupied
        self._mark_occupied(smoothed_path)
        
        result.success = True
        result.route = route
        return result
    
    def _astar(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        constraints: RoutingConstraints,
    ) -> Optional[List[Tuple[float, float, float]]]:
        """A* pathfinding with domain constraints."""
        
        def heuristic(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) * self._resolution
        
        def to_grid(p: Tuple[float, float, float]) -> Tuple[int, int, int]:
            return tuple(int(c / self._resolution) for c in p)
        
        def from_grid(g: Tuple[int, int, int]) -> Tuple[float, float, float]:
            return tuple(c * self._resolution for c in g)
        
        start_grid = to_grid(start)
        end_grid = to_grid(end)
        
        # Priority queue: (f_score, g_score, node, path)
        open_set = [(heuristic(start_grid, end_grid), 0, start_grid, [start_grid])]
        visited: Set[Tuple[int, int, int]] = set()
        
        # 26-connectivity (3D)
        neighbors = [
            (dx, dy, dz)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
            if (dx, dy, dz) != (0, 0, 0)
        ]
        
        max_iterations = 100000
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            f, g, current, path = heapq.heappop(open_set)
            
            if current == end_grid:
                return [from_grid(p) for p in path]
            
            if current in visited:
                continue
            visited.add(current)
            
            for dx, dy, dz in neighbors:
                neighbor = (current[0] + dx, current[1] + dy, current[2] + dz)
                
                if neighbor in visited:
                    continue
                
                if neighbor in self._occupancy:
                    continue
                
                # Check constraints
                world_pos = from_grid(neighbor)
                if not self._is_valid_position(world_pos, constraints):
                    continue
                
                # Cost: prefer axis-aligned, penalize diagonals
                move_cost = math.sqrt(dx*dx + dy*dy + dz*dz) * self._resolution
                
                # Penalize zone crossings
                if self._crosses_avoid_zone(from_grid(current), world_pos, constraints.avoid_zones):
                    move_cost += 10.0
                
                new_g = g + move_cost
                new_f = new_g + heuristic(neighbor, end_grid)
                
                heapq.heappush(open_set, (new_f, new_g, neighbor, path + [neighbor]))
        
        return None
    
    def _get_port_position(
        self,
        component_id: str,
        port_name: str,
    ) -> Optional[Tuple[float, float, float]]:
        """Get world position of component port."""
        component = self._graph.get_component(component_id)
        if not component:
            return None
        
        if hasattr(component, 'ports') and port_name in component.ports:
            # Port offset in component space
            offset = component.ports[port_name]
            # Transform to world space
            pos = component.position if hasattr(component, 'position') else (0, 0, 0)
            return tuple(p + o for p, o in zip(pos, offset))
        
        # Default: component center
        if hasattr(component, 'position'):
            return component.position
        
        return None
    
    def _is_valid_position(
        self,
        position: Tuple[float, float, float],
        constraints: RoutingConstraints,
    ) -> bool:
        """Check if position is valid for routing."""
        # Check within vessel bounds
        bounds = self._graph.get_bounds()
        if bounds:
            x, y, z = position
            if not (bounds.min_x <= x <= bounds.max_x and
                    bounds.min_y <= y <= bounds.max_y and
                    bounds.min_z <= z <= bounds.max_z):
                return False
        
        # Check clearance from obstacles
        # (Simplified - full implementation would use spatial index)
        return True
    
    def _crosses_avoid_zone(
        self,
        from_pos: Tuple[float, float, float],
        to_pos: Tuple[float, float, float],
        avoid_zones: List[str],
    ) -> bool:
        """Check if path segment crosses an avoid zone."""
        if not avoid_zones:
            return False
        
        for zone_id in avoid_zones:
            zone = self._graph.get_zone(zone_id)
            if zone and zone.bounds:
                midpoint = tuple((a + b) / 2 for a, b in zip(from_pos, to_pos))
                if zone.bounds.contains(midpoint):
                    return True
        return False
    
    def _smooth_path(
        self,
        path: List[Tuple[float, float, float]],
        min_bend_radius: float,
    ) -> List[Tuple[float, float, float]]:
        """Smooth path to respect minimum bend radius."""
        if len(path) < 3:
            return path
        
        # Simplified: just return path
        # Full implementation would use spline fitting with curvature constraints
        return path
    
    def _generate_fittings(
        self,
        path: List[Tuple[float, float, float]],
        constraints: RoutingConstraints,
    ) -> List[Fitting]:
        """Generate fittings at direction changes."""
        fittings = []
        
        for i in range(1, len(path) - 1):
            prev_dir = tuple(b - a for a, b in zip(path[i-1], path[i]))
            next_dir = tuple(b - a for a, b in zip(path[i], path[i+1]))
            
            # Check for direction change
            if prev_dir != next_dir:
                # Calculate angle
                dot = sum(a * b for a, b in zip(prev_dir, next_dir))
                mag1 = math.sqrt(sum(x*x for x in prev_dir))
                mag2 = math.sqrt(sum(x*x for x in next_dir))
                
                if mag1 > 0 and mag2 > 0:
                    cos_angle = dot / (mag1 * mag2)
                    angle_deg = math.degrees(math.acos(max(-1, min(1, cos_angle))))
                    
                    fitting_type = "elbow_90" if angle_deg > 60 else "elbow_45"
                    
                    fittings.append(Fitting(
                        id=f"fitting_{uuid.uuid4().hex[:8]}",
                        fitting_type=fitting_type,
                        position=path[i],
                        orientation=(0, 0, 0),
                    ))
        
        return fittings
    
    def _generate_supports(
        self,
        path: List[Tuple[float, float, float]],
        max_span: float,
    ) -> List[Support]:
        """Generate supports at intervals."""
        supports = []
        accumulated_length = 0.0
        
        for i in range(1, len(path)):
            segment_length = math.sqrt(sum(
                (b - a) ** 2 for a, b in zip(path[i-1], path[i])
            ))
            accumulated_length += segment_length
            
            if accumulated_length >= max_span:
                supports.append(Support(
                    id=f"support_{uuid.uuid4().hex[:8]}",
                    support_type="hanger",
                    position=path[i],
                    attached_to="structure",
                ))
                accumulated_length = 0.0
        
        return supports
    
    def _path_length(self, path: List[Tuple[float, float, float]]) -> float:
        """Calculate total path length."""
        if len(path) < 2:
            return 0.0
        
        return sum(
            math.sqrt(sum((b - a) ** 2 for a, b in zip(path[i], path[i+1])))
            for i in range(len(path) - 1)
        )
    
    def _mark_occupied(self, path: List[Tuple[float, float, float]]) -> None:
        """Mark path positions as occupied."""
        for point in path:
            grid = tuple(int(c / self._resolution) for c in point)
            self._occupancy.add(grid)
```


---

## 6. Clash Detection

```python
# cortex/generative/clash/detector.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
import math

from ..artifact_graph import ArtifactGraph, Component
from ..space.zones import BoundingBox


@dataclass
class Clash:
    """A detected clash between components."""
    component_a: str
    component_b: str
    intersection_volume_m3: float
    intersection_point: Tuple[float, float, float]
    severity: str  # "hard" (geometric), "soft" (clearance), "clearance" (minimum distance)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_a": self.component_a,
            "component_b": self.component_b,
            "intersection_volume_m3": self.intersection_volume_m3,
            "intersection_point": list(self.intersection_point),
            "severity": self.severity,
        }


class ClashDetector:
    """
    Detects geometric clashes between components.
    
    Uses Bounding Volume Hierarchy (BVH) for efficient broad-phase,
    then precise intersection for narrow-phase.
    """
    
    def __init__(self, graph: ArtifactGraph):
        self._graph = graph
        self._bvh_dirty = True
        self._bvh: Optional[Any] = None
    
    def detect_clashes(
        self,
        scope: Optional[str] = None,
        tolerance_m: float = 0.001,
        check_clearances: bool = True,
        min_clearance_m: float = 0.05,
    ) -> List[Clash]:
        """
        Detect all clashes in the graph.
        
        Args:
            scope: Optional zone ID to limit scope
            tolerance_m: Geometric tolerance for intersection
            check_clearances: Whether to check minimum clearances
            min_clearance_m: Minimum required clearance
        
        Returns:
            List of detected clashes
        """
        clashes = []
        
        # Get components to check
        components = self._get_components_in_scope(scope)
        
        if len(components) < 2:
            return clashes
        
        # Rebuild BVH if needed
        if self._bvh_dirty:
            self._build_bvh(components)
        
        # Broad-phase: BVH overlap query
        potential_pairs = self._bvh_query(components)
        
        # Narrow-phase: precise intersection
        for comp_a, comp_b in potential_pairs:
            clash = self._check_pair(comp_a, comp_b, tolerance_m)
            if clash:
                clashes.append(clash)
            elif check_clearances:
                clearance_clash = self._check_clearance(comp_a, comp_b, min_clearance_m)
                if clearance_clash:
                    clashes.append(clearance_clash)
        
        return clashes
    
    def detect_incremental(
        self,
        changed_component: str,
        tolerance_m: float = 0.001,
    ) -> List[Clash]:
        """
        Detect clashes involving a single changed component.
        
        More efficient than full detection after single component changes.
        """
        component = self._graph.get_component(changed_component)
        if not component:
            return []
        
        clashes = []
        all_components = self._graph.list_components()
        
        for other in all_components:
            if other.id == changed_component:
                continue
            
            clash = self._check_pair(component, other, tolerance_m)
            if clash:
                clashes.append(clash)
        
        return clashes
    
    def suggest_resolution(self, clash: Clash) -> List[Dict[str, Any]]:
        """Suggest resolutions for a clash."""
        suggestions = []
        
        # Get components
        comp_a = self._graph.get_component(clash.component_a)
        comp_b = self._graph.get_component(clash.component_b)
        
        if not comp_a or not comp_b:
            return suggestions
        
        # Calculate separation vector
        if hasattr(comp_a, 'position') and hasattr(comp_b, 'position'):
            sep = tuple(b - a for a, b in zip(comp_a.position, comp_b.position))
            mag = math.sqrt(sum(s*s for s in sep))
            
            if mag > 0:
                # Normalize
                sep_norm = tuple(s / mag for s in sep)
                
                # Suggest moving each component
                move_dist = clash.intersection_volume_m3 ** (1/3) + 0.05
                
                suggestions.append({
                    "action": "move",
                    "component": clash.component_a,
                    "direction": tuple(-s for s in sep_norm),
                    "distance_m": move_dist / 2,
                    "description": f"Move {clash.component_a} away from {clash.component_b}",
                })
                
                suggestions.append({
                    "action": "move",
                    "component": clash.component_b,
                    "direction": sep_norm,
                    "distance_m": move_dist / 2,
                    "description": f"Move {clash.component_b} away from {clash.component_a}",
                })
        
        return suggestions
    
    def _get_components_in_scope(self, scope: Optional[str]) -> List[Component]:
        """Get components within scope."""
        all_components = self._graph.list_components()
        
        if not scope:
            return all_components
        
        zone = self._graph.get_zone(scope)
        if not zone:
            return all_components
        
        return [c for c in all_components if self._in_zone(c, zone)]
    
    def _in_zone(self, component: Component, zone: Any) -> bool:
        """Check if component is in zone."""
        if not hasattr(component, 'position'):
            return True
        if not hasattr(zone, 'bounds'):
            return True
        return zone.bounds.contains(component.position)
    
    def _build_bvh(self, components: List[Component]) -> None:
        """Build Bounding Volume Hierarchy."""
        # Simplified: just store component list
        # Full implementation would use scipy.spatial or custom BVH
        self._bvh = components
        self._bvh_dirty = False
    
    def _bvh_query(self, components: List[Component]) -> List[Tuple[Component, Component]]:
        """Query BVH for potential collision pairs."""
        pairs = []
        
        for i, comp_a in enumerate(components):
            bbox_a = self._get_bbox(comp_a)
            if not bbox_a:
                continue
            
            for comp_b in components[i+1:]:
                bbox_b = self._get_bbox(comp_b)
                if not bbox_b:
                    continue
                
                if bbox_a.intersects(bbox_b):
                    pairs.append((comp_a, comp_b))
        
        return pairs
    
    def _get_bbox(self, component: Component) -> Optional[BoundingBox]:
        """Get bounding box of component."""
        if hasattr(component, 'bounds'):
            return component.bounds
        if hasattr(component, 'position') and hasattr(component, 'dimensions'):
            pos = component.position
            dims = component.dimensions
            return BoundingBox(
                min_x=pos[0] - dims[0]/2, max_x=pos[0] + dims[0]/2,
                min_y=pos[1] - dims[1]/2, max_y=pos[1] + dims[1]/2,
                min_z=pos[2] - dims[2]/2, max_z=pos[2] + dims[2]/2,
            )
        return None
    
    def _check_pair(
        self,
        comp_a: Component,
        comp_b: Component,
        tolerance: float,
    ) -> Optional[Clash]:
        """Check for geometric intersection between components."""
        bbox_a = self._get_bbox(comp_a)
        bbox_b = self._get_bbox(comp_b)
        
        if not bbox_a or not bbox_b:
            return None
        
        # Calculate intersection box
        int_min_x = max(bbox_a.min_x, bbox_b.min_x)
        int_max_x = min(bbox_a.max_x, bbox_b.max_x)
        int_min_y = max(bbox_a.min_y, bbox_b.min_y)
        int_max_y = min(bbox_a.max_y, bbox_b.max_y)
        int_min_z = max(bbox_a.min_z, bbox_b.min_z)
        int_max_z = min(bbox_a.max_z, bbox_b.max_z)
        
        if int_max_x > int_min_x and int_max_y > int_min_y and int_max_z > int_min_z:
            volume = (int_max_x - int_min_x) * (int_max_y - int_min_y) * (int_max_z - int_min_z)
            
            if volume > tolerance ** 3:
                return Clash(
                    component_a=comp_a.id,
                    component_b=comp_b.id,
                    intersection_volume_m3=volume,
                    intersection_point=(
                        (int_min_x + int_max_x) / 2,
                        (int_min_y + int_max_y) / 2,
                        (int_min_z + int_max_z) / 2,
                    ),
                    severity="hard",
                )
        
        return None
    
    def _check_clearance(
        self,
        comp_a: Component,
        comp_b: Component,
        min_clearance: float,
    ) -> Optional[Clash]:
        """Check minimum clearance between components."""
        bbox_a = self._get_bbox(comp_a)
        bbox_b = self._get_bbox(comp_b)
        
        if not bbox_a or not bbox_b:
            return None
        
        # Calculate minimum distance between boxes
        dx = max(0, max(bbox_a.min_x - bbox_b.max_x, bbox_b.min_x - bbox_a.max_x))
        dy = max(0, max(bbox_a.min_y - bbox_b.max_y, bbox_b.min_y - bbox_a.max_y))
        dz = max(0, max(bbox_a.min_z - bbox_b.max_z, bbox_b.min_z - bbox_a.max_z))
        
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance < min_clearance and distance > 0:
            return Clash(
                component_a=comp_a.id,
                component_b=comp_b.id,
                intersection_volume_m3=0,
                intersection_point=(
                    (bbox_a.center[0] + bbox_b.center[0]) / 2,
                    (bbox_a.center[1] + bbox_b.center[1]) / 2,
                    (bbox_a.center[2] + bbox_b.center[2]) / 2,
                ),
                severity="clearance",
            )
        
        return None
```

---

## 7. Validation Framework

```python
# cortex/generative/validation/framework.py
# REUSES: magnet/validators/aggregator.py, taxonomy.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from enum import Enum
import logging

from ..artifact_graph import ArtifactGraph

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationFinding:
    """Single validation finding."""
    validator_id: str
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None  # Component or zone ID
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of running a validator."""
    validator_id: str
    passed: bool
    findings: List[ValidationFinding] = field(default_factory=list)
    execution_time_ms: float = 0.0
    
    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationSeverity.WARNING)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "findings": [f.to_dict() for f in self.findings],
            "execution_time_ms": self.execution_time_ms,
        }


class DomainValidator(ABC):
    """
    Abstract base class for domain validators.
    
    REUSES: Pattern from magnet/validators/taxonomy.py
    """
    
    @property
    @abstractmethod
    def validator_id(self) -> str:
        """Unique identifier for this validator."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
    
    @abstractmethod
    def validate(self, graph: ArtifactGraph, scope: str) -> ValidationResult:
        """
        Run validation on the artifact graph.
        
        Args:
            graph: The artifact graph to validate
            scope: Scope identifier (zone, system, or "full")
        
        Returns:
            ValidationResult with findings
        """
        pass


# =============================================================================
# CONCRETE VALIDATORS
# =============================================================================

class ClashValidator(DomainValidator):
    """Validates no geometric clashes exist."""
    
    @property
    def validator_id(self) -> str:
        return "clash_validator"
    
    @property
    def description(self) -> str:
        return "Checks for geometric intersections between components"
    
    def validate(self, graph: ArtifactGraph, scope: str) -> ValidationResult:
        from ..clash.detector import ClashDetector
        
        detector = ClashDetector(graph)
        clashes = detector.detect_clashes(scope=scope if scope != "full" else None)
        
        findings = []
        for clash in clashes:
            findings.append(ValidationFinding(
                validator_id=self.validator_id,
                severity=ValidationSeverity.ERROR if clash.severity == "hard" else ValidationSeverity.WARNING,
                message=f"Clash between {clash.component_a} and {clash.component_b}",
                location=clash.component_a,
                suggestion=f"Move components apart by at least {clash.intersection_volume_m3 ** (1/3):.3f}m",
            ))
        
        return ValidationResult(
            validator_id=self.validator_id,
            passed=len([f for f in findings if f.severity == ValidationSeverity.ERROR]) == 0,
            findings=findings,
        )


class ClearanceValidator(DomainValidator):
    """Validates minimum clearances are maintained."""
    
    def __init__(self, min_clearance_m: float = 0.05):
        self._min_clearance = min_clearance_m
    
    @property
    def validator_id(self) -> str:
        return "clearance_validator"
    
    @property
    def description(self) -> str:
        return f"Checks minimum clearance of {self._min_clearance}m between components"
    
    def validate(self, graph: ArtifactGraph, scope: str) -> ValidationResult:
        from ..clash.detector import ClashDetector
        
        detector = ClashDetector(graph)
        clashes = detector.detect_clashes(
            scope=scope if scope != "full" else None,
            check_clearances=True,
            min_clearance_m=self._min_clearance,
        )
        
        clearance_clashes = [c for c in clashes if c.severity == "clearance"]
        
        findings = []
        for clash in clearance_clashes:
            findings.append(ValidationFinding(
                validator_id=self.validator_id,
                severity=ValidationSeverity.WARNING,
                message=f"Clearance violation between {clash.component_a} and {clash.component_b}",
                location=clash.component_a,
                suggestion=f"Increase clearance to at least {self._min_clearance}m",
            ))
        
        return ValidationResult(
            validator_id=self.validator_id,
            passed=True,  # Clearance is warning-only
            findings=findings,
        )


class AccessibilityValidator(DomainValidator):
    """Validates components are accessible for service."""
    
    @property
    def validator_id(self) -> str:
        return "accessibility_validator"
    
    @property
    def description(self) -> str:
        return "Checks that serviceable components have adequate access"
    
    def validate(self, graph: ArtifactGraph, scope: str) -> ValidationResult:
        findings = []
        
        for component in graph.list_components():
            if not hasattr(component, 'requires_access'):
                continue
            
            if component.requires_access:
                # Check for access path
                has_access = self._check_access(graph, component)
                
                if not has_access:
                    findings.append(ValidationFinding(
                        validator_id=self.validator_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"Component {component.id} may not be accessible for service",
                        location=component.id,
                        suggestion="Ensure clear access path exists",
                    ))
        
        return ValidationResult(
            validator_id=self.validator_id,
            passed=True,
            findings=findings,
        )
    
    def _check_access(self, graph: ArtifactGraph, component: Any) -> bool:
        """Check if component has access."""
        # Simplified: always return True
        # Full implementation would check for clear path to access point
        return True


# =============================================================================
# VALIDATION ORCHESTRATOR
# =============================================================================

class ValidationOrchestrator:
    """
    Orchestrates validation across all validators.
    
    REUSES: magnet/validators/aggregator.py pattern
    """
    
    def __init__(self):
        self._validators: Dict[str, DomainValidator] = {}
        self._order: List[str] = []
    
    def register(self, validator: DomainValidator, order: int = 100) -> None:
        """Register a validator."""
        self._validators[validator.validator_id] = validator
        self._order.append(validator.validator_id)
        self._order.sort(key=lambda x: order)
    
    def validate(
        self,
        graph: ArtifactGraph,
        scope: str = "full",
        stop_on_error: bool = False,
    ) -> Dict[str, ValidationResult]:
        """
        Run all validators.
        
        Args:
            graph: Artifact graph to validate
            scope: Scope for validation
            stop_on_error: Whether to stop on first error
        
        Returns:
            Dict of validator_id -> ValidationResult
        """
        results = {}
        
        for validator_id in self._order:
            validator = self._validators[validator_id]
            
            try:
                import time
                start = time.time()
                result = validator.validate(graph, scope)
                result.execution_time_ms = (time.time() - start) * 1000
                results[validator_id] = result
                
                if stop_on_error and not result.passed:
                    break
                    
            except Exception as e:
                logger.error(f"Validator {validator_id} failed: {e}")
                results[validator_id] = ValidationResult(
                    validator_id=validator_id,
                    passed=False,
                    findings=[ValidationFinding(
                        validator_id=validator_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"Validator error: {e}",
                    )],
                )
        
        return results
    
    def get_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results."""
        total_errors = sum(r.error_count for r in results.values())
        total_warnings = sum(r.warning_count for r in results.values())
        all_passed = all(r.passed for r in results.values())
        
        return {
            "all_passed": all_passed,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "validators_run": len(results),
            "validators_passed": sum(1 for r in results.values() if r.passed),
            "validators_failed": sum(1 for r in results.values() if not r.passed),
        }


def create_default_orchestrator() -> ValidationOrchestrator:
    """Create orchestrator with default validators."""
    orchestrator = ValidationOrchestrator()
    orchestrator.register(ClashValidator(), order=10)
    orchestrator.register(ClearanceValidator(), order=20)
    orchestrator.register(AccessibilityValidator(), order=30)
    return orchestrator
```

---

## 8. Generative Agent Tools

```python
# cortex/generative/tools/definitions.py

from typing import Dict, List, Any


GENERATIVE_DESIGN_TOOLS = [
    # =========================================================================
    # LEVEL 0-1: MISSION & SYSTEMS
    # =========================================================================
    {
        "name": "request_space_allocation",
        "description": "Allocate zones within the hull envelope for systems",
        "input_schema": {
            "type": "object",
            "properties": {
                "zones": {
                    "type": "object",
                    "description": "Zone type to minimum volume (m³) mapping",
                    "additionalProperties": {"type": "number"},
                },
                "adjacency_required": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                    "description": "Pairs of zones that must be adjacent",
                },
                "adjacency_forbidden": {
                    "type": "array", 
                    "items": {"type": "array", "items": {"type": "string"}},
                    "description": "Pairs of zones that must NOT be adjacent",
                },
                "priorities": {
                    "type": "object",
                    "description": "Zone priorities (higher = more important)",
                    "additionalProperties": {"type": "integer"},
                },
            },
            "required": ["zones"],
        },
    },
    {
        "name": "select_system_pattern",
        "description": "Select a system pattern from the library",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["fuel", "electrical", "plumbing", "hvac", "propulsion"],
                },
                "conditions": {
                    "type": "object",
                    "description": "Conditions for pattern selection (e.g., fuel_type, engine_count)",
                },
            },
            "required": ["domain"],
        },
    },
    
    # =========================================================================
    # LEVEL 2: COMPONENTS
    # =========================================================================
    {
        "name": "request_placement",
        "description": "Request placement of a component in a zone",
        "input_schema": {
            "type": "object",
            "properties": {
                "component_type": {"type": "string"},
                "component_id": {"type": "string"},
                "zone": {"type": "string"},
                "dimensions": {
                    "type": "object",
                    "properties": {
                        "length_m": {"type": "number"},
                        "width_m": {"type": "number"},
                        "height_m": {"type": "number"},
                    },
                },
                "constraints": {
                    "type": "object",
                    "properties": {
                        "min_clearance_m": {"type": "number"},
                        "access_direction": {"type": "string"},
                        "structural_support": {"type": "boolean"},
                        "weight_limit_kg": {"type": "number"},
                    },
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "near": {"type": "array", "items": {"type": "string"}},
                        "away_from": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "required": ["component_type", "zone"],
        },
    },
    {
        "name": "commit_placement",
        "description": "Commit a proposed placement to the design",
        "input_schema": {
            "type": "object",
            "properties": {
                "component_id": {"type": "string"},
                "accept": {"type": "boolean"},
            },
            "required": ["component_id", "accept"],
        },
    },
    
    # =========================================================================
    # LEVEL 3: ROUTING
    # =========================================================================
    {
        "name": "request_routing",
        "description": "Request routing between two components",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_component": {"type": "string"},
                "from_port": {"type": "string"},
                "to_component": {"type": "string"},
                "to_port": {"type": "string"},
                "system_type": {
                    "type": "string",
                    "enum": ["fuel_supply", "fuel_return", "fuel_vent", "freshwater", "blackwater", "electrical_dc", "electrical_ac", "exhaust"],
                },
                "constraints": {
                    "type": "object",
                    "properties": {
                        "min_bend_radius_m": {"type": "number"},
                        "max_length_m": {"type": "number"},
                        "slope_direction": {"type": "string"},
                        "avoid_zones": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "accessibility": {"type": "string", "enum": ["hidden", "serviceable", "visible"]},
                        "follow_structure": {"type": "boolean"},
                        "minimize_fittings": {"type": "boolean"},
                    },
                },
            },
            "required": ["from_component", "to_component", "system_type"],
        },
    },
    {
        "name": "commit_route",
        "description": "Commit a proposed route to the design",
        "input_schema": {
            "type": "object",
            "properties": {
                "route_id": {"type": "string"},
                "accept": {"type": "boolean"},
            },
            "required": ["route_id", "accept"],
        },
    },
    
    # =========================================================================
    # VALIDATION & VIEWING
    # =========================================================================
    {
        "name": "request_clash_check",
        "description": "Check for clashes in a scope",
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "Zone ID or 'full' for entire design",
                },
            },
        },
    },
    {
        "name": "request_validation",
        "description": "Run full validation on a system or scope",
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string"},
                "validators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific validators to run, or empty for all",
                },
            },
        },
    },
    {
        "name": "request_view",
        "description": "Request an annotated view of the design",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {"type": "string", "description": "Component or zone ID to focus on"},
                "scope": {"type": "string", "enum": ["local_1m", "local_2m", "local_5m", "zone", "system", "full"]},
                "view_angle": {"type": "string", "enum": ["isometric", "top", "front", "side", "section"]},
                "annotations": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["labels", "dimensions", "clearances", "routes"]},
                },
            },
            "required": ["focus", "scope"],
        },
    },
    
    # =========================================================================
    # BACKTRACKING
    # =========================================================================
    {
        "name": "reject_proposal",
        "description": "Reject a proposed placement or route",
        "input_schema": {
            "type": "object",
            "properties": {
                "proposal_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["proposal_id", "reason"],
        },
    },
    {
        "name": "backtrack_to_level",
        "description": "Signal that backtracking is needed",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_level": {
                    "type": "string",
                    "enum": ["mission", "systems", "components", "routing"],
                },
                "reason": {"type": "string"},
            },
            "required": ["target_level", "reason"],
        },
    },
]
```

---

## 9. Agent System Prompts

```python
# cortex/generative/prompts/level_prompts.py

MISSION_AGENT_PROMPT = """You are a naval architect designing vessel systems at the MISSION level.

YOUR TASK:
- Interpret user requirements into space allocations
- Define system requirements and budgets
- Ensure feasibility before descending to SYSTEMS level

INPUTS YOU RECEIVE:
- User requirements (mission statement, vessel specs)
- Hull envelope (available space)

OUTPUTS YOU PRODUCE:
- Space allocation (zones with volumes)
- System requirements per zone
- Weight budget per system
- Power budget

TOOLS AVAILABLE:
- request_space_allocation: Allocate zones within hull
- request_view: Visualize current allocations

VALIDATION REQUIREMENTS:
Before completing this level:
1. Total allocated volume <= hull volume
2. All required systems have zones
3. Adjacency constraints satisfied

When all validations pass, your outputs will be passed to the SYSTEMS level.
If constraints cannot be satisfied, explain why and suggest requirement changes.
"""

SYSTEMS_AGENT_PROMPT = """You are a systems engineer at the SYSTEMS level.

YOUR TASK:
- Select appropriate patterns for each required system
- Define component lists and specifications
- Establish interface points between systems

INPUTS YOU RECEIVE:
- Space allocation from MISSION level
- System requirements and budgets

OUTPUTS YOU PRODUCE:
- System patterns selected
- Component lists with specs
- Interface points between systems
- Routing requirements

TOOLS AVAILABLE:
- select_system_pattern: Choose pattern from library
- request_view: Visualize zones and patterns

PATTERN SELECTION RULES:
1. Match pattern to fuel type, engine configuration
2. Verify pattern fits in allocated zone
3. Check component list against budget

When systems are defined, outputs pass to COMPONENTS level.
"""

COMPONENTS_AGENT_PROMPT = """You are placing components at the COMPONENTS level.

YOUR TASK:
- Place each component from system patterns
- Ensure clearances and access requirements
- Connect ports for routing

INPUTS YOU RECEIVE:
- System specs from SYSTEMS level
- Component lists
- Zone assignments

OUTPUTS YOU PRODUCE:
- Placed components with positions
- Clearance reports
- Connection points for routing

TOOLS AVAILABLE:
- request_placement: Find valid position for component
- commit_placement: Accept a placement
- request_clash_check: Check for collisions
- request_view: Visualize placements

PLACEMENT RULES:
1. Place largest/heaviest components first
2. Maintain minimum clearances
3. Ensure access for serviceable components
4. Respect structural constraints

When all components placed and validated, proceed to ROUTING.
"""

ROUTING_AGENT_PROMPT = """You are routing connections at the ROUTING level.

YOUR TASK:
- Route all connections between components
- Respect system-specific routing rules
- Generate fittings and supports

INPUTS YOU RECEIVE:
- Placed components from COMPONENTS level
- Connection requirements from patterns
- Routing constraints per system type

OUTPUTS YOU PRODUCE:
- Routes with path geometry
- Fitting locations
- Support locations
- Penetration requirements

TOOLS AVAILABLE:
- request_routing: Compute route between ports
- commit_route: Accept a route
- request_clash_check: Verify no collisions
- request_validation: Run system validation
- request_view: Visualize routes

ROUTING RULES:
1. Route fuel and water with proper slopes
2. Separate fuel from electrical
3. Maintain minimum bend radii
4. Add supports at specified intervals

When all routes validated, proceed to DETAILS.
"""

DETAILS_AGENT_PROMPT = """You are finalizing details at the DETAILS level.

YOUR TASK:
- Add supports and hangers
- Generate labels
- Define access panels
- Create installation sequence

INPUTS YOU RECEIVE:
- Routes from ROUTING level
- Support locations
- Labeling requirements

OUTPUTS YOU PRODUCE:
- Support specifications
- Labels and markings
- Access panel locations
- Installation sequence

TOOLS AVAILABLE:
- request_validation: Final validation
- request_view: Visualize complete design

When complete, signal DESIGN COMPLETE.
"""
```

---

## 10. Testing

```python
# tests/test_generative_design.py

import pytest
from cortex.generative.orchestrator import HierarchicalDesignAgent, Requirements
from cortex.generative.levels import DESIGN_LEVELS
from cortex.generative.patterns.registry import PATTERN_REGISTRY
from cortex.generative.patterns.builtin import register_builtin_patterns
from cortex.artifact_graph import ArtifactGraph
from cortex.kernel import Kernel


@pytest.fixture
def graph():
    """Create test artifact graph with hull envelope."""
    g = ArtifactGraph()
    # Add hull envelope (20m x 6m x 3m)
    g.set_bounds(min_x=0, max_x=20, min_y=-3, max_y=3, min_z=-1.5, max_z=1.5)
    return g


@pytest.fixture
def kernel(graph):
    """Create test kernel."""
    return Kernel(graph)


class TestPatternRegistry:
    """Test pattern registry and instantiation."""
    
    def test_builtin_patterns_registered(self):
        register_builtin_patterns()
        
        fuel_patterns = PATTERN_REGISTRY.list_by_domain("fuel")
        assert len(fuel_patterns) >= 2
        
        electrical_patterns = PATTERN_REGISTRY.list_by_domain("electrical")
        assert len(electrical_patterns) >= 1
    
    def test_pattern_selection(self):
        register_builtin_patterns()
        
        # Select diesel twin pattern
        patterns = PATTERN_REGISTRY.find_applicable(
            domain="fuel",
            conditions={"fuel_type": "diesel", "engine_count": 2},
        )
        
        assert len(patterns) >= 1
        assert any(p.id == "fuel_twin_diesel" for p in patterns)


class TestSpaceAllocation:
    """Test space allocation."""
    
    def test_basic_allocation(self, graph):
        from cortex.generative.space.allocator import SpaceAllocator
        from cortex.generative.space.zones import SpaceRequirements, ZoneType
        
        allocator = SpaceAllocator(graph.get_bounds())
        
        requirements = SpaceRequirements(
            zones={
                ZoneType.ENGINE_ROOM: 30.0,
                ZoneType.FUEL: 20.0,
                ZoneType.ACCOMMODATION: 50.0,
            },
            adjacency_required=[
                (ZoneType.ENGINE_ROOM, ZoneType.FUEL),
            ],
        )
        
        result = allocator.allocate(requirements)
        
        assert len(result.zones) == 3
        assert result.satisfaction_score > 0.5


class TestComponentPlacement:
    """Test component placement."""
    
    def test_placement_solver(self, graph):
        from cortex.generative.placement.solver import (
            PlacementSolver, ComponentTemplate, PlacementConstraint
        )
        from cortex.generative.space.zones import Zone, ZoneType, BoundingBox
        
        solver = PlacementSolver(graph)
        
        zone = Zone(
            id="test_zone",
            name="Test Zone",
            zone_type=ZoneType.ENGINE_ROOM,
            bounds=BoundingBox(
                min_x=0, max_x=5,
                min_y=-2, max_y=2,
                min_z=-1, max_z=1,
            ),
        )
        
        component = ComponentTemplate(
            component_type="fuel_tank",
            dimensions=(1.0, 0.5, 0.5),
        )
        
        placement = solver.solve(
            component=component,
            zone=zone,
            constraints=[
                PlacementConstraint(name="clearance", type="clearance", value=0.1),
            ],
        )
        
        assert placement is not None
        assert zone.bounds.contains(placement.position)


class TestRoutingEngine:
    """Test routing engine."""
    
    def test_basic_routing(self, graph):
        from cortex.generative.routing.engine import RoutingEngine, RoutingRequest
        from cortex.generative.routing.constraints import RoutingConstraints
        
        # Add test components
        graph.add_component_at("tank", (2, 0, 0))
        graph.add_component_at("filter", (8, 0, 0))
        
        engine = RoutingEngine(graph)
        
        result = engine.route(RoutingRequest(
            from_component="tank",
            from_port="outlet",
            to_component="filter",
            to_port="inlet",
            system_type="fuel_supply",
            constraints=RoutingConstraints(
                system_type="fuel_supply",
                min_bend_radius_m=0.1,
            ),
        ))
        
        assert result.success
        assert result.route is not None
        assert result.route.total_length_m > 0


class TestClashDetection:
    """Test clash detection."""
    
    def test_detect_clash(self, graph):
        from cortex.generative.clash.detector import ClashDetector
        
        # Add overlapping components
        graph.add_component_at("comp_a", (5, 0, 0), dimensions=(1, 1, 1))
        graph.add_component_at("comp_b", (5.3, 0, 0), dimensions=(1, 1, 1))
        
        detector = ClashDetector(graph)
        clashes = detector.detect_clashes()
        
        assert len(clashes) >= 1
        assert clashes[0].severity == "hard"


class TestValidation:
    """Test validation framework."""
    
    def test_validation_orchestrator(self, graph):
        from cortex.generative.validation.framework import create_default_orchestrator
        
        orchestrator = create_default_orchestrator()
        results = orchestrator.validate(graph)
        
        assert "clash_validator" in results
        assert "clearance_validator" in results


# Performance benchmarks
class TestPerformance:
    """Performance benchmarks."""
    
    def test_routing_performance(self, graph, benchmark):
        """Routing should complete in < 1s for typical distances."""
        from cortex.generative.routing.engine import RoutingEngine, RoutingRequest
        from cortex.generative.routing.constraints import RoutingConstraints
        
        graph.add_component_at("start", (0, 0, 0))
        graph.add_component_at("end", (15, 0, 0))
        
        engine = RoutingEngine(graph, resolution_m=0.1)
        
        def route():
            return engine.route(RoutingRequest(
                from_component="start",
                from_port="default",
                to_component="end", 
                to_port="default",
                system_type="fuel_supply",
                constraints=RoutingConstraints(system_type="fuel_supply"),
            ))
        
        result = benchmark(route)
        assert result.success
    
    def test_clash_detection_performance(self, graph, benchmark):
        """Clash detection should complete in < 500ms for 100 components."""
        from cortex.generative.clash.detector import ClashDetector
        import random
        
        # Add 100 random components
        for i in range(100):
            graph.add_component_at(
                f"comp_{i}",
                (random.uniform(0, 20), random.uniform(-3, 3), random.uniform(-1.5, 1.5)),
                dimensions=(0.3, 0.3, 0.3),
            )
        
        detector = ClashDetector(graph)
        
        result = benchmark(detector.detect_clashes)
        # Result is list of clashes
```

---

## 11. Migration from Current MAGNET

### 11.1 Reuse Map

| CORTEX Component | MAGNET Source | Reuse Level |
|------------------|---------------|-------------|
| Pattern Registry | `magnet/routing/schema/system_topology.py` | Extend |
| Space Allocator | `magnet/routing/router/zone_manager.py` | Adapt |
| Routing Engine | `magnet/routing/router/path_optimizer.py` | Wrap |
| Clash Detection | New | Build |
| Validation Framework | `magnet/validators/aggregator.py` | Extend |
| Agent Orchestrator | `magnet/agents/geometry_proposer.py` | Adapt |

### 11.2 Integration Steps

1. **Week 1**: Create `cortex/generative/` package structure
2. **Week 2**: Port pattern schema and registry
3. **Week 3**: Implement space allocation
4. **Week 4**: Port routing engine
5. **Week 5**: Implement clash detection
6. **Week 6**: Integrate validation framework
7. **Week 7**: Build agent orchestrator
8. **Week 8**: Integration testing

---

*End of CORTEX Generative Design Implementation Specification*
