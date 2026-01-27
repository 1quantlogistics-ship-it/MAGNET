# CORTEX: Generative Design Theory

**Subtitle:** How LLMs Create Complete Physical Artifacts Through Recursive Decomposition

**Version:** 1.0  
**Status:** Working Theory  
**Author:** Ben / MAGNET Project  
**Date:** January 2026

---

## First-Principles Summary

Generative design is constraint satisfaction through recursive decomposition.

- **High-level intent decomposes into sub-problems**
- **Sub-problems decompose until you reach placeable atoms**
- **Atoms are placed, validated, and committed**
- **Validation propagates back up the hierarchy**

The LLM is the architect — it reasons about what and why.  
The kernel is the engineer — it computes how and validates.  
The loop continues until the design is complete and valid.

**This is not different from agentic web design. It's the same pattern in 3D with physics.**

---

## Part I: What Is Design?

### 1.1 The Universal Design Process

Every design problem follows the same structure:

```
Intent
  → Decompose into sub-problems
    → Decompose further
      → Until you hit atoms you can place
        → Place atoms
        → Validate locally
      → Validate sub-assembly
    → Validate system
  → Validate whole
Complete
```

This is true for:
- Web pages (intent → sections → components → elements)
- Vessels (intent → systems → components → fittings)
- Buildings (intent → floors → rooms → elements)
- Circuits (intent → subsystems → components → traces)
- Molecules (intent → scaffolds → fragments → atoms)

### 1.2 Web Design as Existence Proof

Web design agents work today. They:

```
"Build me a landing page for a SaaS product"
    ↓
Decompose: Hero, features, pricing, testimonials, CTA, footer
    ↓
Each section: What components? What layout?
    ↓
Hero: Headline (48px, bold), subhead (18px), image (16:9), button (primary)
    ↓
Place elements, apply styles
    ↓
Validate: Contrast ok? Hierarchy clear? Mobile works?
    ↓
Iterate until done
```

**Why this works:**
1. Atoms are well-defined (div, span, img, button)
2. Composition rules are known (flexbox, grid)
3. Validation is fast (render and check)
4. Undo is trivial (regenerate)

### 1.3 Physical Design Has the Same Structure

```
"Build me a 72-foot sportfisher, 400nm range, 6 passengers"
    ↓
Decompose: Hull, propulsion, fuel, electrical, accommodations
    ↓
Fuel system: What components? What routing?
    ↓
Components: Tank (400gal, frame 12-18), fill (gunwale, station 15), filter, lines
    ↓
Place components, route connections
    ↓
Validate: Capacity ok? No air locks? Accessible? No clashes?
    ↓
Iterate until done
```

**Same pattern. Different atoms. Different validation.**

---

## Part II: The Recursive Agent Architecture

### 2.1 Design Levels

Physical design naturally stratifies into levels:

| Level | Name | Input | Output | Validates |
|-------|------|-------|--------|-----------|
| 0 | **Mission** | User intent, requirements | System requirements, space allocation | Feasibility |
| 1 | **Systems** | Requirements from L0 | System specs, major component zones | Systems don't conflict |
| 2 | **Components** | System specs from L1 | Component instances, positions | Clearances, access, support |
| 3 | **Routing** | Components from L2 | Paths, fittings, penetrations | No collisions, valid geometry |
| 4 | **Details** | Routes from L3 | Hangers, supports, labels, panels | Installable, serviceable |

