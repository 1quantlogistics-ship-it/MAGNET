"""
layout_generator.py - Interior layout generation v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Generates interior layouts from hull geometry and design requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import math
import logging
import uuid

from magnet.interior.schema.space import (
    SpaceType,
    SpaceCategory,
    SpaceDefinition,
    SpaceBoundary,
    SpaceConnection,
    DEFAULT_SPACE_CAPACITIES,
)
from magnet.interior.schema.layout import (
    InteriorLayout,
    LayoutVersion,
    DeckLayout,
    LayoutMetadata,
)
from magnet.interior.schema.validation import (
    ValidationResult,
    validate_space_constraints,
)

__all__ = [
    'LayoutGenerator',
    'GenerationConfig',
    'GenerationResult',
    'DeckConfig',
]

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class DeckConfig:
    """Configuration for a single deck."""

    deck_name: str
    deck_number: int
    z_level: float
    height: float = 2.5
    is_weather_deck: bool = False

    # Space allocations for this deck
    space_types: List[SpaceType] = field(default_factory=list)

    # Frame extent
    frame_start: Optional[float] = None
    frame_end: Optional[float] = None


@dataclass
class GenerationConfig:
    """Configuration for layout generation."""

    # Principal dimensions
    loa: float = 100.0  # Length overall (m)
    beam: float = 20.0  # Beam (m)
    depth: float = 10.0  # Depth (m)
    draft: float = 5.0  # Design draft (m)

    # Deck configuration
    deck_height: float = 2.5  # Default deck height (m)
    num_decks: int = 4

    # Custom deck configs (overrides auto-generation)
    deck_configs: List[DeckConfig] = field(default_factory=list)

    # Hull margins
    side_margin: float = 0.5  # Distance from shell plating (m)
    end_margin: float = 2.0  # Distance from bulkheads (m)

    # Space requirements
    crew_capacity: int = 20
    passenger_capacity: int = 0

    # Ship type
    ship_type: str = "general_cargo"

    # Generation options
    generate_cabins: bool = True
    generate_machinery: bool = True
    generate_cargo: bool = True
    generate_service: bool = True

    # Frame spacing
    frame_spacing: float = 0.6  # meters


@dataclass
class GenerationResult:
    """Result of layout generation."""

    success: bool
    layout: Optional[InteriorLayout] = None
    validation: Optional[ValidationResult] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    generation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "layout": self.layout.to_dict() if self.layout else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "warnings": self.warnings,
            "errors": self.errors,
            "generation_time_ms": self.generation_time_ms,
        }


# =============================================================================
# LAYOUT GENERATOR
# =============================================================================

class LayoutGenerator:
    """
    Generates interior layouts from hull geometry and requirements.

    This is the main generation engine for Module 59.
    """

    def __init__(self, config: GenerationConfig):
        """
        Initialize the generator.

        Args:
            config: Generation configuration
        """
        self._config = config
        self._space_id_counter = 0

    # -------------------------------------------------------------------------
    # Main Generation
    # -------------------------------------------------------------------------

    def generate(self, design_id: str) -> GenerationResult:
        """
        Generate a complete interior layout.

        Args:
            design_id: ID of the design to generate layout for

        Returns:
            GenerationResult with layout and validation
        """
        import time
        start_time = time.time()

        try:
            # Create empty layout
            layout = InteriorLayout.create_empty(design_id)
            layout.metadata = self._create_metadata(design_id)

            # Generate decks
            deck_configs = self._get_deck_configs()
            for deck_config in deck_configs:
                deck = self._generate_deck(deck_config)
                layout.add_deck(deck)

            # Generate spaces on each deck
            self._generate_spaces(layout)

            # Generate connections
            self._generate_connections(layout)

            # Update metadata statistics
            layout.metadata.num_decks = layout.deck_count
            layout.metadata.total_area = layout.total_area
            layout.metadata.total_volume = layout.total_volume
            layout.metadata.total_spaces = layout.space_count

            # Validate
            all_spaces = layout.get_all_spaces()
            validation = validate_space_constraints(all_spaces)

            elapsed = (time.time() - start_time) * 1000

            return GenerationResult(
                success=True,
                layout=layout,
                validation=validation,
                generation_time_ms=elapsed,
            )

        except Exception as e:
            logger.error(f"Layout generation failed: {e}")
            elapsed = (time.time() - start_time) * 1000
            return GenerationResult(
                success=False,
                errors=[str(e)],
                generation_time_ms=elapsed,
            )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def _create_metadata(self, design_id: str) -> LayoutMetadata:
        """Create layout metadata from config."""
        return LayoutMetadata(
            design_id=design_id,
            ship_type=self._config.ship_type,
            loa=self._config.loa,
            beam=self._config.beam,
            depth=self._config.depth,
            crew_capacity=self._config.crew_capacity,
            passenger_capacity=self._config.passenger_capacity,
        )

    # -------------------------------------------------------------------------
    # Deck Generation
    # -------------------------------------------------------------------------

    def _get_deck_configs(self) -> List[DeckConfig]:
        """Get deck configurations."""
        if self._config.deck_configs:
            return self._config.deck_configs

        # Auto-generate deck configs based on ship dimensions
        configs = []
        z = 0.0  # Start at baseline

        for i in range(self._config.num_decks):
            is_weather = (i == self._config.num_decks - 1)

            # Determine deck name
            if i == 0:
                name = "Tank Top"
            elif i == self._config.num_decks - 1:
                name = "Main Deck"
            else:
                name = f"Deck {i}"

            configs.append(DeckConfig(
                deck_name=name,
                deck_number=i,
                z_level=z,
                height=self._config.deck_height,
                is_weather_deck=is_weather,
            ))

            z += self._config.deck_height

        return configs

    def _generate_deck(self, config: DeckConfig) -> DeckLayout:
        """Generate a single deck layout."""
        return DeckLayout(
            deck_id=f"DECK-{config.deck_number:02d}",
            deck_name=config.deck_name,
            deck_number=config.deck_number,
            z_level=config.z_level,
            height=config.height,
            is_weather_deck=config.is_weather_deck,
            frame_start=config.frame_start or 0,
            frame_end=config.frame_end or (self._config.loa / self._config.frame_spacing),
        )

    # -------------------------------------------------------------------------
    # Space Generation
    # -------------------------------------------------------------------------

    def _generate_spaces(self, layout: InteriorLayout) -> None:
        """Generate spaces on all decks."""
        decks = layout.get_decks_sorted()

        if not decks:
            return

        # Bottom deck: tanks and machinery
        if self._config.generate_machinery:
            self._generate_machinery_deck(layout, decks[0])

        # Middle decks: accommodation and service
        for deck in decks[1:-1] if len(decks) > 2 else []:
            self._generate_accommodation_deck(layout, deck)

        # Top deck: bridge and control
        if len(decks) > 1:
            self._generate_control_deck(layout, decks[-1])

    def _generate_machinery_deck(self, layout: InteriorLayout, deck: DeckLayout) -> None:
        """Generate machinery spaces on bottom deck."""
        loa = self._config.loa
        beam = self._config.beam
        margin = self._config.side_margin

        # Engine room (aft section, ~30% of length)
        engine_room = self._create_space(
            name="Main Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            deck=deck,
            x_start=0.0,
            x_end=loa * 0.3,
            y_start=-beam/2 + margin,
            y_end=beam/2 - margin,
        )
        layout.add_space(engine_room)

        # Generator room (adjacent to engine room)
        gen_room = self._create_space(
            name="Generator Room",
            space_type=SpaceType.GENERATOR_ROOM,
            deck=deck,
            x_start=loa * 0.3,
            x_end=loa * 0.4,
            y_start=-beam/2 + margin,
            y_end=beam/2 - margin,
        )
        layout.add_space(gen_room)

        # Switchboard room
        switch_room = self._create_space(
            name="Main Switchboard",
            space_type=SpaceType.SWITCHBOARD_ROOM,
            deck=deck,
            x_start=loa * 0.4,
            x_end=loa * 0.45,
            y_start=-beam/2 + margin,
            y_end=0,
        )
        layout.add_space(switch_room)

        # Workshop
        workshop = self._create_space(
            name="Workshop",
            space_type=SpaceType.WORKSHOP,
            deck=deck,
            x_start=loa * 0.4,
            x_end=loa * 0.45,
            y_start=0,
            y_end=beam/2 - margin,
        )
        layout.add_space(workshop)

        # Steering gear (far aft)
        steering = self._create_space(
            name="Steering Gear Room",
            space_type=SpaceType.STEERING_GEAR,
            deck=deck,
            x_start=-loa * 0.05,
            x_end=0.0,
            y_start=-beam/4,
            y_end=beam/4,
        )
        layout.add_space(steering)

    def _generate_accommodation_deck(self, layout: InteriorLayout, deck: DeckLayout) -> None:
        """Generate accommodation spaces on middle decks."""
        loa = self._config.loa
        beam = self._config.beam
        margin = self._config.side_margin

        # Central corridor
        corridor = self._create_space(
            name=f"Corridor {deck.deck_name}",
            space_type=SpaceType.CORRIDOR,
            deck=deck,
            x_start=loa * 0.2,
            x_end=loa * 0.8,
            y_start=-1.0,
            y_end=1.0,
        )
        layout.add_space(corridor)

        # Cabins on port side
        cabin_width = 3.0
        cabin_depth = 4.0
        x_pos = loa * 0.25

        for i in range(self._config.crew_capacity // 4):
            cabin = self._create_space(
                name=f"Crew Cabin P{i+1}",
                space_type=SpaceType.CABIN_CREW,
                deck=deck,
                x_start=x_pos,
                x_end=x_pos + cabin_width,
                y_start=-beam/2 + margin,
                y_end=-beam/2 + margin + cabin_depth,
            )
            layout.add_space(cabin)
            x_pos += cabin_width + 0.5

            if x_pos > loa * 0.75:
                break

        # Cabins on starboard side
        x_pos = loa * 0.25
        for i in range(self._config.crew_capacity // 4):
            cabin = self._create_space(
                name=f"Crew Cabin S{i+1}",
                space_type=SpaceType.CABIN_CREW,
                deck=deck,
                x_start=x_pos,
                x_end=x_pos + cabin_width,
                y_start=beam/2 - margin - cabin_depth,
                y_end=beam/2 - margin,
            )
            layout.add_space(cabin)
            x_pos += cabin_width + 0.5

            if x_pos > loa * 0.75:
                break

        # Mess room
        mess = self._create_space(
            name="Crew Mess",
            space_type=SpaceType.MESS_CREW,
            deck=deck,
            x_start=loa * 0.5,
            x_end=loa * 0.6,
            y_start=-beam/2 + margin,
            y_end=-beam/4,
        )
        layout.add_space(mess)

        # Galley
        galley = self._create_space(
            name="Galley",
            space_type=SpaceType.GALLEY,
            deck=deck,
            x_start=loa * 0.5,
            x_end=loa * 0.6,
            y_start=beam/4,
            y_end=beam/2 - margin,
        )
        layout.add_space(galley)

    def _generate_control_deck(self, layout: InteriorLayout, deck: DeckLayout) -> None:
        """Generate control spaces on top deck."""
        loa = self._config.loa
        beam = self._config.beam
        margin = self._config.side_margin

        # Bridge (forward)
        bridge = self._create_space(
            name="Navigation Bridge",
            space_type=SpaceType.BRIDGE,
            deck=deck,
            x_start=loa * 0.85,
            x_end=loa - margin,
            y_start=-beam/2 + margin,
            y_end=beam/2 - margin,
        )
        layout.add_space(bridge)

        # Chart room
        chart = self._create_space(
            name="Chart Room",
            space_type=SpaceType.CHART_ROOM,
            deck=deck,
            x_start=loa * 0.8,
            x_end=loa * 0.85,
            y_start=-beam/4,
            y_end=beam/4,
        )
        layout.add_space(chart)

        # Radio room
        radio = self._create_space(
            name="Radio Room",
            space_type=SpaceType.RADIO_ROOM,
            deck=deck,
            x_start=loa * 0.8,
            x_end=loa * 0.85,
            y_start=beam/4,
            y_end=beam/2 - margin,
        )
        layout.add_space(radio)

        # Captain cabin
        captain = self._create_space(
            name="Captain Cabin",
            space_type=SpaceType.CABIN_OFFICER,
            deck=deck,
            x_start=loa * 0.75,
            x_end=loa * 0.8,
            y_start=-beam/2 + margin,
            y_end=-beam/4,
        )
        layout.add_space(captain)

    # -------------------------------------------------------------------------
    # Space Creation Helper
    # -------------------------------------------------------------------------

    def _create_space(
        self,
        name: str,
        space_type: SpaceType,
        deck: DeckLayout,
        x_start: float,
        x_end: float,
        y_start: float,
        y_end: float,
    ) -> SpaceDefinition:
        """Create a rectangular space."""
        self._space_id_counter += 1
        space_id = f"SPACE-{self._space_id_counter:04d}"

        # Create boundary polygon (rectangular)
        points = [
            (x_start, y_start),
            (x_end, y_start),
            (x_end, y_end),
            (x_start, y_end),
        ]

        # Determine category
        category_map = {
            SpaceType.ENGINE_ROOM: SpaceCategory.OPERATIONAL,
            SpaceType.GENERATOR_ROOM: SpaceCategory.OPERATIONAL,
            SpaceType.SWITCHBOARD_ROOM: SpaceCategory.OPERATIONAL,
            SpaceType.WORKSHOP: SpaceCategory.OPERATIONAL,
            SpaceType.STEERING_GEAR: SpaceCategory.OPERATIONAL,
            SpaceType.BRIDGE: SpaceCategory.OPERATIONAL,
            SpaceType.CHART_ROOM: SpaceCategory.OPERATIONAL,
            SpaceType.RADIO_ROOM: SpaceCategory.OPERATIONAL,
            SpaceType.CABIN_CREW: SpaceCategory.LIVING,
            SpaceType.CABIN_OFFICER: SpaceCategory.LIVING,
            SpaceType.MESS_CREW: SpaceCategory.LIVING,
            SpaceType.GALLEY: SpaceCategory.SERVICE,
            SpaceType.CORRIDOR: SpaceCategory.CIRCULATION,
        }
        category = category_map.get(space_type, SpaceCategory.OPERATIONAL)

        return SpaceDefinition(
            space_id=space_id,
            name=name,
            space_type=space_type,
            category=category,
            boundary=SpaceBoundary(
                points=points,
                deck_id=deck.deck_id,
                z_min=deck.z_level,
                z_max=deck.z_level + deck.height,
            ),
            deck_id=deck.deck_id,
            frame_start=x_start / self._config.frame_spacing,
            frame_end=x_end / self._config.frame_spacing,
        )

    # -------------------------------------------------------------------------
    # Connection Generation
    # -------------------------------------------------------------------------

    def _generate_connections(self, layout: InteriorLayout) -> None:
        """Generate connections between spaces."""
        # For each deck, connect adjacent spaces via corridor
        for deck in layout.decks.values():
            corridor = None
            for space in deck.spaces.values():
                if space.space_type == SpaceType.CORRIDOR:
                    corridor = space
                    break

            if not corridor:
                continue

            # Connect all spaces on this deck to corridor
            conn_id = 0
            for space in deck.spaces.values():
                if space.space_id == corridor.space_id:
                    continue

                conn_id += 1
                connection = SpaceConnection(
                    connection_id=f"CONN-{deck.deck_id}-{conn_id:03d}",
                    from_space_id=corridor.space_id,
                    to_space_id=space.space_id,
                    connection_type="door",
                    width=0.8,
                    height=2.0,
                )
                layout.add_connection(connection)

        # Connect decks via stairways
        decks_sorted = layout.get_decks_sorted()
        for i in range(len(decks_sorted) - 1):
            lower = decks_sorted[i]
            upper = decks_sorted[i + 1]

            # Find corridors on each deck
            lower_corridor = None
            upper_corridor = None
            for s in lower.spaces.values():
                if s.space_type == SpaceType.CORRIDOR:
                    lower_corridor = s
                    break
            for s in upper.spaces.values():
                if s.space_type == SpaceType.CORRIDOR:
                    upper_corridor = s
                    break

            if lower_corridor and upper_corridor:
                connection = SpaceConnection(
                    connection_id=f"STAIR-{lower.deck_id}-{upper.deck_id}",
                    from_space_id=lower_corridor.space_id,
                    to_space_id=upper_corridor.space_id,
                    connection_type="ladder",
                    width=0.8,
                    height=upper.z_level - lower.z_level,
                )
                layout.add_connection(connection)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_basic_layout(
    design_id: str,
    loa: float = 100.0,
    beam: float = 20.0,
    depth: float = 10.0,
    crew_capacity: int = 20,
) -> GenerationResult:
    """
    Generate a basic interior layout.

    Args:
        design_id: Design ID
        loa: Length overall (m)
        beam: Beam (m)
        depth: Depth (m)
        crew_capacity: Number of crew

    Returns:
        GenerationResult
    """
    config = GenerationConfig(
        loa=loa,
        beam=beam,
        depth=depth,
        crew_capacity=crew_capacity,
    )
    generator = LayoutGenerator(config)
    return generator.generate(design_id)
