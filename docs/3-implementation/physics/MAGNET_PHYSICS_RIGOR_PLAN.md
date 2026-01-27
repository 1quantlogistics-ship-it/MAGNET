# MAGNET Physics Rigor & Primitives Upgrade Plan

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, physics, rigor, plan]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Version:** 1.0  
**Status:** Implementation Roadmap  
**Target:** Transition from Operational Prototype to Scientifically Defensible Kernel  
**Reference:** `../theory/MAGNET_UNIFIED_PHYSICS_THEORY.md` (v2.5)

---

## 🎯 Objectives

1.  **Numerical Rigor:** Upgrade longitudinal integration from Trapezoidal to **Simpson's 1/3 Rule**.
2.  **Polygon Integrity:** Implement **Sutherland-Hodgman Waterline Clipping** for precise submerged area/centroid calculation.
3.  **Universal Primitives:** Support `opening`, `flow_path`, and `attachment` in the compiler and physics stack.
4.  **Human Decision Point:** Implement mandatory **Halt logic** in the conductor for severe stability/buoyancy failures.

---

## 🏗️ Phase 1: Numerical Rigor & Polygon Integrity (Kernel Foundation)

*Objective: Ensure area and volume calculations are accurate enough for regulatory submittal.*

### TASK-RIG-001: Sutherland-Hodgman Waterline Clipping
- **Files:** `magnet/physics/geometry_hydrostatics.py`
- **Logic:** Replace simple vertex filtering with true polygon clipping against the plane $Z = draft$.
- **Requirement:** Submerged area must account for the exact intersection points on the hull shell, not just vertices below the line.

### TASK-RIG-002: Simpson's 1/3 Rule Integration
- **Files:** `magnet/physics/geometry_hydrostatics.py`
- **Logic:** 
    - Implement `_integrate_simpsons(values, x_positions)`.
    - Ensure longitudinal integration of Areas ($A_w$), Moments ($M_x$), and Inertia ($I_t, I_l$) uses Simpson's rule.
    - **Constraint:** If section count is even, use Simpson's 3/8 rule for the terminal segment or fallback to Trapezoidal for that specific segment to maintain 1/3 rule rigor elsewhere.

---

## 🏗️ Phase 2: Human Decision Point (Orchestration)

*Objective: Prevent the Agent from proceeding with downstream engineering on physically "broken" designs without human approval.*

### TASK-HALT-001: Conductor Halt Logic
- **Files:** `magnet/kernel/conductor.py`, `magnet/deployment/spiral_endpoints.py`
- **Logic:** 
    - Post-Hydrostatics check: if `HydrostaticsResult.stable == False` OR `freeboard < 0.1m`, set `state.metadata.awaiting_human_decision = True`.
    - Block downstream phases (Resistance, Propulsion, Cost) until `decision_token` is present.
- **API:** Add `POST /api/v1/designs/{id}/decision` endpoint to accept "CONTINUE" or "REVISE" commands.

---

## 🏗️ Phase 3: Universal Primitive Expansion (Features)

*Objective: Support the full "Seven Universal Primitives" defined in the Unified Theory.*

### TASK-PRIM-001: Schema Expansion
- **Files:** `magnet/core/design_state.py`, `magnet/agents/geometry_schema.json`
- **Requirement:** Add resource types for:
    - `geometry.opening`: (x, y, z, diameter) — subtracts volume/buoyancy.
    - `geometry.attachment`: (body_id, transform) — adds weight/buoyancy.
    - `geometry.flow_path`: (waypoints, type) — for skegs/tunnels.

### TASK-PRIM-002: Compiler & Physics Support
- **Files:** `magnet/kernel/stdlib/compiler.py`, `magnet/physics/geometry_hydrostatics.py`
- **Logic:**
    - Compiler must loft `flow_path` as a sub-mesh.
    - Hydrostatics must apply "Lost Buoyancy" method for `opening` primitives.
    - Attachments must contribute to the composite `Parallel Axis Theorem` calculation.

---

## 🚩 Acceptance Criteria

1.  **Integration Accuracy:** `Volume(Simpsons)` vs `Volume(Trapezoidal)` should show a delta of 0.5-1.5% on curvature-heavy hulls (FP/AP).
2.  **Clipping Verification:** A section with only 2 vertices below the waterline and 2 above must produce a closed submerged polygon with **4 vertices** (2 original + 2 intersection points).
3.  **Halt Proof:** Attempting to design a "Weighted Pencil" (VCG > Metacenter) results in a `needs_clarification` response with status `AWAITING_HUMAN_DECISION`.
4.  **Primitive Proof:** A design with a `geometry.opening` shows a corresponding reduction in `displacement_m3` compared to an identical design without the opening.

---

## 🗓️ Estimated Effort (Agent Hours)

| Phase | Task | Effort | Complexity |
|-------|------|--------|------------|
| 1 | Numerical Rigor | 30 hrs | High (Math) |
| 2 | Human Decision Point | 15 hrs | Medium (Logic) |
| 3 | Primitive Expansion | 45 hrs | High (Schema/Mesh) |
| **Total** | | **90 hrs** | |

---

## 📂 File Index

| File | Primary Phase | Impact |
|------|---------------|--------|
| `magnet/physics/geometry_hydrostatics.py` | Phase 1 | Solver Accuracy |
| `magnet/kernel/conductor.py` | Phase 2 | Execution Flow |
| `magnet/core/design_state.py` | Phase 3 | State Schema |
| `magnet/kernel/stdlib/compiler.py` | Phase 3 | 3D Construction |
