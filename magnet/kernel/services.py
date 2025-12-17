"""
magnet/kernel/services.py - Kernel Services Factory

Single source of truth for Intent→Action protocol services.
Addresses audit P0-3: Lazy resolution risks duplicating services.

Usage:
    from magnet.kernel.services import get_intent_protocol_services
    validator, executor = get_intent_protocol_services(state_manager)
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.kernel.action_validator import ActionPlanValidator
    from magnet.kernel.action_executor import ActionExecutor


def get_intent_protocol_services(
    state_manager: "StateManager",
) -> Tuple["ActionPlanValidator", "ActionExecutor"]:
    """
    Get the Intent→Action protocol services.

    Single factory for creating properly configured validator and executor.
    Ensures consistent EventDispatcher sharing and design_id resolution.

    Args:
        state_manager: The StateManager instance to use for state access.

    Returns:
        Tuple of (ActionPlanValidator, ActionExecutor)

    Example:
        validator, executor = get_intent_protocol_services(self.state)
        validation_result = validator.validate(plan, self.state)
        exec_result = executor.execute(validation_result.approved, plan)
    """
    from magnet.kernel.action_validator import ActionPlanValidator
    from magnet.kernel.action_executor import ActionExecutor
    from magnet.kernel.event_dispatcher import EventDispatcher

    # Resolve design_id from state
    design_id = state_manager.get("metadata.design_id") if state_manager else "default"
    if design_id is None:
        design_id = "default"

    # Create shared dispatcher
    dispatcher = EventDispatcher(design_id=design_id)

    # Create services
    validator = ActionPlanValidator()
    executor = ActionExecutor(state_manager, dispatcher)

    return validator, executor
