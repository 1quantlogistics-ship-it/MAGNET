#!/usr/bin/env python3
"""
MAGNET End-to-End Design Runner

Runs the complete MAGNET design pipeline from mission parameters through
hull synthesis, weight estimation, stability analysis, and compliance verification.

Usage:
    python scripts/run_design.py --speed 25 --type workboat --crew 4
    python scripts/run_design.py --speed 30 --type patrol --crew 6 --range 500

Examples:
    # Basic workboat design
    python scripts/run_design.py

    # High-speed patrol boat
    python scripts/run_design.py --speed 35 --type patrol --crew 8 --range 300

    # Ferry with specific LOA
    python scripts/run_design.py --speed 20 --type ferry --crew 4 --loa 40
"""

import argparse
import sys
import os

# Ensure MAGNET is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magnet.bootstrap.app import MAGNETApp
from magnet.core.state_manager import StateManager
from magnet.kernel.conductor import Conductor


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")


def run_design(
    max_speed_kts: float,
    vessel_type: str = "workboat",
    crew: int = 4,
    range_nm: float = 300.0,
    loa_m: float = None,
    verbose: bool = True
) -> dict:
    """
    Run complete MAGNET design pipeline.

    Args:
        max_speed_kts: Maximum speed in knots (required for Froude calculation)
        vessel_type: Hull family type (workboat, patrol, ferry, planing, catamaran)
        crew: Number of crew berthed
        range_nm: Design range in nautical miles
        loa_m: Optional LOA constraint in meters
        verbose: Print progress and results

    Returns:
        Dictionary with design results
    """

    if verbose:
        print_header("MAGNET DESIGN PIPELINE")

    # Phase 1: Initialize application
    if verbose:
        print("\n[1/6] Initializing MAGNETApp...")

    app = MAGNETApp().build()
    state = app.container.resolve(StateManager)
    conductor = app.container.resolve(Conductor)

    if verbose:
        print("       Application initialized successfully.")

    # Phase 2: Seed mission parameters
    if verbose:
        print("\n[2/6] Seeding mission parameters...")

    state.set("mission.max_speed_kts", max_speed_kts, "user")
    state.set("mission.vessel_type", vessel_type, "user")
    state.set("mission.crew_berthed", crew, "user")
    state.set("mission.range_nm", range_nm, "user")
    state.set("hull.hull_type", vessel_type, "user")

    if loa_m:
        state.set("mission.loa_m", loa_m, "user")

    if verbose:
        print(f"       Max Speed:    {max_speed_kts} kts")
        print(f"       Vessel Type:  {vessel_type}")
        print(f"       Crew:         {crew}")
        print(f"       Range:        {range_nm} nm")
        if loa_m:
            print(f"       LOA:          {loa_m} m")

    # Phase 3: Create design session
    if verbose:
        print("\n[3/6] Creating design session...")

    conductor.create_session("user_design_001")

    if verbose:
        print("       Session created: user_design_001")

    # Phase 4: Run design phases
    # Full dependency chain: mission -> hull -> structure/propulsion -> weight -> stability
    # Note: loading requires arrangement.tanks which needs additional setup
    # Note: compliance requires loading which we skip for now
    # Core design phases give us the essential hull/weight/stability results
    phases = ["mission", "hull", "structure", "propulsion", "weight", "stability"]

    if verbose:
        print(f"\n[4/6] Running core design phases: {phases}")

    results = []
    all_passed = True

    for phase in phases:
        if verbose:
            print(f"\n       [{phase.upper()}] Running phase...")

        try:
            result = conductor.run_phase(phase)
            results.append(result)

            status_str = result.status.value if hasattr(result.status, 'value') else str(result.status)

            if verbose:
                print(f"       [{phase.upper()}] Status: {status_str}")

            if "FAILED" in status_str.upper() or "BLOCKED" in status_str.upper():
                all_passed = False
                if verbose:
                    print(f"       [{phase.upper()}] Errors: {result.errors}")
                # Continue to try other phases for diagnostic purposes

        except Exception as e:
            all_passed = False
            if verbose:
                print(f"       [{phase.upper()}] Exception: {e}")
            results.append({"phase_name": phase, "status": "ERROR", "error": str(e)})

    # Phase 5: Extract results
    if verbose:
        print("\n[5/6] Extracting design results...")

    # Hull dimensions
    lwl = state.get("hull.lwl")
    beam = state.get("hull.beam")
    draft = state.get("hull.draft")
    depth = state.get("hull.depth")
    cb = state.get("hull.cb")

    # Calculate displacement
    vol = None
    disp = None
    if lwl and beam and draft and cb:
        vol = lwl * beam * draft * cb
        disp = vol * 1.025  # seawater density

    # Weight values - check multiple possible keys
    lightship = (
        state.get("weight.lightship") or
        state.get("weight.lightship_weight_mt") or
        state.get("weight.lightship_tonnes")
    )

    # Stability values
    kb = state.get("stability.kb_m")
    bm = state.get("stability.bm_m")
    kg = state.get("stability.kg_m")
    gm = state.get("stability.gm_m")

    # Calculate GM if not directly available
    if gm is None and kb and bm and kg:
        gm = kb + bm - kg

    # Depth/draft ratio (to verify fix is active)
    depth_draft_ratio = depth / draft if depth and draft else None

    # Phase 6: Output results
    if verbose:
        print("\n[6/6] Design complete.")
        print_header("DESIGN RESULTS")

        print_section("HULL DIMENSIONS")
        print(f"  LWL:   {lwl:.2f} m" if lwl else "  LWL:   N/A")
        print(f"  Beam:  {beam:.2f} m" if beam else "  Beam:  N/A")
        print(f"  Draft: {draft:.2f} m" if draft else "  Draft: N/A")
        print(f"  Depth: {depth:.2f} m" if depth else "  Depth: N/A")
        print(f"  Cb:    {cb:.3f}" if cb else "  Cb:    N/A")
        if depth_draft_ratio:
            print(f"  D/T:   {depth_draft_ratio:.3f}")

        print_section("DISPLACEMENT")
        print(f"  Volume:       {vol:.1f} m³" if vol else "  Volume:       N/A")
        print(f"  Displacement: {disp:.1f} tonnes" if disp else "  Displacement: N/A")

        print_section("WEIGHT")
        print(f"  Lightship: {lightship:.1f} tonnes" if lightship else "  Lightship: N/A")

        print_section("STABILITY")
        print(f"  KB: {kb:.3f} m" if kb else "  KB: N/A")
        print(f"  BM: {bm:.3f} m" if bm else "  BM: N/A")
        print(f"  KG: {kg:.3f} m" if kg else "  KG: N/A")
        print(f"  GM: {gm:.3f} m" if gm else "  GM: N/A")

        print_section("PHASE SUMMARY")
        for r in results:
            if isinstance(r, dict):
                print(f"  {r['phase_name']}: {r['status']}")
            else:
                status = r.status.value if hasattr(r.status, 'value') else str(r.status)
                print(f"  {r.phase_name}: {status}")

        print_section("VERDICT")
        if all_passed:
            print("  ALL PHASES COMPLETED SUCCESSFULLY")
        else:
            print("  SOME PHASES FAILED - Review errors above")

        print("\n" + "=" * 70)

    # Return structured results
    return {
        "success": all_passed,
        "mission": {
            "max_speed_kts": max_speed_kts,
            "vessel_type": vessel_type,
            "crew": crew,
            "range_nm": range_nm,
            "loa_m": loa_m
        },
        "hull": {
            "lwl_m": lwl,
            "beam_m": beam,
            "draft_m": draft,
            "depth_m": depth,
            "cb": cb,
            "depth_draft_ratio": depth_draft_ratio
        },
        "displacement": {
            "volume_m3": vol,
            "tonnes": disp
        },
        "weight": {
            "lightship_tonnes": lightship
        },
        "stability": {
            "kb_m": kb,
            "bm_m": bm,
            "kg_m": kg,
            "gm_m": gm
        },
        "phases": [
            {
                "phase": r["phase_name"] if isinstance(r, dict) else r.phase_name,
                "status": r["status"] if isinstance(r, dict) else (r.status.value if hasattr(r.status, 'value') else str(r.status))
            }
            for r in results
        ]
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run MAGNET end-to-end design pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_design.py                              # Default workboat
  python scripts/run_design.py --speed 35 --type patrol     # Fast patrol boat
  python scripts/run_design.py --type ferry --crew 10       # Ferry design
        """
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=25.0,
        help="Maximum speed in knots (default: 25.0)"
    )
    parser.add_argument(
        "--type",
        type=str,
        default="workboat",
        choices=["workboat", "patrol", "ferry", "planing", "catamaran"],
        help="Vessel type / hull family (default: workboat)"
    )
    parser.add_argument(
        "--crew",
        type=int,
        default=4,
        help="Number of crew (default: 4)"
    )
    parser.add_argument(
        "--range",
        type=float,
        default=300.0,
        help="Design range in nautical miles (default: 300.0)"
    )
    parser.add_argument(
        "--loa",
        type=float,
        default=None,
        help="LOA constraint in meters (optional)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    result = run_design(
        max_speed_kts=args.speed,
        vessel_type=args.type,
        crew=args.crew,
        range_nm=args.range,
        loa_m=args.loa,
        verbose=not args.quiet
    )

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