### 2.2 Level Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│                         LEVEL 0: MISSION                         │
│  "72-foot sportfisher, 400nm range, 6 passengers, 30kt cruise"  │
│                                                                  │
│  Outputs:                                                        │
│  - Fuel requirement: ~800 gal                                    │
│  - Accommodation: 3 cabins                                       │
│  - Engine: ~1500hp total                                         │
│  - Space budget: {engine_room: 15%, tanks: 12%, accom: 40%...}  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LEVEL 1: SYSTEMS                          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   Hull   │ │Propulsion│ │   Fuel   │ │Electrical│ ...       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  Each system receives:                                           │
│  - Space allocation                                              │
│  - Performance requirements                                      │
│  - Interface points to other systems                            │
│                                                                  │
│  Each system outputs:                                            │
│  - Component list with rough positions                          │
│  - Connection requirements                                       │
│  - Weight and power budgets                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LEVEL 2: COMPONENTS                         │
│                                                                  │
│  Fuel System Components:                                         │
│  - Tank 1: 400gal, frames 12-18, centerline                     │
│  - Tank 2: 400gal, frames 12-18, centerline (split)             │
│  - Fill port (stbd): gunwale, station 15                        │
│  - Fill port (port): gunwale, station 15                        │
│  - Vent fitting: hull side, above WL                            │
│  - Fuel filter: engine room, accessible                         │
│  - Fuel shutoff: engine room, near tanks                        │
│                                                                  │
│  Validates: Clearances, structural support, access              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LEVEL 3: ROUTING                           │
│                                                                  │
│  Fuel lines:                                                     │
│  - Fill (stbd) → Tank 1: 1.5" ID, 2.3m, 3 fittings             │
│  - Fill (port) → Tank 2: 1.5" ID, 2.1m, 2 fittings             │
│  - Tank 1 → Filter: 0.5" ID, 3.7m, anti-siphon valve           │
│  - Filter → Engine 1: 0.5" ID, 1.2m                             │
│  - Vent loop: 0.75" ID, rises 300mm above tank top             │
│                                                                  │
│  Validates: No collisions, bend radii, proper slope             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LEVEL 4: DETAILS                          │
│                                                                  │
│  - Hanger at frame 14 (fuel supply)                             │
│  - Hanger at frame 16 (fuel supply)                             │
│  - P-clamp at filter mount                                       │
│  - Label: "FUEL SUPPLY - GASOLINE"                              │
│  - Access panel: 12"x12" at filter location                     │
│                                                                  │
│  Validates: Installable sequence, serviceable, labeled          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Validation Propagation

Validation flows both down and up:

**Downward (constraints):**
- Level 0 constrains Level 1 (space budgets, weight limits)
- Level 1 constrains Level 2 (component zones, interface points)
- Level 2 constrains Level 3 (endpoints, keep-out zones)
- Level 3 constrains Level 4 (support points, access requirements)

**Upward (verification):**
- Level 4 confirms: "This is installable"
- Level 3 confirms: "Routes don't clash"
- Level 2 confirms: "Components fit and are accessible"
- Level 1 confirms: "System meets requirements"
- Level 0 confirms: "Mission achieved"

### 2.4 Iteration Within and Across Levels

When validation fails, iteration occurs:

**Within level:** Adjust placement, try alternative routing
**Across levels:** Escalate constraint violation, request more space/budget

```
Level 3: "Cannot route fuel vent without collision"
    ↑
Level 2: "Move fuel filter 100mm aft"
    ↓
Level 3: [re-route succeeds]
```

```
Level 2: "Cannot fit specified tank in allocated space"
    ↑
Level 1: "Reduce tank capacity or expand fuel zone"
    ↑
Level 0: "Accept reduced range (350nm) or lengthen vessel"
    ↓
[User decision]
```

---

## Part III: The LLM's Role at Each Level

### 3.1 What LLMs Are Good At

| Capability | Application in Design |
|------------|----------------------|
| **Pattern recognition** | "This looks like a center console layout" |
| **Requirements interpretation** | "400nm range at 30kt means ~800gal fuel" |
| **Trade-off reasoning** | "More tankage means less accommodation" |
| **Constraint specification** | "Filter must be accessible and before engine" |
| **Review and critique** | "This routing passes too close to exhaust" |
| **Natural language interface** | "Move the fill port closer to the dock side" |

### 3.2 What LLMs Cannot Do

| Limitation | Implication |
|------------|-------------|
| **3D spatial reasoning from coordinates** | Cannot generate valid paths from numbers |
| **Precise geometric computation** | Cannot compute clearances, volumes, angles |
| **Collision detection** | Cannot verify non-intersection |
| **Physics simulation** | Cannot verify flow, structural, thermal |
| **Optimization** | Cannot search large solution spaces efficiently |

### 3.3 The Division of Labor

| Task | LLM | Kernel |
|------|-----|--------|
| Interpret requirements | ✅ | |
| Decompose into systems | ✅ | |
| Select patterns/templates | ✅ | |
| Specify constraints | ✅ | |
| Generate placement | | ✅ (constraint solver) |
| Generate routing | | ✅ (pathfinding) |
| Validate geometry | | ✅ (clash detection) |
| Validate physics | | ✅ (domain solvers) |
| Review results | ✅ (via vision) | |
| Accept/reject/modify | ✅ | |
| Explain decisions | ✅ | |

