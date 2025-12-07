"""
DesignState Contract - Abstract Base Class

Defines the interface that DesignState must implement.
All 27 sections must be present with serialization support.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Optional


class DesignStateContract(ABC):
    """
    Abstract contract for the unified design state container.

    Required Sections (27):
    1. mission - MissionConfig
    2. hull - HullState
    3. structural_design - StructuralDesign
    4. structural_loads - StructuralLoads
    5. propulsion - PropulsionState
    6. weight - WeightEstimate
    7. stability - StabilityState
    8. loading - LoadingState
    9. arrangement - ArrangementState
    10. compliance - ComplianceState
    11. production - ProductionState
    12. cost - CostState
    13. optimization - OptimizationState
    14. reports - ReportsState
    15. kernel - KernelState
    16. analysis - AnalysisState
    17. performance - PerformanceState
    18. systems - SystemsState
    19. outfitting - OutfittingState
    20. environmental - EnvironmentalState
    21. deck_equipment - DeckEquipmentState
    22. vision - VisionState
    23. resistance - ResistanceState
    24. seakeeping - SeakeepingState
    25. maneuvering - ManeuveringState
    26. electrical - ElectricalState
    27. safety - SafetyState
    """

    # Required identity fields
    design_id: Optional[str]
    design_name: Optional[str]
    version: str

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the entire design state to a dictionary.

        Returns:
            Dictionary representation of all 27 sections plus metadata.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignStateContract":
        """
        Deserialize a dictionary into a DesignState instance.

        Args:
            data: Dictionary containing serialized design state.

        Returns:
            New DesignState instance populated from the dictionary.
        """
        pass

    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the design state for internal consistency.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def patch(self, updates: Dict[str, Any], source: str) -> List[str]:
        """
        Apply a partial update to the design state.

        Args:
            updates: Dictionary of path -> value updates.
            source: Identifier of the update source (agent, user, etc.)

        Returns:
            List of paths that were modified.
        """
        pass

    @abstractmethod
    def diff(self, other: "DesignStateContract") -> Dict[str, Tuple[Any, Any]]:
        """
        Compare this state with another and return differences.

        Args:
            other: Another DesignState to compare against.

        Returns:
            Dictionary mapping changed paths to (old_value, new_value) tuples.
        """
        pass

    @abstractmethod
    def get_section(self, section_name: str) -> Any:
        """
        Get a specific section by name.

        Args:
            section_name: Name of the section (e.g., 'mission', 'hull').

        Returns:
            The section dataclass instance.
        """
        pass

    @abstractmethod
    def set_section(self, section_name: str, value: Any) -> None:
        """
        Set a specific section by name.

        Args:
            section_name: Name of the section.
            value: New value for the section.
        """
        pass


# List of required section names for validation
REQUIRED_SECTIONS = [
    "mission",
    "hull",
    "structural_design",
    "structural_loads",
    "propulsion",
    "weight",
    "stability",
    "loading",
    "arrangement",
    "compliance",
    "production",
    "cost",
    "optimization",
    "reports",
    "kernel",
    "analysis",
    "performance",
    "systems",
    "outfitting",
    "environmental",
    "deck_equipment",
    "vision",
    "resistance",
    "seakeeping",
    "maneuvering",
    "electrical",
    "safety",
]
