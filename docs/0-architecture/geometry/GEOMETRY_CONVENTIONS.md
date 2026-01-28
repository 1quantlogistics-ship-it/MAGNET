# MAGNET Geometry Conventions

<!-- AGENT_CONTEXT
Purpose: Canonical coordinate system and geometry conventions for all MAGNET modules
Authoritative: Yes
Depends_On: None
Used_By: hull_gen, webgl, physics, agents, kernel
Last_Verified: 2026-01-14
-->

## Overview

This document defines the **MAGNET Standard** coordinate system and geometry conventions. All modules MUST conform to these conventions. Any deviation is a bug.

---

## Coordinate System (Naval Architecture Standard)

MAGNET uses a **right-handed coordinate system** with origin at the intersection of:
- After Perpendicular (AP)
- Centerline (CL)
- Baseline (BL)

| Axis | Direction | Origin | Positive |
|------|-----------|--------|----------|
| **X** | Longitudinal | AP (stern) | Forward (toward bow) |
| **Y** | Transverse | Centerline | **Port** (left when facing forward) |
| **Z** | Vertical | Baseline | Up (toward sky) |

### Mathematical Verification

The system is right-handed:
```
X × Y = Z
```
Where:
- X = Forward (bow direction)
- Y = Port (left side)
- Z = Up

### Key Values

| Location | X Value | Y Value | Z Value |
|----------|---------|---------|---------|
| AP (stern) | 0 | 0 | varies |
| FP (bow) | LOA | 0 | varies |
| Centerline | varies | 0 | varies |
| Port side | varies | > 0 | varies |
| Starboard side | varies | < 0 | varies |
| Baseline | varies | varies | 0 |
| Waterline | varies | varies | draft |
| Main deck | varies | varies | depth |

---

## Station Convention

Stations are normalized positions along the hull length.

| Value | Location | X Position |
|-------|----------|------------|
| station = 0.0 | AP (stern) | x = 0 |
| station = 0.5 | Midship | x = LOA / 2 |
| station = 1.0 | FP (bow) | x = LOA |

**Formula:**
```python
x_position = station * LOA
station = x_position / LOA
```

---

## Section Point Ordering

Section points are ordered from **keel to deck** (Z increasing).

```
Point Index:  0    1    2    3    4    ...   N
              ↑    ↑    ↑    ↑    ↑          ↑
           Keel  ...  Chine ...  ...      Sheer
        (lowest Z)                    (highest Z)
```

### Half-Hull Convention

- Sections store **port side only** (Y ≥ 0)
- Tessellation mirrors to starboard (Y < 0)
- Centerline points (Y = 0) are shared, not duplicated

### Point Requirements

| Requirement | Value | Reason |
|-------------|-------|--------|
| Minimum points | 12 | Adequate resolution for fair curves |
| Recommended points | 16-32 | Balance of quality and performance |
| Maximum points | 128 | Performance limit |

---

## Edge Types

| Type | Meaning | Rendering |
|------|---------|-----------|
| `smooth` | Fair curve through point | Averaged normals |
| `hard` | Discontinuity (chine) | Split normals |
| `crease` | Conditional hard edge | Split if angle > threshold |

---

## Multi-Body Offsets

For multi-hull vessels (catamarans, trimarans):

| Offset | Direction | Example |
|--------|-----------|---------|
| `offset_x_m` | Longitudinal from parent | Bow offset for amas |
| `offset_y_m` | Transverse from centerline | Hull spacing |
| `offset_z_m` | Vertical from baseline | Raised hulls |

**Convention:**
- Positive `offset_y_m` = port side
- Negative `offset_y_m` = starboard side
- Child body coordinates are **local**; transform applied at attachment

**Example (Catamaran):**
```python
port_hull = Body(offset_y_m=+5.0)   # 5m to port
stbd_hull = Body(offset_y_m=-5.0)   # 5m to starboard
```

---

## Face Winding

Triangle faces use **counter-clockwise (CCW)** winding when viewed from outside the hull.

```
     v2
    /  \
   /    \
  v0----v1
  
CCW order: [v0, v1, v2]
Normal points OUT of hull
```

---

## Vertical Datum

| Datum | Z Value | Use |
|-------|---------|-----|
| **Baseline** | Z = 0 | **Primary datum** (static) |
| Waterline | Z = draft | Variable (depends on loading) |
| Main Deck | Z = depth | Variable (depends on design) |

**Critical:** Z = 0 is ALWAYS the baseline, never the waterline. The waterline position is a state variable (`hull.draft`), not a datum.

---

## Unit System

All dimensions are in **SI units (meters)**.

| Quantity | Unit | Example |
|----------|------|---------|
| Length | meters (m) | LOA = 25.0 |
| Area | square meters (m²) | Awp = 45.0 |
| Volume | cubic meters (m³) | ∇ = 120.0 |
| Angle | degrees (°) | deadrise = 20.0 |
| Mass | metric tons (MT) | displacement = 150.0 |

---

## Mirror Operation Invariant

The mirror operation MUST be involutive (applying twice returns identity):

```python
assert mirror(mirror(point)) == point  # Bitwise identical
```

This prevents asymmetry drift in multi-pass operations.

---

## Validation

To verify a module conforms to MAGNET Standard:

```bash
# Check Y-axis convention (should all say "port")
grep -n "positive.*port\|Y.*port" <file>

# Check for violations (should return empty)
grep -n "positive.*starboard\|Y.*starboard" <file>

# Check Z datum (should say "baseline", not "waterline")
grep -n "Z.*=.*0" <file>
```

---

## Migration Notes

The following files had conflicting conventions and were updated to MAGNET Standard:

| File | Original | Updated |
|------|----------|---------|
| `hull_gen/geometry.py` | Y+ = Starboard | Y+ = Port |
| `weight/items.py` | Y+ = Starboard | Y+ = Port |
| `interior/section_sampler.py` | Y+ = Starboard | Y+ = Port |
| `agents/geometry_proposer.py` | Z=0 at Waterline | Z=0 at Baseline |

---

## References

- Naval Architecture Standard: SNAME conventions
- Right-hand rule: Standard mathematical convention
- Half-hull modeling: Industry standard for symmetric vessels

---

> **Warning:** Any module that deviates from these conventions will produce incorrect geometry, physics, or renders. There are no exceptions.