---

## Part IV: The Kernel's Algorithms

The kernel provides the computational capabilities the LLM lacks.

### 4.1 Space Allocation (Level 0-1)

**Problem:** Divide available volume among competing systems

**Algorithms:**
- Bin packing (3D)
- Constraint satisfaction (CSP)
- Linear programming (for optimization)

**LLM role:** Specify requirements, priorities, accept/reject allocation

```python
# LLM specifies
allocation_request = {
    "total_volume": 150,  # m³
    "systems": {
        "fuel": {"min": 15, "max": 25, "priority": "high"},
        "engine_room": {"min": 20, "max": 30, "priority": "required"},
        "accommodation": {"min": 50, "max": 70, "priority": "medium"},
    },
    "constraints": [
        "fuel.adjacent_to(engine_room)",
        "accommodation.not_adjacent_to(engine_room)",
    ]
}

# Kernel computes
allocation_result = space_allocator.solve(allocation_request)
# Returns: zone boundaries, volumes, satisfaction status
```

### 4.2 Component Placement (Level 2)

**Problem:** Position components within allocated zones

**Algorithms:**
- Constraint satisfaction
- Physics simulation (for settling)
- Genetic algorithms (for optimization)

**LLM role:** Specify components, constraints, preferences

```python
# Tool: request_placement
{
    "name": "request_placement",
    "input_schema": {
        "component": "fuel_tank_1",
        "zone": "fuel_zone_aft",
        "constraints": {
            "min_clearance_hull": 0.05,
            "min_clearance_above": 0.3,
            "orientation": "longitudinal",
            "access_side": "top"
        },
        "preferences": {
            "center_in_zone": True,
            "low_as_possible": True
        }
    }
}

# Kernel returns
{
    "position": [7.2, 0.0, -1.4],
    "orientation": [0, 0, 0],
    "clearances": {
        "hull_port": 0.12,
        "hull_stbd": 0.12,
        "above": 0.45,
        "forward": 0.30
    },
    "validation": "pass",
    "conflicts": []
}
```

### 4.3 Routing (Level 3)

**Problem:** Connect components with valid paths

**Algorithms:**
- A* (grid-based pathfinding)
- RRT/RRT* (sampling-based, handles complex constraints)
- PRM (probabilistic roadmap, good for repeated queries)
- Visibility graphs (for 2.5D routing)

**LLM role:** Specify endpoints, preferences, review results

```python
# Tool: request_routing
{
    "name": "request_routing",
    "input_schema": {
        "from_component": "fuel_tank_1",
        "from_port": "outlet",
        "to_component": "fuel_filter_1",
        "to_port": "inlet",
        "system_type": "fuel_supply",
        "constraints": {
            "min_bend_radius": 0.1,  # meters
            "max_length": 5.0,
            "slope_direction": "toward_destination",
            "avoid_zones": ["exhaust_zone", "accommodation"]
        },
        "preferences": {
            "accessibility": "serviceable",
            "follow_structure": True,
            "minimize_fittings": True
        }
    }
}

# Kernel runs pathfinding algorithm
# Returns: path points, fittings required, validation status
```

### 4.4 Clash Detection (Continuous)

**Problem:** Ensure no geometry intersects

**Algorithms:**
- Bounding Volume Hierarchy (BVH)
- Spatial hashing
- GJK/EPA (for precise collision)

**LLM role:** None — kernel does this automatically

```python
# Automatic validation after any placement or routing
def validate_no_clashes(artifact_graph) -> ValidationResult:
    bvh = build_bvh(artifact_graph.all_geometry())
    collisions = bvh.find_all_intersections()
    return ValidationResult(
        passed=len(collisions) == 0,
        collisions=collisions
    )
```

### 4.5 Domain Validation (Level-Specific)

Each domain has specific validation:

**Vessel:**
```python
validators = {
    "hydrostatics": validate_floats_and_trim,
    "stability": validate_gz_curve,
    "structural": validate_loads_and_stresses,
    "systems": {
        "fuel": validate_fuel_flow_and_venting,
        "electrical": validate_load_and_protection,
        "hvac": validate_airflow_and_cooling,
    }
}
```

**Building:**
```python
validators = {
    "structural": validate_load_paths,
    "egress": validate_exit_distances,
    "energy": validate_envelope_performance,
    "mep": validate_system_capacity,
}
```

