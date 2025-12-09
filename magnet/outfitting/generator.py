"""
outfitting/generator.py - Outfitting system generation
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from typing import Dict, Any, List, Tuple
from ..core.state_manager import StateManager
from .system import OutfittingSystem
from .spaces import AccommodationSpace, SPACE_REQUIREMENTS
from .furniture import FurnitureLibrary, FixtureLibrary
from .openings import Door, Window


class OutfittingGenerator:
    """Generate outfitting from requirements."""

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> OutfittingSystem:
        """Generate complete outfitting system."""

        loa = self.state.get("hull.loa", 25)
        beam = self.state.get("hull.beam", 6)
        crew = self.state.get("mission.crew_berthed", 5)
        passengers = self.state.get("mission.passengers", 0)

        # v1.1 FIX: Use metadata.design_id
        system = OutfittingSystem(
            system_id=f"OUT-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        system.spaces = self._generate_spaces(loa, beam, crew, passengers)
        system.furniture, system.furniture_weight_kg = self._generate_furniture(system.spaces)
        system.fixtures, system.fixture_weight_kg = self._generate_fixtures(system.spaces)
        system.doors = self._generate_doors(system.spaces)
        system.windows = self._generate_windows(loa, beam)

        system.calculate_totals()

        return system

    def _generate_spaces(
        self,
        loa: float,
        beam: float,
        crew: int,
        passengers: int,
    ) -> List[AccommodationSpace]:
        """Generate accommodation spaces."""
        spaces = []

        # Wheelhouse
        wh_length = loa * 0.12
        wh_width = beam * 0.7
        spaces.append(AccommodationSpace(
            space_id="SP-WH",
            space_name="Wheelhouse",
            space_type="wheelhouse",
            length_m=wh_length,
            width_m=wh_width,
            height_m=2.3,
            deck="bridge",
            design_occupancy=4,
        ))

        # Crew cabins
        num_crew_cabins = max(1, crew // 2)
        for i in range(num_crew_cabins):
            berths_in_cabin = min(2, crew - (i * 2))
            spaces.append(AccommodationSpace(
                space_id=f"SP-CC-{i+1}",
                space_name=f"Crew Cabin {i+1}",
                space_type="crew_cabin",
                length_m=3.0,
                width_m=2.5,
                height_m=2.1,
                deck="main",
                design_occupancy=berths_in_cabin,
                berths=berths_in_cabin,
            ))

        # Passenger saloon (if passengers)
        if passengers > 0:
            saloon_area = passengers * 1.2
            saloon_length = min(loa * 0.3, saloon_area / (beam * 0.6))
            spaces.append(AccommodationSpace(
                space_id="SP-SAL",
                space_name="Passenger Saloon",
                space_type="passenger_saloon",
                length_m=saloon_length,
                width_m=beam * 0.6,
                height_m=2.2,
                deck="main",
                design_occupancy=passengers,
            ))

        # Mess/Galley
        mess_area = max(8, (crew + passengers) * 0.5)
        spaces.append(AccommodationSpace(
            space_id="SP-MESS",
            space_name="Mess/Galley",
            space_type="mess",
            length_m=mess_area / 2.5,
            width_m=2.5,
            height_m=2.1,
            deck="main",
            design_occupancy=max(4, crew // 2),
        ))

        # Heads (1 per 8 persons minimum)
        num_heads = max(1, (crew + passengers) // 8)
        for i in range(num_heads):
            spaces.append(AccommodationSpace(
                space_id=f"SP-HEAD-{i+1}",
                space_name=f"Head {i+1}",
                space_type="head",
                length_m=1.8,
                width_m=1.2,
                height_m=2.1,
                deck="main",
            ))

        return spaces

    def _generate_furniture(
        self,
        spaces: List[AccommodationSpace],
    ) -> Tuple[List[Dict], float]:
        """Generate furniture for spaces."""
        furniture = []
        total_weight = 0.0

        for space in spaces:
            if space.space_type == "wheelhouse":
                item = FurnitureLibrary.get("helm_seat")
                furniture.append({"space_id": space.space_id, "item_type": "helm_seat", "quantity": 2})
                total_weight += item.weight_kg * 2

                item = FurnitureLibrary.get("nav_table")
                furniture.append({"space_id": space.space_id, "item_type": "nav_table", "quantity": 1})
                total_weight += item.weight_kg

            elif space.space_type == "crew_cabin":
                if space.berths == 2:
                    item = FurnitureLibrary.get("bunk_berth")
                    furniture.append({"space_id": space.space_id, "item_type": "bunk_berth", "quantity": 1})
                    total_weight += item.weight_kg
                else:
                    item = FurnitureLibrary.get("single_berth")
                    furniture.append({"space_id": space.space_id, "item_type": "single_berth", "quantity": space.berths})
                    total_weight += item.weight_kg * space.berths

                item = FurnitureLibrary.get("locker")
                furniture.append({"space_id": space.space_id, "item_type": "locker", "quantity": space.berths})
                total_weight += item.weight_kg * space.berths

            elif space.space_type == "passenger_saloon":
                item = FurnitureLibrary.get("passenger_seat")
                furniture.append({"space_id": space.space_id, "item_type": "passenger_seat", "quantity": space.design_occupancy})
                total_weight += item.weight_kg * space.design_occupancy

            elif space.space_type == "mess":
                item = FurnitureLibrary.get("mess_table")
                num_tables = max(1, space.design_occupancy // 6)
                furniture.append({"space_id": space.space_id, "item_type": "mess_table", "quantity": num_tables})
                total_weight += item.weight_kg * num_tables

                item = FurnitureLibrary.get("crew_seat")
                furniture.append({"space_id": space.space_id, "item_type": "crew_seat", "quantity": space.design_occupancy})
                total_weight += item.weight_kg * space.design_occupancy

        return furniture, total_weight

    def _generate_fixtures(
        self,
        spaces: List[AccommodationSpace],
    ) -> Tuple[List[Dict], float]:
        """Generate fixtures for spaces."""
        fixtures = []
        total_weight = 0.0

        for space in spaces:
            if space.space_type == "head":
                item = FixtureLibrary.get("marine_toilet")
                fixtures.append({"space_id": space.space_id, "item_type": "marine_toilet", "quantity": 1})
                total_weight += item.weight_kg

                item = FixtureLibrary.get("sink")
                fixtures.append({"space_id": space.space_id, "item_type": "sink", "quantity": 1})
                total_weight += item.weight_kg

                if "HEAD-1" in space.space_id:
                    item = FixtureLibrary.get("shower")
                    fixtures.append({"space_id": space.space_id, "item_type": "shower", "quantity": 1})
                    total_weight += item.weight_kg

            elif space.space_type == "mess":
                crew = self.state.get("mission.crew_berthed", 5)

                stove_type = "stove_4" if crew > 6 else "stove_2"
                item = FixtureLibrary.get(stove_type)
                fixtures.append({"space_id": space.space_id, "item_type": stove_type, "quantity": 1})
                total_weight += item.weight_kg

                fridge_type = "fridge_200" if crew > 6 else "fridge_100"
                item = FixtureLibrary.get(fridge_type)
                fixtures.append({"space_id": space.space_id, "item_type": fridge_type, "quantity": 1})
                total_weight += item.weight_kg

                item = FixtureLibrary.get("sink")
                fixtures.append({"space_id": space.space_id, "item_type": "sink", "quantity": 1})
                total_weight += item.weight_kg

                item = FixtureLibrary.get("microwave")
                fixtures.append({"space_id": space.space_id, "item_type": "microwave", "quantity": 1})
                total_weight += item.weight_kg

        return fixtures, total_weight

    def _generate_doors(self, spaces: List[AccommodationSpace]) -> List[Door]:
        """Generate doors for spaces."""
        doors = []
        door_idx = 1

        for space in spaces:
            if space.space_type == "wheelhouse":
                doors.append(Door.create("weathertight", f"DR-{door_idx}"))
            elif space.space_type in ["crew_cabin", "officer_cabin"]:
                doors.append(Door.create("fire_rated", f"DR-{door_idx}"))
            elif space.space_type == "head":
                doors.append(Door.create("standard", f"DR-{door_idx}"))
            else:
                doors.append(Door.create("standard", f"DR-{door_idx}"))
            door_idx += 1

        doors.append(Door.create("watertight", f"DR-{door_idx}"))

        return doors

    def _generate_windows(self, loa: float, beam: float) -> List[Window]:
        """Generate windows."""
        windows = []

        wh_width = beam * 0.7
        num_front = max(3, int(wh_width / 0.8))
        for i in range(num_front):
            windows.append(Window.create("fixed", 700, 500, f"WIN-WH-F{i+1}"))

        for i in range(2):
            windows.append(Window.create("opening", 600, 400, f"WIN-WH-P{i+1}"))
            windows.append(Window.create("opening", 600, 400, f"WIN-WH-S{i+1}"))

        num_portlights = int(loa / 4)
        for i in range(num_portlights):
            windows.append(Window.create("portlight", 300, 300, f"WIN-PL-{i+1}"))

        return windows
