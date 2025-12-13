"""
Validator Registry - Maps definitions to implementations and manages instances.

BRAVO OWNS THIS FILE.

Guardrail #3: Explicit lifecycle control - reset() must be called before initialize_defaults()
Guardrail #4: Fail hard if required validators lack implementations
"""
from typing import Dict, Optional, Type, Set, TYPE_CHECKING
import logging

from .taxonomy import ValidatorInterface, ValidatorDefinition
from .builtin import get_validator_by_id, get_all_validators

if TYPE_CHECKING:
    from ..kernel.conductor import Conductor

logger = logging.getLogger(__name__)


class ValidatorRegistry:
    """
    Central registry for validator implementations.

    IMPORTANT: This uses class-level state. Call reset() before initialize_defaults()
    in each process/app lifecycle to prevent state leakage.
    """

    _validator_classes: Dict[str, Type[ValidatorInterface]] = {}
    _instances: Dict[str, ValidatorInterface] = {}
    _initialized: bool = False
    _required_validators: Set[str] = set()  # Validators that MUST have implementations

    @classmethod
    def reset(cls) -> None:
        """
        Reset registry state. MUST be called before initialize_defaults() in each process.

        Guardrail #3: Prevents state leakage across workers/tests/reloads.
        """
        cls._validator_classes.clear()
        cls._instances.clear()
        cls._initialized = False
        cls._required_validators.clear()
        logger.debug("ValidatorRegistry reset")

    @classmethod
    def register_class(cls, validator_id: str, validator_class: Type[ValidatorInterface]) -> None:
        """Register a validator implementation class."""
        cls._validator_classes[validator_id] = validator_class

    @classmethod
    def mark_required(cls, validator_id: str) -> None:
        """Mark a validator as required (must have implementation)."""
        cls._required_validators.add(validator_id)

    @classmethod
    def get_instance(cls, validator_id: str) -> Optional[ValidatorInterface]:
        """Get validator instance by ID (lazy instantiation)."""
        if validator_id not in cls._instances:
            cls._instantiate(validator_id)
        return cls._instances.get(validator_id)

    @classmethod
    def get_all_instances(cls) -> Dict[str, ValidatorInterface]:
        """Get all instantiated validators."""
        return cls._instances.copy()

    @classmethod
    def _instantiate(cls, validator_id: str) -> None:
        """Create validator instance from registered class."""
        if validator_id not in cls._validator_classes:
            return

        definition = get_validator_by_id(validator_id)
        if not definition:
            logger.warning(f"No definition for: {validator_id}")
            return

        try:
            validator_class = cls._validator_classes[validator_id]
            instance = validator_class(definition)
            cls._instances[validator_id] = instance
            logger.debug(f"Instantiated: {validator_id}")
        except Exception as e:
            logger.error(f"Failed to instantiate {validator_id}: {e}")

    @classmethod
    def validate_required_implementations(cls) -> None:
        """
        Verify all required validators have BOTH implementations AND instances.

        Guardrail #4: Fail hard if required validators missing.
        Raises RuntimeError if any required validator lacks implementation or instance.

        IMPORTANT: Call instantiate_all() BEFORE this method to ensure instances exist.
        """
        # First: Check class registrations
        missing_classes = []
        for validator_id in cls._required_validators:
            if validator_id not in cls._validator_classes:
                missing_classes.append(validator_id)

        if missing_classes:
            raise RuntimeError(
                f"Required validators missing class implementations: {missing_classes}"
            )

        # Second: Check instances (class registered but instantiation failed)
        missing_instances = []
        for validator_id in cls._required_validators:
            if validator_id not in cls._instances:
                missing_instances.append(validator_id)

        if missing_instances:
            raise RuntimeError(
                f"Required validators failed to instantiate: {missing_instances}"
            )

        logger.info(f"✓ All {len(cls._required_validators)} required validators verified (class + instance)")

    @classmethod
    def initialize_defaults(cls) -> None:
        """Register all available validator implementations."""
        if cls._initialized:
            return

        # Physics validators (REQUIRED for hull phase)
        try:
            from magnet.physics.validators import HydrostaticsValidator, ResistanceValidator
            cls.register_class("physics/hydrostatics", HydrostaticsValidator)
            cls.register_class("physics/resistance", ResistanceValidator)
            cls.mark_required("physics/hydrostatics")  # Required for any hull analysis
        except ImportError as e:
            logger.warning(f"Physics validators not available: {e}")

        # Stability validators (REQUIRED for stability phase)
        try:
            from magnet.stability.validators import (
                IntactGMValidator, GZCurveValidator,
                DamageStabilityValidator, WeatherCriterionValidator
            )
            cls.register_class("stability/intact_gm", IntactGMValidator)
            cls.register_class("stability/gz_curve", GZCurveValidator)
            cls.register_class("stability/damage", DamageStabilityValidator)
            cls.register_class("stability/weather_criterion", WeatherCriterionValidator)
            cls.mark_required("stability/intact_gm")  # Required for stability
        except ImportError as e:
            logger.warning(f"Stability validators not available: {e}")

        # Weight validator (REQUIRED for weight phase)
        try:
            from magnet.weight.validators import WeightEstimationValidator
            cls.register_class("weight/estimation", WeightEstimationValidator)
            cls.mark_required("weight/estimation")
        except ImportError as e:
            logger.warning(f"Weight validator not available: {e}")

        # Compliance validator (REQUIRED - gate condition)
        try:
            from magnet.compliance.validators import ComplianceValidator
            cls.register_class("compliance/regulatory", ComplianceValidator)
            cls.mark_required("compliance/regulatory")  # Gate validator
        except ImportError as e:
            logger.warning(f"Compliance validator not available: {e}")

        # Arrangement validator
        try:
            from magnet.arrangement.validators import ArrangementValidator
            cls.register_class("arrangement/generator", ArrangementValidator)
        except ImportError as e:
            logger.warning(f"Arrangement validator not available: {e}")

        # Loading validator
        try:
            from magnet.loading.validators import LoadingComputerValidator
            cls.register_class("loading/computer", LoadingComputerValidator)
        except ImportError as e:
            logger.warning(f"Loading validator not available: {e}")

        # Production validator
        try:
            from magnet.production.validators import ProductionPlanningValidator
            cls.register_class("production/planning", ProductionPlanningValidator)
        except ImportError as e:
            logger.warning(f"Production validator not available: {e}")

        # Cost validator
        try:
            from magnet.cost.validators import CostValidator
            cls.register_class("cost/estimation", CostValidator)
        except ImportError as e:
            logger.warning(f"Cost validator not available: {e}")

        cls._initialized = True
        logger.info(f"Registered {len(cls._validator_classes)} validator classes")

    @classmethod
    def instantiate_all(cls) -> int:
        """Instantiate all registered validator classes."""
        for validator_id in list(cls._validator_classes.keys()):
            cls._instantiate(validator_id)
        return len(cls._instances)