---

## Part V: Domain Libraries

### 5.1 The Pattern Library Concept

LLMs don't invent from scratch. They select and instantiate patterns.

**Web design analogy:**
- Component libraries (shadcn, Radix)
- Layout patterns (hero, grid, sidebar)
- Style systems (Tailwind)

**Physical design equivalent:**
- System templates
- Routing rules
- Component catalogs
- Assembly patterns

### 5.2 System Templates

```python
FUEL_SYSTEM_TEMPLATES = {
    "single_engine_gasoline": {
        "description": "Simple gasoline system for single outboard/sterndrive",
        "components": [
            {"type": "fuel_tank", "quantity": 1},
            {"type": "fuel_fill", "quantity": 1},
            {"type": "fuel_vent", "quantity": 1},
            {"type": "fuel_pickup", "quantity": 1},
            {"type": "water_separator", "quantity": 1},
            {"type": "fuel_line", "subtype": "supply"},
            {"type": "fuel_line", "subtype": "return"},
        ],
        "topology": """
            fill --> tank
            tank --> pickup --> water_sep --> engine
            engine --> return --> tank
            tank --> vent --> hull_fitting
        """,
        "rules": [
            "tank_below_fill",
            "vent_highest_point",
            "antisiphon_required",
            "return_above_pickup",
        ]
    },
    
    "twin_diesel": {
        "description": "Diesel system for twin engine configuration",
        "components": [
            {"type": "fuel_tank", "quantity": 2, "config": "split"},
            {"type": "fuel_fill", "quantity": 2},
            {"type": "fuel_vent", "quantity": 2},
            {"type": "fuel_manifold", "quantity": 1},
            {"type": "primary_filter", "quantity": 2},
            {"type": "secondary_filter", "quantity": 2},
            {"type": "fuel_cooler", "quantity": 2},
        ],
        "topology": """
            fill_p --> tank_p --> manifold
            fill_s --> tank_s --> manifold
            manifold --> primary_1 --> secondary_1 --> engine_1
            manifold --> primary_2 --> secondary_2 --> engine_2
            engine_1 --> cooler_1 --> return --> manifold
            engine_2 --> cooler_2 --> return --> manifold
        """,
        "rules": [
            "cross_feed_capability",
            "filter_duplex_or_accessible",
            "day_tank_optional",
        ]
    }
}
```

### 5.3 Routing Rules

```python
ROUTING_RULES = {
    "fuel_supply": {
        "min_bend_radius_factor": 3,  # 3x pipe OD
        "max_unsupported_span": 1.0,  # meters
        "slope_for_drain": 0.02,  # 2% grade
        "fitting_at_direction_change": True,
        "material": "USCG_approved_A1",
        "clearance_from_exhaust": 0.2,
        "penetration_requires": "grommet_or_fitting",
    },
    
    "fuel_vent": {
        "must_rise_continuously": True,
        "loop_above_tank_top": 0.3,  # meters
        "terminate_outside_hull": True,
        "screen_required": True,
    },
    
    "exhaust_wet": {
        "min_slope_to_exit": 0.04,
        "water_injection_distance": 0.5,
        "insulation_before_injection": True,
        "clearance_from_combustible": 0.1,
    },
    
    "electrical_dc": {
        "max_voltage_drop": 0.03,  # 3%
        "support_interval": 0.5,
        "bundling_allowed": True,
        "separation_from_fuel": 0.05,
        "chafe_protection_at_penetration": True,
    }
}
```

### 5.4 Component Catalogs

```python
COMPONENT_CATALOG = {
    "fuel_tank_aluminum": {
        "material": "5052-H32",
        "shapes": ["rectangular", "L-shaped", "custom"],
        "capacity_range": [50, 2000],  # gallons
        "baffles_required_above": 75,  # gallons
        "ports": ["fill", "vent", "supply", "return", "sender", "drain"],
        "mounting": ["saddle", "strap", "flange"],
        "certification": ["USCG", "ABYC_H-33"],
    },
    
    "fuel_filter_racor": {
        "models": {
            "230R": {"flow_gph": 30, "port_size": 0.25},
            "500FG": {"flow_gph": 60, "port_size": 0.375},
            "900FG": {"flow_gph": 90, "port_size": 0.5},
            "1000FG": {"flow_gph": 180, "port_size": 0.75},
        },
        "mounting": "bracket_vertical",
        "service_clearance": {"below": 0.15, "forward": 0.1},
    }
}
```

