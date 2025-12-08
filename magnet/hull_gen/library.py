"""
hull_gen/library.py - Parent hull library with standard designs.

BRAVO OWNS THIS FILE.

Module 16 v1.0 - Parent hull library.
"""

from typing import Dict, List, Optional
from .parameters import (
    HullDefinition, MainDimensions, FormCoefficients,
    DeadriseProfile, HullFeatures
)
from .enums import (
    HullType, ChineType, StemProfile, SternProfile,
    TransomType, KeelType
)


class ParentHullLibrary:
    """
    Library of parent hull forms.

    Parent hulls serve as starting points for parametric variation.
    """

    PARENT_HULLS: Dict[str, HullDefinition] = {}

    @classmethod
    def register(cls, hull: HullDefinition) -> None:
        """Register a parent hull."""
        cls.PARENT_HULLS[hull.hull_id] = hull

    @classmethod
    def get(cls, hull_id: str) -> Optional[HullDefinition]:
        """Get parent hull by ID."""
        return cls.PARENT_HULLS.get(hull_id)

    @classmethod
    def list_all(cls) -> List[str]:
        """List all available parent hulls."""
        return list(cls.PARENT_HULLS.keys())

    @classmethod
    def get_by_type(cls, hull_type: HullType) -> List[HullDefinition]:
        """Get all hulls of a specific type."""
        return [h for h in cls.PARENT_HULLS.values() if h.hull_type == hull_type]

    @classmethod
    def initialize_defaults(cls) -> None:
        """Initialize default parent hulls."""

        # === 25M PATROL BOAT (Deep-V) ===
        patrol_25m = HullDefinition(
            hull_id="PATROL-25M-V",
            hull_name="25m Patrol Boat (Deep-V)",
            hull_type=HullType.DEEP_V_PLANING,
            dimensions=MainDimensions(
                loa=26.0,
                lwl=24.0,
                lpp=23.5,
                beam_max=6.2,
                beam_wl=5.8,
                beam_chine=5.5,
                depth=3.2,
                draft=1.4,
                draft_fwd=1.2,
                draft_aft=1.5,
                freeboard_bow=2.8,
                freeboard_mid=1.8,
                freeboard_stern=1.7,
            ),
            coefficients=FormCoefficients(
                cb=0.38,
                cp=0.58,
                cm=0.66,
                cwp=0.72,
                lcb=0.42,
                lcf=0.44,
            ),
            deadrise=DeadriseProfile.warped(
                transom=18.0,
                midship=20.0,
                bow=45.0,
            ),
            features=HullFeatures(
                chine_type=ChineType.HARD,
                chine_width_mm=50,
                stem_profile=StemProfile.RAKED,
                stem_rake_deg=20,
                bow_flare_deg=15,
                stern_profile=SternProfile.TRANSOM,
                transom_type=TransomType.DRY,
                transom_rake_deg=12,
                transom_width_fraction=0.82,
                keel_type=KeelType.FLAT,
            ),
        )
        patrol_25m.compute_displacement()
        cls.register(patrol_25m)

        # === 35M CREW BOAT (Semi-Displacement) ===
        crew_35m = HullDefinition(
            hull_id="CREW-35M-SD",
            hull_name="35m Crew Boat (Semi-Displacement)",
            hull_type=HullType.SEMI_DISPLACEMENT,
            dimensions=MainDimensions(
                loa=36.0,
                lwl=33.5,
                lpp=33.0,
                beam_max=8.0,
                beam_wl=7.5,
                beam_chine=7.0,
                depth=4.0,
                draft=1.8,
                draft_fwd=1.6,
                draft_aft=1.9,
                freeboard_bow=3.5,
                freeboard_mid=2.2,
                freeboard_stern=2.1,
            ),
            coefficients=FormCoefficients(
                cb=0.48,
                cp=0.64,
                cm=0.75,
                cwp=0.76,
                lcb=0.48,
                lcf=0.50,
            ),
            deadrise=DeadriseProfile.warped(
                transom=14.0,
                midship=16.0,
                bow=40.0,
            ),
            features=HullFeatures(
                chine_type=ChineType.HARD,
                chine_width_mm=75,
                stem_profile=StemProfile.RAKED,
                stem_rake_deg=18,
                bow_flare_deg=12,
                stern_profile=SternProfile.TRANSOM,
                transom_type=TransomType.SEMI_IMMERSED,
                transom_rake_deg=10,
                transom_width_fraction=0.78,
                keel_type=KeelType.SKEG,
                skeg_height_m=0.4,
            ),
        )
        crew_35m.compute_displacement()
        cls.register(crew_35m)

        # === 45M FERRY (Catamaran) ===
        ferry_45m_cat = HullDefinition(
            hull_id="FERRY-45M-CAT",
            hull_name="45m Ferry (Catamaran)",
            hull_type=HullType.CATAMARAN,
            dimensions=MainDimensions(
                loa=46.0,
                lwl=43.0,
                lpp=42.5,
                beam_max=12.0,  # Overall
                beam_wl=3.2,    # Per demi-hull
                beam_chine=3.0,
                depth=4.5,
                draft=1.6,
                draft_fwd=1.5,
                draft_aft=1.7,
                freeboard_bow=4.0,
                freeboard_mid=2.9,
                freeboard_stern=2.8,
            ),
            coefficients=FormCoefficients(
                cb=0.42,
                cp=0.60,
                cm=0.70,
                cwp=0.74,
                lcb=0.46,
                lcf=0.48,
            ),
            deadrise=DeadriseProfile.warped(
                transom=12.0,
                midship=15.0,
                bow=35.0,
            ),
            features=HullFeatures(
                chine_type=ChineType.HARD,
                chine_width_mm=40,
                stem_profile=StemProfile.WAVE_PIERCING,
                stem_rake_deg=25,
                bow_flare_deg=8,
                stern_profile=SternProfile.TRANSOM,
                transom_type=TransomType.DRY,
                transom_rake_deg=8,
                transom_width_fraction=0.75,
                keel_type=KeelType.FLAT,
                has_tunnels=True,
                tunnel_width_m=5.6,
                tunnel_depth_m=2.8,
            ),
        )
        ferry_45m_cat.compute_displacement()
        cls.register(ferry_45m_cat)

        # === 15M RIB (Deep-V) ===
        rib_15m = HullDefinition(
            hull_id="RIB-15M-V",
            hull_name="15m RIB (Deep-V)",
            hull_type=HullType.DEEP_V_PLANING,
            dimensions=MainDimensions(
                loa=15.5,
                lwl=14.0,
                lpp=13.8,
                beam_max=4.2,
                beam_wl=3.8,
                beam_chine=3.6,
                depth=2.0,
                draft=0.8,
                draft_fwd=0.7,
                draft_aft=0.9,
                freeboard_bow=1.8,
                freeboard_mid=1.2,
                freeboard_stern=1.1,
            ),
            coefficients=FormCoefficients(
                cb=0.32,
                cp=0.52,
                cm=0.62,
                cwp=0.68,
                lcb=0.40,
                lcf=0.42,
            ),
            deadrise=DeadriseProfile.warped(
                transom=22.0,
                midship=24.0,
                bow=50.0,
            ),
            features=HullFeatures(
                chine_type=ChineType.DOUBLE,
                chine_width_mm=30,
                stem_profile=StemProfile.RAKED,
                stem_rake_deg=22,
                bow_flare_deg=18,
                stern_profile=SternProfile.TRANSOM,
                transom_type=TransomType.DRY,
                transom_rake_deg=14,
                transom_width_fraction=0.85,
                keel_type=KeelType.FLAT,
            ),
        )
        rib_15m.compute_displacement()
        cls.register(rib_15m)

        # === 20M WORKBOAT (Round Bilge) ===
        workboat_20m = HullDefinition(
            hull_id="WORK-20M-RB",
            hull_name="20m Workboat (Round Bilge)",
            hull_type=HullType.ROUND_BILGE,
            dimensions=MainDimensions(
                loa=21.0,
                lwl=19.5,
                lpp=19.0,
                beam_max=6.5,
                beam_wl=6.2,
                beam_chine=0.0,  # No chine for round bilge
                depth=3.0,
                draft=1.6,
                draft_fwd=1.4,
                draft_aft=1.7,
                freeboard_bow=2.2,
                freeboard_mid=1.4,
                freeboard_stern=1.3,
            ),
            coefficients=FormCoefficients(
                cb=0.58,
                cp=0.70,
                cm=0.83,
                cwp=0.80,
                lcb=0.52,
                lcf=0.53,
            ),
            deadrise=DeadriseProfile.constant(5.0),
            features=HullFeatures(
                chine_type=ChineType.NONE,
                stem_profile=StemProfile.RAKED,
                stem_rake_deg=12,
                bow_flare_deg=8,
                stern_profile=SternProfile.CRUISER,
                transom_type=TransomType.IMMERSED,
                transom_rake_deg=5,
                transom_width_fraction=0.60,
                keel_type=KeelType.BAR,
            ),
        )
        workboat_20m.compute_displacement()
        cls.register(workboat_20m)


# Initialize defaults on module load
ParentHullLibrary.initialize_defaults()
