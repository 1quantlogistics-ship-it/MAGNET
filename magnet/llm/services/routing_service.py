"""
magnet/llm/services/routing_service.py - Routing Service

High-level service for route selection, conflict resolution, and optimization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..prompts.schemas import (
    RouteSelectionResponse,
    ConflictResolutionResponse,
    ConflictResolutionStrategy,
    RouteOptimizationResponse,
    OptimizationSuggestion,
)
from ..prompts.routing import (
    ROUTING_SYSTEM_PROMPT,
    CONFLICT_RESOLUTION_SYSTEM_PROMPT,
    create_route_selection_prompt,
    create_conflict_resolution_prompt,
    create_optimization_prompt,
    get_fallback_route_selection,
    get_fallback_conflict_resolution,
    get_fallback_optimization,
    SYSTEM_PRIORITIES,
)

if TYPE_CHECKING:
    from ..protocol import LLMProviderProtocol

logger = logging.getLogger("llm.services.routing")


class RoutingService:
    """
    Service for ship systems routing decisions.

    Features:
    - LLM-powered route selection with trade-off analysis
    - Intelligent conflict resolution
    - Routing optimization suggestions
    - Automatic fallback to deterministic algorithms
    """

    def __init__(
        self,
        llm: Optional["LLMProviderProtocol"] = None,
        use_fallback: bool = True,
    ):
        """
        Initialize the routing service.

        Args:
            llm: LLM provider instance (optional)
            use_fallback: Whether to use fallback when LLM unavailable
        """
        self.llm = llm
        self.use_fallback = use_fallback

    async def select_route(
        self,
        system_type: str,
        route_options: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RouteSelectionResponse:
        """
        Select the best route from available options.

        Args:
            system_type: Type of system being routed
            route_options: List of route options with metrics
            constraints: Routing constraints

        Returns:
            RouteSelectionResponse with selected route and reasoning
        """
        if not route_options:
            return RouteSelectionResponse(
                selected_index=0,
                reasoning="No route options available",
                confidence=0.0,
            )

        # Use deterministic for single option
        if len(route_options) == 1:
            return RouteSelectionResponse(
                selected_index=0,
                reasoning="Only one route option available",
                confidence=1.0,
            )

        if self.llm is None:
            logger.debug("No LLM available, using fallback route selection")
            return self._fallback_route_selection(route_options)

        prompt = create_route_selection_prompt(
            system_type=system_type,
            route_options=route_options,
            constraints=constraints,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=RouteSelectionResponse,
                system_prompt=ROUTING_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM route selection failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_route_selection(route_options)
            raise

    async def resolve_conflict(
        self,
        system_a: str,
        system_b: str,
        conflict_type: str,
        affected_spaces: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConflictResolutionResponse:
        """
        Resolve a routing conflict between two systems.

        Args:
            system_a: First system in conflict
            system_b: Second system in conflict
            conflict_type: Type of conflict (SPACE_CONFLICT, CLEARANCE_VIOLATION, etc.)
            affected_spaces: Spaces where conflict occurs
            context: Additional context

        Returns:
            ConflictResolutionResponse with strategy and parameters
        """
        affected_spaces = affected_spaces or []

        if self.llm is None:
            logger.debug("No LLM available, using fallback conflict resolution")
            return self._fallback_conflict_resolution(system_a, system_b, conflict_type)

        prompt = create_conflict_resolution_prompt(
            system_a=system_a,
            system_b=system_b,
            conflict_type=conflict_type,
            affected_spaces=affected_spaces,
            context=context,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=ConflictResolutionResponse,
                system_prompt=CONFLICT_RESOLUTION_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM conflict resolution failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_conflict_resolution(system_a, system_b, conflict_type)
            raise

    async def suggest_optimizations(
        self,
        current_routing: Dict[str, Any],
        optimization_goals: Optional[List[str]] = None,
    ) -> RouteOptimizationResponse:
        """
        Generate routing optimization suggestions.

        Args:
            current_routing: Current routing state
            optimization_goals: Specific goals for optimization

        Returns:
            RouteOptimizationResponse with suggestions
        """
        optimization_goals = optimization_goals or [
            "Minimize total route length",
            "Reduce conflicts",
            "Improve maintenance access",
        ]

        if self.llm is None:
            logger.debug("No LLM available, using fallback optimization")
            return self._fallback_optimization()

        prompt = create_optimization_prompt(
            current_routing=current_routing,
            optimization_goals=optimization_goals,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=RouteOptimizationResponse,
                system_prompt=ROUTING_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM optimization failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_optimization()
            raise

    async def resolve_batch_conflicts(
        self,
        conflicts: List[Dict[str, Any]],
    ) -> List[ConflictResolutionResponse]:
        """
        Resolve multiple conflicts in batch.

        Args:
            conflicts: List of conflict descriptions

        Returns:
            List of resolution responses
        """
        if not conflicts:
            return []

        # Process conflicts sequentially to consider interdependencies
        resolutions = []
        for conflict in conflicts:
            resolution = await self.resolve_conflict(
                system_a=conflict.get("system_a", "unknown"),
                system_b=conflict.get("system_b", "unknown"),
                conflict_type=conflict.get("conflict_type", "SPACE_CONFLICT"),
                affected_spaces=conflict.get("affected_spaces", []),
                context=conflict.get("context"),
            )
            resolutions.append(resolution)

        return resolutions

    def get_system_priority(self, system_type: str) -> int:
        """
        Get the priority of a system type.

        Args:
            system_type: System type name

        Returns:
            Priority (1=highest, 10=lowest)
        """
        return SYSTEM_PRIORITIES.get(system_type, 5)

    def compare_system_priorities(self, system_a: str, system_b: str) -> int:
        """
        Compare priorities of two systems.

        Args:
            system_a: First system
            system_b: Second system

        Returns:
            -1 if a higher priority, 0 if equal, 1 if b higher priority
        """
        priority_a = self.get_system_priority(system_a)
        priority_b = self.get_system_priority(system_b)

        if priority_a < priority_b:
            return -1
        elif priority_a > priority_b:
            return 1
        return 0

    # =========================================================================
    # Fallback Methods
    # =========================================================================

    def _fallback_route_selection(
        self,
        route_options: List[Dict[str, Any]],
    ) -> RouteSelectionResponse:
        """Use deterministic route selection algorithm."""
        data = get_fallback_route_selection(route_options)
        return RouteSelectionResponse(
            selected_index=data["selected_index"],
            reasoning=data["reasoning"],
            confidence=data["confidence"],
            alternatives_considered=data.get("alternatives_considered", []),
            trade_offs=data.get("trade_offs", []),
        )

    def _fallback_conflict_resolution(
        self,
        system_a: str,
        system_b: str,
        conflict_type: str,
    ) -> ConflictResolutionResponse:
        """Use priority-based conflict resolution."""
        data = get_fallback_conflict_resolution(system_a, system_b, conflict_type)
        return ConflictResolutionResponse(
            strategy=ConflictResolutionStrategy(data["strategy"]),
            parameters=data.get("parameters", {}),
            reasoning=data["reasoning"],
            affected_systems=data.get("affected_systems", [system_a, system_b]),
            estimated_rework=data.get("estimated_rework"),
        )

    def _fallback_optimization(self) -> RouteOptimizationResponse:
        """Return generic optimization suggestions."""
        data = get_fallback_optimization()
        suggestions = [
            OptimizationSuggestion(
                description=s["description"],
                benefit=s["benefit"],
                implementation=s["implementation"],
                priority=s["priority"],
            )
            for s in data.get("suggestions", [])
        ]
        return RouteOptimizationResponse(
            suggestions=suggestions,
            overall_assessment=data.get("overall_assessment", ""),
            potential_savings=data.get("potential_savings"),
        )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def select_best_route_for_system(
        self,
        system_type: str,
        routes: List[Dict[str, Any]],
    ) -> int:
        """
        Simple interface to get the best route index.

        Args:
            system_type: Type of system
            routes: Route options

        Returns:
            Index of the best route
        """
        response = await self.select_route(system_type, routes)
        return response.selected_index

    async def should_reroute_system(
        self,
        system_type: str,
        blocking_system: str,
    ) -> bool:
        """
        Determine if a system should be rerouted around another.

        Args:
            system_type: System to potentially reroute
            blocking_system: System causing the block

        Returns:
            True if system_type should be rerouted
        """
        resolution = await self.resolve_conflict(
            system_a=system_type,
            system_b=blocking_system,
            conflict_type="SPACE_CONFLICT",
        )

        return resolution.strategy == ConflictResolutionStrategy.REROUTE_A

    async def get_routing_summary(
        self,
        routing_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a summary of routing state with recommendations.

        Args:
            routing_state: Current routing information

        Returns:
            Summary with stats and recommendations
        """
        # Extract routing metrics
        systems = routing_state.get("systems", {})
        conflicts = routing_state.get("conflicts", [])

        total_length = sum(
            s.get("length_m", 0) for s in systems.values()
        )
        total_bends = sum(
            s.get("bend_count", 0) for s in systems.values()
        )

        # Get optimization suggestions
        optimizations = await self.suggest_optimizations(
            current_routing=systems,
            optimization_goals=["Minimize length", "Reduce conflicts"],
        )

        return {
            "total_systems": len(systems),
            "total_length_m": total_length,
            "total_bends": total_bends,
            "conflict_count": len(conflicts),
            "assessment": optimizations.overall_assessment,
            "top_suggestions": [
                s.description for s in optimizations.suggestions[:3]
            ],
            "potential_savings": optimizations.potential_savings,
        }