### 5.5 How LLM Uses Libraries

```
User: "Design the fuel system for a 45-foot sportfish with twin Caterpillar C12s"

LLM:
  1. Recognizes: twin diesel configuration
  2. Selects template: "twin_diesel"
  3. Sizes components: 
     - Tanks: 2x 400gal (800 total for range requirement)
     - Filters: Racor 1000FG (matches C12 flow)
  4. Specifies placement constraints:
     - Tanks in fuel zone amidships
     - Filters in engine room, accessible
  5. Requests kernel execution
  
Kernel:
  1. Instantiates template
  2. Places components per constraints
  3. Routes per ROUTING_RULES
  4. Validates per FUEL_SYSTEM_VALIDATORS
  5. Returns result with views
  
LLM:
  1. Reviews views
  2. Accepts or requests modifications
```

---

## Part VI: The Agent Loop for Generative Design

### 6.1 Tools for Generative Design

```python
GENERATIVE_DESIGN_TOOLS = [
    # Level 0-1: Mission & Systems
    {
        "name": "decompose_requirements",
        "description": "Break down mission into system requirements",
        "inputs": ["mission_statement", "constraints"],
        "outputs": ["system_requirements", "space_budget", "weight_budget"]
    },
    {
        "name": "allocate_spaces",
        "description": "Allocate zones for systems",
        "inputs": ["hull_envelope", "system_requirements", "adjacency_rules"],
        "outputs": ["zone_definitions", "interface_points"]
    },
    
    # Level 2: Components
    {
        "name": "select_template",
        "description": "Select a system template",
        "inputs": ["system_type", "configuration", "requirements"],
        "outputs": ["template_id", "component_list", "topology"]
    },
    {
        "name": "request_placement",
        "description": "Place a component in the design",
        "inputs": ["component_id", "zone", "constraints", "preferences"],
        "outputs": ["position", "orientation", "clearances", "validation"]
    },
    
    # Level 3: Routing
    {
        "name": "request_routing",
        "description": "Route a connection between components",
        "inputs": ["from_port", "to_port", "system_type", "constraints", "preferences"],
        "outputs": ["path", "fittings", "length", "validation"]
    },
    {
        "name": "request_routing_batch",
        "description": "Route multiple connections for a system",
        "inputs": ["system_id", "topology", "constraints"],
        "outputs": ["all_routes", "bill_of_materials", "validation"]
    },
    
    # Level 4: Details
    {
        "name": "add_supports",
        "description": "Add hangers/supports to routes",
        "inputs": ["route_id", "support_rules"],
        "outputs": ["support_locations", "support_types"]
    },
    {
        "name": "add_labels",
        "description": "Add identification labels",
        "inputs": ["system_id", "labeling_standard"],
        "outputs": ["label_locations", "label_text"]
    },
    
    # Vision
    {
        "name": "request_view",
        "description": "Render current state",
        "inputs": ["focus", "scope", "annotations", "view_angle"],
        "outputs": ["image"]
    },
    
    # Validation
    {
        "name": "validate_system",
        "description": "Run full validation on a system",
        "inputs": ["system_id"],
        "outputs": ["validation_results", "issues", "suggestions"]
    },
    
    # Commit
    {
        "name": "commit_design",
        "description": "Commit current state to design history",
        "inputs": ["description"],
        "outputs": ["version_id", "snapshot"]
    }
]
```

### 6.2 The Generative Loop

```python
def generative_design_agent(
    mission: str,
    hull_geometry: ArtifactGraph,
    max_iterations: int = 100
) -> DesignResult:
    
    messages = [{"role": "user", "content": f"""
Design a complete vessel based on this mission:
{mission}

The hull geometry is provided. Design all systems:
1. Fuel system
2. Electrical system
3. Propulsion system
4. Fresh water system
5. Waste system
6. HVAC system
7. Accommodations layout

For each system:
- Select appropriate template
- Place components
- Route connections
- Validate
- Iterate until valid

Use the tools provided. Request views to verify your work.
Start with Level 0 (space allocation) and work down.
"""}]
    
    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=GENERATIVE_DESIGN_SYSTEM_PROMPT,
            tools=GENERATIVE_DESIGN_TOOLS,
            messages=messages
        )
        
        if response.stop_reason == "tool_use":
            results = execute_tools(response.tool_calls, hull_geometry)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
            
        elif response.stop_reason == "end_turn":
            # Check if design is complete
            if "DESIGN COMPLETE" in response.content[0].text:
                return extract_design_result(hull_geometry)
            else:
                # Continue
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": "Continue with the design."})
    
    return DesignResult(status="max_iterations", partial=hull_geometry)
```

### 6.3 System Prompt for Generative Design

```markdown
You are a naval architect designing complete vessel systems.

## Your Process

1. **Understand the mission** - Range, speed, passengers, purpose
2. **Allocate space** - Divide hull volume among systems
3. **Design each system** - Work through fuel, electrical, plumbing, HVAC
4. **For each system:**
   - Select the appropriate template
   - Size components for the requirements
   - Place components respecting constraints
   - Route all connections
   - Validate the system
   - Iterate until valid

## Rules

- Always request_view after major placements to verify visually
- Never guess coordinates - use request_placement and request_routing
- Validate systems before moving to the next
- If validation fails, understand why before retrying
- Respect the routing rules for each system type

## System Order

Design in this order (dependencies flow down):
1. Fuel (tanks and fills drive space)
2. Propulsion (engines drive alignment)
3. Electrical (panels, runs to major loads)
4. Fresh water (tanks, pumps, distribution)
5. Waste (holding, treatment, discharge)
6. HVAC (units, ducting)
7. Accommodations (furniture, fixtures)

## Completion

When all systems are designed, validated, and you are satisfied:
- Request a final full-vessel view
- Run validate_system on each system
- If all pass, respond with "DESIGN COMPLETE"

Begin.
```

---

## Part VII: Handling Complexity

### 7.1 Hierarchical Scoping

Large artifacts (cruise ships, buildings) have too many components to show at once.

**Solution:** Hierarchical scope in all queries and views.

```
Scope hierarchy:
vessel
  └── deck_7
        └── zone_forward
              └── cabin_7042
                    └── hvac_outlet_3

# Views respect scope
request_view(focus="deck_7", scope="deck") → deck plan
request_view(focus="cabin_7042", scope="local_3m") → cabin detail
request_view(focus="hvac_outlet_3", scope="local_0.5m") → outlet detail
```

### 7.2 Parallel System Design

Systems can be designed in parallel if they don't conflict:

```
Phase 1 (sequential): Space allocation - establishes zones
Phase 2 (parallel): 
  - Fuel system design (in fuel zone)
  - Electrical design (throughout, but non-conflicting)
  - Fresh water design (in utility zones)
Phase 3 (sequential): Integration - resolve conflicts
Phase 4 (parallel): Details for each system
```

### 7.3 Conflict Resolution

When systems conflict:

```
Kernel detects: "Fuel line clashes with electrical conduit at frame 12"

Options:
1. Re-route fuel (request_routing with avoid constraint)
2. Re-route electrical (request_routing with avoid constraint)
3. Stack vertically (add offset constraint)
4. Request penetration (if through bulkhead)

LLM decides based on:
- Which system is more constrained
- Which has more routing flexibility
- Code requirements (fuel/electrical separation)
```

### 7.4 Iteration Bounds

Prevent infinite loops:

```python
ITERATION_LIMITS = {
    "placement_attempts": 5,      # Tries to place one component
    "routing_attempts": 3,        # Tries to route one connection
    "system_iterations": 10,      # Total iterations on one system
    "integration_passes": 3,      # Cross-system conflict resolution
}

# Escalation on limit hit
if placement_attempts >= 5:
    escalate("Cannot place {component} in {zone}. Need: larger zone, smaller component, or relaxed constraints")
```

---

## Part VIII: Validation Throughout

### 8.1 Validation Levels

| Level | What's Validated | When | Blocking? |
|-------|------------------|------|-----------|
| **Geometry** | No clashes, valid shapes | Every placement/route | Yes |
| **System** | Flows, pressures, loads | After system complete | Yes |
| **Integration** | Cross-system conflicts | After all systems | Yes |
| **Regulatory** | Class rules, standards | Final validation | Yes |
| **Quality** | Accessibility, serviceability | Final review | No (warnings) |

### 8.2 Validation Pipeline

```python
def full_validation(design: ArtifactGraph) -> ValidationReport:
    report = ValidationReport()
    
    # Level 1: Geometry (fast, always run)
    report.geometry = validate_geometry(design)
    if not report.geometry.passed:
        return report  # Stop early
    
    # Level 2: Each system
    for system in design.systems:
        report.systems[system.id] = validate_system(system)
    
    if any(not r.passed for r in report.systems.values()):
        return report  # Stop early
    
    # Level 3: Integration
    report.integration = validate_integration(design)
    if not report.integration.passed:
        return report
    
    # Level 4: Regulatory
    report.regulatory = validate_regulatory(design)
    
    # Level 5: Quality (non-blocking)
    report.quality = validate_quality(design)
    
    return report
```

### 8.3 Validation Feedback to LLM

```python
# After validation, format for LLM understanding
def format_validation_for_llm(report: ValidationReport) -> str:
    if report.all_passed():
        return "✅ All validations passed."
    
    output = "Validation issues:\n\n"
    
    for issue in report.all_issues():
        output += f"""
❌ {issue.severity}: {issue.title}
   Location: {issue.location}
   Details: {issue.details}
   Suggestion: {issue.suggestion}
"""
    
    return output
```

---

## Part IX: The Comparison

### 9.1 Web Design vs Physical Design

| Aspect | Web Design Agent | Physical Design Agent |
|--------|------------------|----------------------|
| **Atoms** | DOM elements (div, button, img) | Physical components (tank, pipe, fitting) |
| **Composition** | CSS layout (flex, grid) | 3D spatial + routing algorithms |
| **Validation** | Render + screenshot | Physics + clash detection |
| **Iteration speed** | Milliseconds | Seconds (pathfinding, physics) |
| **Failure mode** | Ugly but functional | Non-functional or dangerous |
| **Libraries** | shadcn, Tailwind | System templates, routing rules |
| **LLM strength** | Aesthetic judgment | System architecture |
| **Kernel strength** | DOM manipulation | Pathfinding, physics simulation |

### 9.2 What Makes Physical Design Harder

1. **3D pathfinding with constraints** — Not a capability LLMs have
2. **Physics validation** — Requires domain solvers
3. **Manufacturing constraints** — Bend radii, weld access, install sequence
4. **Regulatory compliance** — Complex rule sets
5. **Consequence severity** — Bad CSS looks ugly; bad piping sinks boats

### 9.3 What Makes It Tractable

1. **Decomposition works** — Same pattern as web design
2. **Patterns exist** — System templates, routing rules
3. **Validation is computable** — Algorithms exist
4. **LLM strengths apply** — Requirements interpretation, trade-offs, review
5. **Kernel handles the hard parts** — Pathfinding, physics, optimization

---

## Part X: Implementation Roadmap

### Phase 1: Single System (Fuel)
- Implement fuel system templates
- Implement routing for fuel lines
- Implement fuel system validation
- **Proves:** One system can be generated

### Phase 2: Multiple Independent Systems
- Add electrical, fresh water, waste
- Parallel design for non-conflicting systems
- **Proves:** Multiple systems work

### Phase 3: System Integration
- Conflict detection across systems
- Resolution strategies
- Integrated validation
- **Proves:** Systems coexist

### Phase 4: Full Vessel
- All systems including HVAC, accommodations
- Hierarchical scoping for complexity
- Full regulatory validation
- **Proves:** Complete designs possible

### Phase 5: Generalization
- Abstract system templates
- Pluggable validators
- Other domains (buildings, appliances)
- **Proves:** Pattern is general

---

## Conclusion

Generative design by LLMs is not impossible. It's the same pattern as web design:

**Decompose → Pattern-match → Instantiate → Validate → Iterate**

The differences are:
- Different atoms (components vs DOM)
- Different composition (3D routing vs CSS)
- Different validation (physics vs render)

But the agent architecture is identical:
- LLM reasons about **what** and **why**
- Kernel computes **how** and validates
- Vision closes the loop
- Libraries provide patterns
- Iteration handles errors

**You're not doing something new. You're doing web design in 3D with physics.**

The kernel needs:
- Pathfinding algorithms
- Clash detection
- Domain solvers
- Pattern libraries

The LLM needs:
- Vision (to see results)
- Tools (to request operations)
- Domain knowledge (in prompts and libraries)

When you have both, you can generate complete physical artifacts.

---

*End of document.*
