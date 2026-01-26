# MAGNET Agent Enhancement Plan

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, agent, enhancement, plan]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Date:** January 6, 2026  
**Status:** 🔴 CRITICAL - Agent lacks domain knowledge  
**Priority:** P0 - Blocks production readiness  
**Effort:** 5 hours (2-3h prompt engineering + 2h testing)

---

## Executive Summary

**THE PROBLEM:** The GeometryProposer agent lacks naval architecture domain knowledge to translate design intent into correct geometry primitives.

**THE GAP:**
- ✅ Kernel validates physics correctly (189/189 tests pass)
- ✅ Geometry primitives are sufficient (7 types, compositional)
- ✅ Architecture is sound (no enumeration)
- ❌ **Agent can't translate "make it faster" → "increase L/B ratio"**
- ❌ **Agent will invent non-existent primitives**
- ❌ **Agent will use enumeration instead of composition**

**THE FIX:** Add Naval Architecture Translation Guide to system prompt (2-3h prompt engineering)

**THE VALIDATION:** Run 12 knowledge tests, target ≥10/12 pass (83%+)

**THE SAFEGUARDS:** Prompt size monitoring, unknown term fallback, ongoing quality monitoring (addresses audit findings)

---

## Part I: Problem Statement

### What Works

```
USER INPUT: "CREATE geometry.body port { offset_y_m: -3.0 }"
         ↓
    AGENT: Parses DSL correctly ✓
         ↓
    KERNEL: Compiles and validates ✓
         ↓
    RESULT: Catamaran demihull created ✓
```

### What Doesn't Work

```
USER INPUT: "I want a catamaran"
         ↓
    AGENT: ❌ Doesn't know catamaran = 2 bodies with lateral offset
         ↓
    AGENT: Sets hull_type = "catamaran" (enumeration) ❌
         ↓
    KERNEL: Rejects (hull_type not in geometry primitives) ❌
         ↓
    RESULT: Failure (user frustrated)
```

### Root Cause

**Current System Prompt** (`magnet/agents/geometry_proposer.py`, lines 24-73):
```python
GEOMETRY_PROPOSER_SYSTEM_PROMPT = """You are MAGNET's Geometry Proposer.

YOUR ROLE:
- Convert design problems into geometry primitives
- Output ONLY geometry.* operations
- NEVER use hull.* types
- Include confidence and reasoning

ALLOWED PRIMITIVES:
- geometry.body
- geometry.section
- geometry.surface
- geometry.discontinuity
- geometry.flow_path
- geometry.opening
- geometry.attachment

RULES:
1. Include reasoning
2. Never output hull.spray_rail, hull.chine
3. Use freeform strings
4. Set confidence < 0.7 if uncertain
5. Output SIMPLEST approach first
"""
```

**Analysis:**
- ✅ Lists primitives
- ✅ Forbids enumeration
- ✅ Requires reasoning
- ❌ **NO naval architecture knowledge**
- ❌ **NO translation guide** (spray rails → discontinuity)
- ❌ **NO physics relationships** (GM = KB + BM - KG)
- ❌ **NO typical values** (L/B ratios, deadrise angles)

**Predicted Test Failure Rate:** ~75% (9/12 tests fail)

---

## Part II: The 12 Knowledge Tests

Tests are implemented in `tests/knowledge/test_agent_naval_architecture_knowledge.py`

### Expected Failures (Without Enhancement)

| Test | Intent | What Agent Needs to Know | Predicted Result |
|:-----|:-------|:------------------------|:-----------------|
| **KNOW_001** | "Make it faster" | L/B ratio affects resistance | ❌ FAIL - Generic response |
| **KNOW_002** | "Add spray rails" | Spray rails = discontinuity at 70% height | ❌ FAIL - Invents primitive |
| **KNOW_003** | "Catamaran" | 2 bodies with lateral spacing | ❌ FAIL - Uses enumeration |
| **KNOW_004** | "More stable" | GM = KB + BM - KG, beam increases BM | ❌ FAIL - Generic advice |
| **KNOW_005** | "Deep-V hull" | High deadrise angle in sections | ❌ FAIL - Invents primitive |
| **KNOW_006** | "Bulbous bow" | Separate body + attachment | ❌ FAIL - Won't compose |
| **KNOW_007** | "Reduce draft" | Draft emergent from sections | ❌ FAIL - Sets parameter |
| **KNOW_008** | "Cigarette boat" | Translate brand → geometry | ❌ FAIL - Refuses or generic |
| **KNOW_009** | "Fuel efficient" | Resistance reduction strategies | ❌ FAIL - Generic advice |
| **KNOW_010** | "Wider stern" | Modify aft stations only | ⚠️ MAYBE - May change globally |
| **KNOW_011** | "Add chines" | Discontinuity or section corners | ❌ FAIL - Invents primitive |
| **KNOW_012** | "3ft seas" | Freeboard, flare, deadrise | ❌ FAIL - No seakeeping knowledge |

**Baseline Prediction:** 2-3 / 12 pass (~20%)

---

## Part III: The Solution

### Required Enhancement: Naval Architecture Translation Guide

**Location:** `magnet/agents/geometry_proposer.py`  
**Current:** Lines 24-73 (50 lines)  
**Enhanced:** Lines 24-~300 (250+ lines)

**Add the following sections to system prompt:**

#### 3.1: Speed & Resistance Translation

```markdown
### SPEED & RESISTANCE

"Make it faster" → Increase L/B ratio
- Current L/B = LOA / Beam
- Target L/B: 6-8 (displacement), 8-12 (planing)
- Higher L/B → Lower wave-making resistance → Higher speed
- Implementation: Reduce beam OR increase length
  - UPDATE geometry.section { ... narrow beam in points ... }

"Reduce resistance" → Multiple strategies
- Fine bow entry (10-15° entry angle)
- Increase L/B ratio
- Reduce wetted surface
- For planing: Add steps or spray rails

"Fuel efficient" → Minimize resistance
- Displacement (Fn < 0.4): Maximize L/B ratio
- Planing (Fn > 1.0): Minimize wetted surface

Typical L/B Ratios:
- Cargo ships: 6-7
- Displacement yachts: 3-4
- Planing boats: 8-12
- Racing yachts: 3.5-4.5
- Catamarans (per hull): 10-15
```

#### 3.2: Stability Translation

```markdown
### STABILITY

"More stable" → Increase GM
- GM = KB + BM - KG (metacentric height)
- BM = I_waterplane / Volume
- To increase GM:
  OPTION A: Increase beam (increases BM)
    - UPDATE geometry.section { ... widen beam ... }
  OPTION B: Lower VCG (center of gravity)
    - CONSTRAIN hull.vcg <= [lower_value]
  OPTION C: Multi-body spacing (if applicable)
    - Parallel axis: I_total = Σ(I_local + A × d²)
    - Wider spacing → higher BM

"GM too low" → Same as above
"Tippy" or "unstable" → Same as above

Multi-body stability:
- BM dominated by parallel axis term
- Hull spacing is critical
- Wider spacing → exponentially higher BM
```

#### 3.3: Hull Forms Translation

```markdown
### HULL FORMS

"Deep-V hull" → High deadrise angle in sections
- Deadrise = angle from horizontal at keel
- Deadrise angle = tan⁻¹(z_chine / y_chine)
- Typical: 20-30° for deep-V
- Example: 24° at 2m half-beam
  - z = 2.0 × tan(24°) = 0.89m
  - Section points: [[0, 0], [2.0, 0.89], [2.0, 1.5], ...]
- UPDATE geometry.section with high-angle points

"Flat bottom" → Low deadrise (0-10°)
"Round bilge" → Smooth curves, no hard corners
"Hard chine" → Sharp transition, addressed in Features

Deadrise Angles:
- Flat bottom: 0-10°
- Moderate V: 12-18°
- Deep V: 20-30°
- Extreme V: 30-45°

Effects:
- Higher deadrise → Better rough-water ride, reduced slamming
- Higher deadrise → Higher draft, more wetted surface
- Lower deadrise → Better planing efficiency, more slamming
```

#### 3.4: Features Translation

```markdown
### FEATURES → GEOMETRY PRIMITIVES

"Add spray rails" → geometry.discontinuity
CREATE geometry.discontinuity spray_rail_port {
  body_id: "main_hull",
  type: "surface_break",
  start_station: 0.2,    // 20% aft of bow
  end_station: 0.7,      // 70% forward of stern
  profile: "longitudinal_edge",
  height_fraction: 0.7,  // 70% up hull side (CRITICAL)
  depth_m: 0.03,         // 20-50mm protrusion
}
- Purpose: Deflect spray, reduce wetted surface at planing speeds
- Must specify height_fraction (0.6-0.8 typical)

"Add chines" → geometry.discontinuity OR sharp section corners
CREATE geometry.discontinuity chine_port {
  body_id: "main_hull",
  type: "hard_edge",
  start_station: 0.2,
  end_station: 0.95,
  profile: "longitudinal_edge",
  height_fraction: 0.6,  // 50-70% up hull side
  depth_m: 0.0,          // Sharp edge, no rounding
}
- Alternative: Create sharp corner in section points
- Location: Bottom/side transition (50-70% hull depth)
- Purpose: Dynamic lift, spray deflection, flow separation

"Add steps" → geometry.discontinuity
CREATE geometry.discontinuity step_1 {
  body_id: "main_hull",
  type: "surface_break",
  start_station: 0.4,
  end_station: 0.5,
  profile: "transverse_step",
  depth_m: 0.15,         // 100-200mm step height
}
- For planing hulls
- Purpose: Air introduction, reduced wetted surface

"Bulbous bow" → geometry.body + geometry.attachment
CREATE geometry.body bow_bulb {
  body_type: "bulbous_bow",
  physics_category: "submerged",
  offset_x_m: -0.5,      // Forward of main bow
  offset_y_m: 0.0,
  offset_z_m: -1.5,      // Below waterline
}
CREATE geometry.attachment bulb_to_hull {
  parent_body_id: "main_hull",
  child_body_id: "bow_bulb",
  attachment_type: "integral",
  ...
}
- Separate body, not hull modification
- Positioned forward and below waterline
- Effective at Fn > 0.2 for displacement vessels
```

#### 3.5: Multi-Body Translation

```markdown
### MULTI-BODY CONFIGURATIONS

"Catamaran" → 2× geometry.body with lateral offset
CREATE geometry.body port_hull {
  body_type: "demihull",
  physics_category: "surface_piercing",
  offset_x_m: 0.0,
  offset_y_m: -10.0,     // Negative = port side
  offset_z_m: 0.0,
}
CREATE geometry.body stbd_hull {
  body_type: "demihull",
  physics_category: "surface_piercing",
  offset_x_m: 0.0,
  offset_y_m: 10.0,      // Positive = starboard side
  offset_z_m: 0.0,
}
- Hull spacing: S/L = 0.35-0.45 typical
  - For LOA=25m: spacing = 0.4 × 25 = 10m
  - offset_y_m = ±5.0m (half-spacing from centerline)
- Demihulls are slender (L/B 10-15 per hull)

"Trimaran" → 3× geometry.body
- Main hull at y=0 (centerline)
- Amas (outriggers) at y=±(0.4-0.5)×LOA
- Amas are smaller, lighter than main

Hull Spacing Guidelines:
- S/L < 0.3: Too narrow (wave interference)
- S/L = 0.35-0.45: Optimal (catamaran)
- S/L > 0.5: Wide (heavy cross-structure loads)
```

#### 3.6: Seakeeping Translation

```markdown
### SEAKEEPING → GEOMETRIC FEATURES

"Rough seas" or "high seas" → Multiple features
1. High deadrise (25-35°) - reduces slamming
2. Bow flare - deflects green water
3. Adequate freeboard - height above waterline
   - Minimum freeboard ≥ 1.5 × wave_height

"3ft seas" (0.9m waves) → Specific requirements
1. Freeboard:
   CONSTRAIN hull.freeboard_bow_m >= 1.5  // 1.5m minimum
   CONSTRAIN hull.freeboard_stern_m >= 1.0
2. Bow flare:
   UPDATE geometry.section bow {
     points: [...increase beam above waterline...]
   }
3. Deadrise:
   - Forward sections: 20-25° minimum

"Reduce slamming" → Increase deadrise forward
- Slamming worst at forward 1/3 of hull
- Increase deadrise in stations 0.1-0.4
- Target: 20-30° deadrise

Seakeeping Principles:
- Freeboard prevents deck wetness
- Flare deflects green water (wave over bow)
- Deadrise reduces impact loads (slamming)
- All are geometric, not abstract properties
```

#### 3.7: Constraints & Emergent Properties

```markdown
### CONSTRAINTS - EMERGENT vs SETTABLE

Draft is EMERGENT (not a parameter):
- Draft comes FROM section geometry
- Cannot set draft directly
- To change draft:
  1. Modify ALL section z-coordinates proportionally
  2. Revalidate displacement and stability

"Reduce draft to 1.2m":
WRONG: SET hull.draft = 1.2  ❌
RIGHT:
  UPDATE geometry.section midship {
    points: [
      [0, 0],
      [2.5, 1.2],  // Reduced from 1.8 (33% reduction)
      ...
    ]
  }
  // Must update ALL sections (bow, midship, stern)

Beam is LOCAL (not global):
- Each section has its own beam
- Cannot set global beam parameter
- To change beam:
  - Midship: Affects displacement, stability
  - Bow: Affects entry angle, resistance
  - Stern: Affects planing surface, aesthetics

"Make stern wider":
WRONG: SET hull.beam = 7.0  ❌ (changes all sections)
RIGHT:
  UPDATE geometry.section stern {
    station_fraction: 0.9,
    points: [[0, 0], [3.5, 1.5], ...]  // Wider than midship
  }
  UPDATE geometry.section quarter {
    station_fraction: 0.75,
    points: [[0, 0], [3.0, 1.5], ...]  // Taper from midship
  }
  // Preserve bow and midship sections
```

#### 3.8: Brand/Industry Term Translation

```markdown
### TRANSLATING COMMON TERMS

"Cigarette boat" → High-performance offshore racing
- High L/B ratio (9-11)
- Deep-V (24-28° deadrise)
- Stepped hull (air lubrication)
- Narrow beam, aggressive
Implementation:
  1. CREATE geometry.body with L/B 9-11
  2. UPDATE sections with 24-28° deadrise
  3. CREATE geometry.discontinuity steps
  4. CONSTRAIN hull.length_beam_ratio >= 9.0

"Trawler" → Displacement, full hull
- Low L/B (3-4)
- Round bilge
- Low deadrise (10-15°)
- High freeboard

"RIB" (Rigid Inflatable Boat) → Deep-V with inflatable collar
- Deep-V center hull (25-35° deadrise)
- Note: Inflatable collar outside scope (no inflatable primitive)
- Focus on deep-V hull geometry

Translation Strategy:
1. Identify key characteristics
2. Map to measurable geometry
3. Warn if aspects are outside primitive scope
4. Never refuse - translate what's possible
```

---

## Part IV: Implementation Method

### Step 1: Baseline Testing (1h, ~$1)

**Objective:** Quantify current agent capability

**Commands:**
```bash
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0

# Run knowledge tests
python3 -m pytest tests/knowledge/test_agent_naval_architecture_knowledge.py::test_agent_knowledge_summary -v -s > baseline_results.txt

# Expected: 2-4 / 12 tests pass (~25%)
```

**Deliverable:**
- `baseline_results.txt` with pass/fail for each test
- Specific failure modes documented
- Identify patterns (inventing primitives? using enumeration?)

---

### Step 2: Enhance System Prompt (2-3h)

**File:** `magnet/agents/geometry_proposer.py`  
**Location:** Lines 24-73  
**Action:** Replace with enhanced prompt (250+ lines)

**Structure:**

```python
GEOMETRY_PROPOSER_SYSTEM_PROMPT = """You are MAGNET's Geometry Proposer.

YOUR ROLE:
[...existing role description...]

ALLOWED PRIMITIVES (geometry.* only):
[...existing primitives list...]

## NAVAL ARCHITECTURE TRANSLATION GUIDE

### SPEED & RESISTANCE
[Section 3.1 above - ~40 lines]

### STABILITY
[Section 3.2 above - ~30 lines]

### HULL FORMS
[Section 3.3 above - ~40 lines]

### FEATURES → GEOMETRY PRIMITIVES
[Section 3.4 above - ~60 lines]

### MULTI-BODY CONFIGURATIONS
[Section 3.5 above - ~30 lines]

### SEAKEEPING → GEOMETRIC FEATURES
[Section 3.6 above - ~40 lines]

### CONSTRAINTS - EMERGENT vs SETTABLE
[Section 3.7 above - ~40 lines]

### TRANSLATING COMMON TERMS
[Section 3.8 above - ~30 lines]

## CRITICAL REMINDERS

1. NEVER invent primitives
   - Valid: geometry.body, geometry.section, geometry.surface,
           geometry.discontinuity, geometry.flow_path, 
           geometry.opening, geometry.attachment
   - Invalid: geometry.spray_rail, geometry.chine, geometry.step

2. NEVER use enumeration
   - Invalid: hull.hull_type, hull.style, hull.performance
   - Invalid: SET hull.has_spray_rails = true

3. ALWAYS make geometric changes
   - Bad: "I'll make it faster" (no changes)
   - Good: UPDATE geometry.section { ... reduce beam ... }

4. ALWAYS include quantification
   - Bad: "Increase beam"
   - Good: "Increase beam from 5.0m to 6.0m (L/B 4.2 to 5.0)"

5. ALWAYS explain physics
   - "L/B increase → lower wave-making resistance"
   - "Wider beam → higher BM → higher GM"

## IMPORTANT FLEXIBILITY GUIDELINES

1. **Typical values are GUIDELINES, not rules**
   - Translation guide shows CONVENTIONAL values
   - If user specifies different values, USE THOSE
   - Example: User wants catamaran with S/L = 0.6 (wider than typical)
     → Use 0.6, don't force to 0.4
   - Novel configurations are ENCOURAGED

2. **Unknown terms: ASK instead of GUESS**
   - If you don't know how to translate a term, REQUEST CLARIFICATION
   - Bad: Inventing a primitive for "skeg"
   - Good: "I'm not certain how to implement a skeg with current primitives.
           Could you describe the geometric feature you want? (e.g., keel extension,
           rudder support, longitudinal fin)"
   - Set confidence < 0.5 when uncertain

3. **User intent overrides conventions**
   - User may want non-standard designs
   - User may want to experiment with extreme values
   - Your role: Translate intent → geometry, not judge viability
   - Kernel will validate physics (that's its job, not yours)

[...existing rules and format instructions...]
"""
```

**Enhancement Checklist:**
- [ ] Add Speed & Resistance section
- [ ] Add Stability section
- [ ] Add Hull Forms section
- [ ] Add Features translation
- [ ] Add Multi-body section
- [ ] Add Seakeeping section
- [ ] Add Constraints section
- [ ] Add Brand translation section
- [ ] Add critical reminders
- [ ] Verify no enumeration examples
- [ ] Verify all examples use valid primitives

**Estimated Time:** 2-3 hours (copy, adapt, test for coherence)

---

### Step 3: Validation Testing (1h, ~$1)

**Objective:** Verify enhancement achieves target pass rate

**Commands:**
```bash
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0

# Run all knowledge tests
python3 -m pytest tests/knowledge/ -v -s > enhanced_results.txt

# Target: ≥10 / 12 tests pass (83%+)
```

**Success Criteria:**
- ✅ ≥10/12 tests pass → **Production ready**
- ⚠️ 8-9/12 tests pass → **Needs few-shot examples**
- ❌ <8/12 tests pass → **Needs iteration**

**Deliverable:**
- `enhanced_results.txt` with results
- Comparison: baseline vs enhanced
- Remaining failure analysis

---

### Step 4: Iterative Refinement (IF NEEDED, 1-2h)

**IF pass rate < 83%, add few-shot examples**

**Add to system prompt:**

```python
## FEW-SHOT EXAMPLES

### Example 1: "Add spray rails"

USER: "Add spray rails to reduce spray"

CORRECT ✅:
CREATE geometry.discontinuity spray_rail_port {
  body_id: "main_hull",
  type: "surface_break",
  start_station: 0.2,
  end_station: 0.7,
  profile: "longitudinal_edge",
  height_fraction: 0.7,
  depth_m: 0.03,
}

Reasoning: Spray rails are longitudinal discontinuities at ~70% 
hull height that deflect spray and reduce wetted surface at 
planing speeds. Positioned from 20% (forward) to 70% (aft) of LOA.

INCORRECT ❌:
CREATE hull.spray_rail { ... }         // Invents type
CREATE geometry.spray_rail { ... }     // Invents primitive
SET hull.has_spray_rails = true        // Enumeration

---

### Example 2: "Make it faster"

USER: "Make this design faster"

CORRECT ✅:
ANALYSIS: Current L/B = 25/6 = 4.17 (beamy for speed)
Target L/B = 6.5 (displacement efficiency)

UPDATE geometry.section midship {
  body_id: "main_hull",
  station_fraction: 0.5,
  points: [
    [0, 0],
    [1.9, 1.5],  // Reduced from 3.0m (narrower)
    [1.9, 2.0],
    [0, 2.0]
  ]
}

Reasoning: Reducing beam from 6.0m to 3.8m increases L/B from 
4.17 to 6.58. Higher L/B reduces wave-making resistance by ~12% 
at Fn=0.22 (displacement regime).

INCORRECT ❌:
SET hull.speed = 30                    // Doesn't change physics
hull.performance = "fast"              // Enumeration
"I'll make it faster"                  // No geometric changes

---

### Example 3: "I want a catamaran"

USER: "Make this a catamaran"

CORRECT ✅:
CREATE geometry.body port_hull {
  body_type: "demihull",
  physics_category: "surface_piercing",
  offset_x_m: 0.0,
  offset_y_m: -10.0,  // Port side, 40% of LOA
  offset_z_m: 0.0,
}

CREATE geometry.body stbd_hull {
  body_type: "demihull",
  physics_category: "surface_piercing",
  offset_x_m: 0.0,
  offset_y_m: 10.0,   // Starboard side
  offset_z_m: 0.0,
}

CREATE geometry.section port_midship {
  body_id: "port_hull",
  station_fraction: 0.5,
  points: [[0, 0], [1.5, 1.2], [1.5, 1.8], [0, 1.8]],
}

CREATE geometry.section stbd_midship {
  body_id: "stbd_hull",
  station_fraction: 0.5,
  points: [[0, 0], [1.5, 1.2], [1.5, 1.8], [0, 1.8]],
}

Reasoning: Catamaran = two symmetric hulls (demihulls) with 
lateral spacing. Hull spacing S/L = 0.4 typical. For LOA=25m, 
spacing = 10m, so offset = ±5m from centerline. Demihulls are 
slender (L/B ~10-15) for multi-body vessels.

INCORRECT ❌:
SET hull.hull_type = "catamaran"           // Enumeration
CREATE hull_config { type: "catamaran" }   // Invents type system
CREATE geometry.body { body_type: "catamaran" }  // Single body
```

**Add examples for specific failures identified in Step 3.**

---

## Part V: Best Method Forward

### Recommended Path (5h total)

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: BASELINE (1h)                                  │
├─────────────────────────────────────────────────────────┤
│ • Run current tests                                     │
│ • Document failures                                     │
│ • Identify patterns                                     │
│ Expected: 2-4/12 pass (~25%)                            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: ENHANCE PROMPT (2-3h)                          │
├─────────────────────────────────────────────────────────┤
│ • Add Naval Architecture Translation Guide              │
│ • Add 8 knowledge sections (from Part III)              │
│ • Add critical reminders                                │
│ • Verify no enumeration in examples                     │
│ File: magnet/agents/geometry_proposer.py (lines 24-73) │
│ Change: 50 lines → 300 lines                            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: VALIDATE (1h)                                  │
├─────────────────────────────────────────────────────────┤
│ • Run all 12 tests again                                │
│ • Compare baseline vs enhanced                          │
│ • Target: ≥10/12 pass (83%+)                            │
│ Expected: 10-11/12 pass                                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: ITERATE IF NEEDED (0-2h)                       │
├─────────────────────────────────────────────────────────┤
│ IF pass rate < 83%:                                     │
│ • Add few-shot examples for failures                    │
│ • Re-test                                               │
│ ELSE:                                                   │
│ • Document success                                      │
│ • Mark agent as production ready                        │
└─────────────────────────────────────────────────────────┘
```

**Total Effort:** 4-5 hours + ~$2 in API costs  
**Outcome:** Production-ready agent with 80%+ knowledge test pass rate

---

### Alternative Paths (NOT RECOMMENDED)

#### Alt 1: Retrieval-Augmented Generation (RAG)

**Concept:** Store knowledge base, retrieve relevant sections based on intent

**Pros:**
- Can have unlimited knowledge base size
- Easy to update knowledge without prompt changes
- Can provide references

**Cons:**
- More complex (4-6h implementation)
- Requires vector database or search
- Adds latency to every request
- Retrieval quality matters

**Verdict:** Overkill for this problem. Prompt enhancement is simpler and faster.

---

#### Alt 2: Fine-Tuning

**Concept:** Fine-tune LLM on naval architecture examples

**Pros:**
- Deeply internalized knowledge
- No prompt bloat

**Cons:**
- Expensive ($100-500+)
- Requires training dataset
- Slow iteration (days not hours)
- Less controllable

**Verdict:** Too heavy. Use for v2 if prompt approach insufficient.

---

#### Alt 3: Defer Enhancement

**Concept:** Ship without agent knowledge, require users to write DSL

**Pros:**
- Zero effort now

**Cons:**
- Poor user experience
- System appears broken (even though kernel works)
- Reduces value proposition
- Will need to do this eventually anyway

**Verdict:** Not viable. Agent is the user interface.

---

## Part VI: Success Metrics

### Definition of Done

**Minimum Viable (Production Ready):**
- ✅ ≥10/12 knowledge tests pass (83%+)
- ✅ No enumeration in any test response
- ✅ No invented primitives in any test response
- ✅ All responses include geometric changes (not generic advice)
- ✅ All responses include quantification and physics reasoning

**Specific Test Requirements:**

**Must Pass (Critical):**
1. ✅ KNOW_001: "Make it faster" - Shows L/B knowledge
2. ✅ KNOW_002: "Add spray rails" - Uses discontinuity correctly
3. ✅ KNOW_003: "Catamaran" - Creates 2 bodies, no enumeration
4. ✅ KNOW_004: "More stable" - Shows GM/BM knowledge
5. ✅ KNOW_005: "Deep-V" - Modifies sections with deadrise
6. ✅ KNOW_011: "Add chines" - Uses discontinuity or sections

**Should Pass (Important):**
7. ✅ KNOW_007: "Reduce draft" - Understands emergent property
8. ✅ KNOW_009: "Fuel efficient" - Resistance reduction strategies
9. ✅ KNOW_010: "Wider stern" - Local section modification
10. ✅ KNOW_012: "3ft seas" - Seakeeping → geometry

**Can Fail (Advanced):**
11. ⚠️ KNOW_006: "Bulbous bow" - Complex composition
12. ⚠️ KNOW_008: "Cigarette boat" - Brand translation

---

### Measurement Process

```bash
# Run tests
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0
python3 -m pytest tests/knowledge/ -v -s > results.txt

# Analyze results
grep "PASS\|FAIL" results.txt | wc -l     # Total tests
grep "PASS" results.txt | wc -l          # Passes
grep "FAIL" results.txt | wc -l          # Failures

# Calculate pass rate
# Pass rate = (passes / total) * 100%

# Check for violations
grep "enumeration" results.txt            # Should be 0
grep "invented" results.txt               # Should be 0
grep "no geometric changes" results.txt   # Should be 0
```

---

## Part VII: Risk Mitigation

### Risk 1: Prompt Too Long

**Probability:** LOW  
**Impact:** MEDIUM

**Scenario:** 300-line prompt exceeds context window or degrades performance

**Mitigation:**
- Test with actual LLM first (Claude Sonnet 4.5 has large context)
- If needed, compress using tables instead of prose
- If still too long, move to RAG (Phase 2 fallback)

**Trigger:** LLM truncates prompt or quality degrades

---

### Risk 2: Still Fails Tests After Enhancement

**Probability:** MEDIUM  
**Impact:** MEDIUM

**Scenario:** Enhanced prompt achieves 7-9/12 pass (not ≥10/12)

**Mitigation:**
- Add few-shot examples for specific failures (1-2h)
- If still insufficient, implement RAG (4-6h)
- If RAG insufficient, consider fine-tuning (long term)

**Trigger:** Pass rate < 83% after Phase 3

---

### Risk 3: Cost of Testing

**Probability:** LOW  
**Impact:** LOW

**Scenario:** Multiple test runs become expensive

**Mitigation:**
- Each full run: ~$0.50-$1.00
- Budget for 3-5 runs: ~$5 total
- Cache responses for regression testing
- Use sampling (run 3-4 tests) during iteration

**Trigger:** Testing costs exceed $10

---

### Risk 4: LLM Doesn't Follow Instructions

**Probability:** LOW  
**Impact:** HIGH

**Scenario:** Even with enhanced prompt, LLM ignores guidelines

**Mitigation:**
- Reinforce with few-shot examples (show correct patterns)
- Add self-validation (agent checks its own output)
- If persistent, switch LLM model or use fine-tuning
- This is unlikely with Claude Sonnet 4.5 (strong instruction following)

**Trigger:** Consistent instruction-following failures in tests

---

## Part VIII: Execution Plan

### Pre-Work (Complete ✅)

- [x] Assessment framework created
- [x] 12 knowledge tests implemented
- [x] Gap analysis documented
- [x] Enhancement plan specified

---

### Week 1: Agent Enhancement

#### Day 1 Morning (2h)

**Task:** Baseline testing + analysis

```bash
# 1. Run baseline tests (30 min)
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0
python3 -m pytest tests/knowledge/test_agent_naval_architecture_knowledge.py::test_agent_knowledge_summary -v -s | tee baseline_results.txt

# 2. Analyze results (30 min)
# Document:
# - Which tests passed?
# - Which tests failed?
# - Common failure patterns?
# - Enumeration usage?
# - Invented primitives?

# 3. Create baseline report (1h)
# File: MAGNET_Agent_Baseline_Results.md
# Contents:
# - Pass/fail for each test
# - Failure modes
# - Specific examples
# - Confirm predicted ~25% pass rate
```

**Deliverable:** Baseline metrics document

---

#### Day 1 Afternoon (3h)

**Task:** Enhance system prompt with explicit edit locations

---

##### EXPLICIT EDIT INSTRUCTIONS FOR CURSOR

Each edit specifies exact file, line number, and content. **After EVERY edit, run the sacred invariants check.**

---

###### EDIT 1: Add Naval Architecture Translation Guide Header

**File:** `magnet/agents/geometry_proposer.py`
**Line 82:** Insert BEFORE the closing `"""`
**Content:**
```python

## NAVAL ARCHITECTURE TRANSLATION GUIDE

Use this guide to translate user intent into valid geometry primitives.
```

**SACRED INVARIANTS CHECK (run after this edit):**
```bash
python3 -m pytest tests/invariants/ -v
# MUST pass 54/54 - if ANY fail, STOP and revert

grep -rn "HullFamily\|hull_type" magnet/agents/geometry_proposer.py
# MUST return ONLY comments, NOT code - if grep returns non-comment lines, STOP and revert
```

---

###### EDIT 2: Add Speed & Resistance Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~85:** Insert AFTER Translation Guide header
**Content:**
```python

### SPEED & RESISTANCE

"Make it faster" → Increase L/B ratio
- Target L/B: 6-8 (displacement), 8-12 (planing)
- Implementation: UPDATE geometry.section { ... narrow beam ... }

Typical L/B Ratios:
- Cargo ships: 6-7, Planing boats: 8-12, Catamarans (per hull): 10-15
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 3: Add Stability Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~100:** Insert AFTER Speed & Resistance
**Content:**
```python

### STABILITY

"More stable" → Increase GM (GM = KB + BM - KG)
- To increase GM: Increase beam → UPDATE geometry.section { ... widen beam ... }
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 4: Add Hull Forms Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~110:** Insert AFTER Stability
**Content:**
```python

### HULL FORMS

"Deep-V hull" → High deadrise (20-30°) in sections
- UPDATE geometry.section with high-angle points
Deadrise: Flat bottom: 0-10°, Deep V: 20-30°
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 5: Add Features Translation Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~125:** Insert AFTER Hull Forms
**Content:**
```python

### FEATURES → GEOMETRY PRIMITIVES

"Add spray rails" → geometry.discontinuity { type: "surface_break", height_fraction: 0.7 }
"Add chines" → geometry.discontinuity { type: "hard_edge", height_fraction: 0.6 }
"Bulbous bow" → geometry.body + geometry.attachment (separate body, forward, below waterline)
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 6: Add Multi-Body Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~145:** Insert AFTER Features
**Content:**
```python

### MULTI-BODY CONFIGURATIONS

"Catamaran" → 2× geometry.body with lateral offset
- port_hull: offset_y_m: -10.0, stbd_hull: offset_y_m: 10.0
- Hull spacing: S/L = 0.35-0.45 typical
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 7: Add Seakeeping Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~160:** Insert AFTER Multi-Body
**Content:**
```python

### SEAKEEPING

"3ft seas" → 1. High deadrise (25-35°), 2. Bow flare, 3. Freeboard ≥ 1.5 × wave_height
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 8: Add Constraints Section

**File:** `magnet/agents/geometry_proposer.py`
**Line ~170:** Insert AFTER Seakeeping
**Content:**
```python

### CONSTRAINTS - EMERGENT vs SETTABLE

Draft is EMERGENT: WRONG: SET hull.draft = 1.2 ❌, RIGHT: UPDATE geometry.section { z-coords }
Beam is LOCAL: WRONG: SET hull.beam = 7.0 ❌, RIGHT: UPDATE geometry.section stern { wider }
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

###### EDIT 9: Add Critical Reminders

**File:** `magnet/agents/geometry_proposer.py`
**Line ~185:** Insert BEFORE closing `"""`
**Content:**
```python

## CRITICAL REMINDERS

1. NEVER invent primitives (Valid: geometry.body/section/surface/discontinuity/flow_path/opening/attachment)
2. NEVER use enumeration (Invalid: hull.hull_type, SET hull.has_spray_rails = true)
3. ALWAYS make geometric changes (Good: UPDATE geometry.section { ... })
4. ALWAYS include quantification (Good: "Increase beam from 5.0m to 6.0m")
```

**SACRED INVARIANTS CHECK:** `python3 -m pytest tests/invariants/ -v` # MUST pass 54/54

---

##### FINAL VERIFICATION (after all 9 edits)

```bash
python3 -m pytest tests/invariants/ -v              # MUST pass 54/54
grep -rn "HullFamily\|hull_type" magnet/agents/geometry_proposer.py  # Only comments
python3 -c "from magnet.agents.geometry_proposer import GEOMETRY_PROPOSER_SYSTEM_PROMPT; print('OK')"  # MUST print OK
```

---

**Deliverable:** Enhanced system prompt with 9 explicit edits + invariants verification after each

---

#### Day 2 Morning (1h)

**Task:** Validation testing

---

##### ⚠️ DECISION GATE AFTER DAY 1 PM

**BEFORE proceeding to Day 2, run this decision gate:**

```bash
# Run knowledge tests
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0
python3 -m pytest tests/knowledge/ -v -s | tee day1_results.txt

# Count passes
PASSES=$(grep -c "PASSED" day1_results.txt)
echo "Pass count: $PASSES / 12"
```

**DECISION LOGIC:**

| Result | Action |
|:-------|:-------|
| **≥10/12 pass** | ✅ **STOP** - Mark complete, update `MAGNET_Critical_Corrections.md`, skip Day 2 |
| **8-9/12 pass** | ⚠️ **CONTINUE** to few-shot examples (Day 2 AM) |
| **<8/12 pass** | 🛑 **STOP** - Escalate to human, do NOT iterate blindly |

**If ≥10/12 pass, run:**
```bash
# Mark complete
echo "✅ Agent enhancement COMPLETE - $(date)" >> MAGNET_Critical_Corrections.md
echo "Knowledge tests: $PASSES/12 pass" >> MAGNET_Critical_Corrections.md
```

**If <8/12 pass, STOP and:**
1. Do NOT add more few-shot examples blindly
2. Document which specific tests failed
3. Escalate to human for review
4. Possible issues: prompt too long, wrong section formatting, LLM not following instructions

---

##### Day 2 AM Tasks (only if 8-9/12 pass)

```bash
# 1. Run enhanced tests (30 min)
export SKIP_LIVE_LLM_TESTS=0
python3 -m pytest tests/knowledge/ -v -s | tee enhanced_results.txt

# 2. Analyze failures
grep "FAILED" enhanced_results.txt  # Which tests failed?

# 3. Add few-shot examples ONLY for failed tests
# (See Step 4 in Part IV for example format)
```

---

##### ⚠️ DECISION GATE AFTER DAY 2 AM

```bash
# Re-run after adding few-shot examples
python3 -m pytest tests/knowledge/ -v -s | tee day2_results.txt
PASSES=$(grep -c "PASSED" day2_results.txt)
```

| Result | Action |
|:-------|:-------|
| **≥10/12 pass** | ✅ **STOP** - Mark complete |
| **<10/12 pass** | 🛑 **STOP** - Escalate to human, do NOT iterate further |

**CRITICAL:** Maximum 2 iterations. If still <10/12 after Day 2 AM, the approach needs human review - do NOT keep adding examples.

---

#### Day 2 Afternoon (IF NEEDED, 2h)

**Task:** Add few-shot examples for failures

```python
# Add to system prompt:

## FEW-SHOT EXAMPLES

### Example 1: [Specific test that failed]
[Show correct approach]
[Show incorrect approaches]

### Example 2: [Another failed test]
[Show correct approach]
[Show incorrect approaches]

[Continue for each persistent failure]
```

**Re-test:**
```bash
python3 -m pytest tests/knowledge/ -v -s | tee iteration2_results.txt
```

**Target:** ≥10/12 pass

---

### Completion Criteria

**Agent is production ready when:**
- ✅ ≥10/14 total tests pass (12 knowledge + 2 safeguard tests)
- ✅ No enumeration detected in any response
- ✅ No invented primitives in any response
- ✅ All responses make geometric changes
- ✅ Unknown terms trigger clarification request (not hallucination)
- ✅ Novel configurations use user-specified values (not forced to typical)
- ✅ Prompt size < 30% of model context
- ✅ Quality logging operational
- ✅ Documentation updated (mark agent as validated)

**Then:**
1. Update `MAGNET_Critical_Corrections.md` - mark agent as complete
2. Update `MAGNET_System_State_Analysis.md` - note agent capability
3. Create `MAGNET_Agent_Validation_Report.md` - document test results
4. Update README - note agent is production ready
5. **Set up ongoing monitoring:**
   - Weekly quality reports enabled
   - Monthly test automation configured
   - Quarterly review scheduled (April 2026)

---

## Part IX: Critical Safeguards & Ongoing Maintenance

### Audit Summary

The enhancement plan is **aligned with project goals** and **executable**. However, several critical safeguards must be added to ensure long-term success:

---

### Safeguard 1: Prompt Size Monitoring

**Issue:** Enhanced prompt grows from 50 → 300 lines. With user conversation history and complex intent, total context could exceed limits.

**Risk:** Context crowding → degraded performance, truncated responses, lost conversation history

**Mitigation:**

```python
# Add to geometry_proposer.py

import tiktoken

def check_prompt_size(
    system_prompt: str,
    user_message: str,
    conversation_history: List[str],
    model: str = "claude-sonnet-4"
) -> Dict[str, Any]:
    """
    Monitor prompt token usage to prevent context overflow.
    
    Returns warnings if prompt exceeds thresholds.
    """
    # Estimate tokens (rough approximation)
    total_chars = len(system_prompt) + len(user_message) + sum(len(m) for m in conversation_history)
    estimated_tokens = total_chars // 4  # ~4 chars per token
    
    # Model-specific limits
    context_limits = {
        "claude-sonnet-4": 200_000,
        "gpt-4": 8_000,
        "gpt-4-turbo": 128_000,
    }
    
    limit = context_limits.get(model, 8_000)
    usage_pct = (estimated_tokens / limit) * 100
    
    if usage_pct > 60:
        return {
            "warning": "HIGH",
            "usage_pct": usage_pct,
            "recommendation": "Consider RAG retrieval instead of full static prompt",
        }
    elif usage_pct > 30:
        return {
            "warning": "MEDIUM",
            "usage_pct": usage_pct,
            "recommendation": "Monitor closely, may need compression",
        }
    else:
        return {
            "warning": None,
            "usage_pct": usage_pct,
        }
```

**Threshold:** If prompt uses >30% of context, consider RAG retrieval for translation guide.

**Action Item:** Add prompt size check to Step 2 (Enhancement) validation.

---

### Safeguard 2: Fallback for Unknown Terms

**Issue:** If user requests a term not in translation guide (e.g., "Add a skeg"), agent might hallucinate.

**Risk:** Invented primitives, enumeration, or generic responses

**Mitigation:** Already added to prompt (Flexibility Guidelines #2):

```markdown
2. **Unknown terms: ASK instead of GUESS**
   - If you don't know how to translate a term, REQUEST CLARIFICATION
   - Set confidence < 0.5 when uncertain
   - Example: "I'm not certain how to implement a skeg. Could you 
              describe the geometric feature? (keel extension, rudder 
              support, longitudinal fin)"
```

**Test:** Add KNOW_013: "Add a skeg" → Should request clarification, NOT invent primitive

**Action Item:** Add test case in validation phase.

---

### Safeguard 3: Novel Configuration Support

**Issue:** Translation guide shows TYPICAL values (e.g., S/L = 0.35-0.45 for catamaran). Might constrain novel designs.

**Risk:** Agent pushes toward conventional designs, violating "novel forms without new code" goal

**Mitigation:** Already added to prompt (Flexibility Guidelines #1):

```markdown
1. **Typical values are GUIDELINES, not rules**
   - If user specifies different values, USE THOSE
   - Example: User wants catamaran with S/L = 0.6 → Use 0.6
   - Novel configurations are ENCOURAGED
```

**Test:** Add KNOW_014: "Catamaran with 60% hull spacing" → Should use 0.6, NOT force to 0.4

**Action Item:** Add test case in validation phase.

---

### Safeguard 4: Multi-Model Compatibility

**Issue:** Enhanced prompt designed for Claude Sonnet 4.5. May not work with smaller or weaker models.

**Risk:** Performance degradation with different LLMs

**Compatibility Assessment:**

| Model | Expected Performance | Recommendation |
|:------|:--------------------|:---------------|
| Claude Sonnet 4+ | ✅ Excellent | Use as-is |
| Claude Opus | ✅ Excellent | Use as-is |
| GPT-4 Turbo | ✅ Good | Use as-is, test |
| GPT-4 (base) | ⚠️ Fair | May need compression |
| Llama 7B/13B | ❌ Poor | Use RAG, not static prompt |
| Mistral 7B | ❌ Poor | Use RAG, not static prompt |

**Mitigation:**

```python
def adapt_prompt_for_model(model: str) -> str:
    """
    Adapt prompt based on model capabilities.
    """
    if model in ["claude-sonnet-4", "claude-opus"]:
        # Full prompt with all 8 sections
        return FULL_ENHANCED_PROMPT
    
    elif model in ["gpt-4-turbo", "gpt-4"]:
        # Compressed version: tables instead of prose
        return COMPRESSED_ENHANCED_PROMPT
    
    elif model in ["llama", "mistral", "small"]:
        # Use RAG: inject only relevant sections based on intent
        return BASE_PROMPT  # Minimal, rely on RAG
    
    else:
        # Unknown model: use full prompt, log warning
        logger.warning(f"Unknown model {model}, using full prompt")
        return FULL_ENHANCED_PROMPT
```

**Action Item:** If switching from Claude, re-run baseline tests. Document model-specific results.

---

### Maintenance Plan: Translation Guide Evolution

**Issue:** Naval architecture evolves. New hull forms emerge. Translation guide can become stale.

**Examples:**
- Hydrofoil-assisted vessels (emerging)
- Electric propulsion configurations (new)
- Autonomous vessel forms (future)
- Regional design preferences (cultural)

**Maintenance Schedule:**

```markdown
QUARTERLY REVIEW (Every 3 months):
1. Review user feedback logs
   - What terms are users requesting?
   - What clarifications are agents requesting most?
2. Identify new patterns
   - Are there repeated requests for features not in guide?
3. Update translation guide
   - Add new terms with geometric translations
   - Update typical values if industry standards change
4. Re-run validation tests
   - Ensure updates don't break existing translations

ANNUAL REVIEW (Yearly):
1. Major revision based on:
   - New hull form research
   - Regulatory changes (safety standards)
   - Technology advances (new materials, methods)
2. Consider fine-tuning
   - If guide becomes too large (>500 lines)
   - If RAG complexity is high
3. Update test suite
   - Add tests for new terms
   - Archive obsolete tests
```

**Responsibility:** Assign to engineering team or domain expert.

**Action Item:** Schedule first quarterly review for April 2026.

---

### Ongoing Quality Monitoring

**Issue:** Plan validates agent once. No ongoing monitoring of quality over time.

**Risk:** Agent quality degrades as patterns shift, model updates, or edge cases accumulate

**Monitoring Strategy:**

#### 1. Real-Time Logging

```python
# Add to geometry_proposer.py

def log_proposal_quality(
    intent: str,
    proposal: DesignProgram,
    execution_result: ExecutionResult,
):
    """
    Log every agent proposal for quality analysis.
    """
    quality_metrics = {
        "timestamp": datetime.now().isoformat(),
        "intent": intent,
        "has_enumeration": check_for_enumeration(proposal),
        "invented_primitives": check_for_invented_primitives(proposal),
        "confidence": calculate_avg_confidence(proposal),
        "success": execution_result.success,
        "errors": execution_result.errors,
    }
    
    # Log to quality monitoring database
    log_to_metrics_db(quality_metrics)
    
    # Alert on violations
    if quality_metrics["has_enumeration"]:
        alert("ENUMERATION_DETECTED", quality_metrics)
    if quality_metrics["invented_primitives"]:
        alert("INVENTED_PRIMITIVE", quality_metrics)
```

#### 2. Weekly Sampling

```python
def weekly_quality_report():
    """
    Generate weekly quality report from logs.
    """
    last_week = get_proposals_last_week()
    
    metrics = {
        "total_proposals": len(last_week),
        "enumeration_rate": count_enumeration(last_week) / len(last_week),
        "invention_rate": count_inventions(last_week) / len(last_week),
        "avg_confidence": calculate_avg_confidence(last_week),
        "success_rate": count_successes(last_week) / len(last_week),
        "top_unknown_terms": extract_unknown_terms(last_week),
    }
    
    # Alert if quality degrades
    if metrics["enumeration_rate"] > 0.05:  # >5% enumeration
        alert("QUALITY_DEGRADATION", metrics)
    
    return metrics
```

#### 3. Monthly Test Suite Run

```bash
# Run full 12-test suite monthly
# Automated via cron:

# /etc/cron.monthly/magnet_agent_tests.sh
#!/bin/bash
cd /path/to/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0
python3 -m pytest tests/knowledge/ -v -s > monthly_test_$(date +%Y%m).txt

# Email results to team
mail -s "MAGNET Agent Monthly Test Results" team@example.com < monthly_test_$(date +%Y%m).txt
```

**Quality Thresholds:**

| Metric | Warning Threshold | Critical Threshold |
|:-------|:-----------------|:-------------------|
| Enumeration rate | >2% | >5% |
| Invention rate | >2% | >5% |
| Success rate | <90% | <80% |
| Knowledge test pass | <10/12 | <8/12 |

**Action Items:**
1. Implement logging in Step 2 (Enhancement)
2. Set up weekly reports in Step 4 (Completion)
3. Configure monthly test automation

---

### User Context & Profiles (Future Enhancement)

**Issue:** Different users have different priorities. "Make it faster" for racing vs cargo means different things.

**Example:**
- **Racing team:** Maximize speed (minimize resistance at all costs)
- **Commercial operator:** Balance speed with stability, economy
- **Military:** Prioritize seakeeping, range
- **Recreational:** Comfort, ease of handling

**Future Enhancement (v2):**

```python
class UserProfile:
    """User context for tailored responses."""
    profile_type: str  # "racing", "commercial", "military", "recreational"
    priorities: List[str]  # ["speed", "efficiency", "stability", "seakeeping"]
    risk_tolerance: str  # "conservative", "moderate", "aggressive"

def adapt_translation_for_user(
    intent: str,
    profile: UserProfile
) -> str:
    """
    Adapt translation guide based on user profile.
    """
    if "faster" in intent.lower():
        if profile.profile_type == "racing":
            # Aggressive: High L/B, planing, steps
            return racing_speed_translation()
        elif profile.profile_type == "commercial":
            # Conservative: Moderate L/B, efficiency
            return commercial_speed_translation()
    
    # ... similar for other intents
```

**Not in scope for v1, but architecture supports it.**

**Action Item:** Document for future roadmap.

---

### Summary: Safeguards Checklist

**Add to Implementation (Step 2):**
- [ ] Add "Flexibility Guidelines" to system prompt ✅ (Done above)
- [ ] Add prompt size monitoring function
- [ ] Add proposal quality logging
- [ ] Test with different model if not using Claude

**Add to Validation (Step 3):**
- [ ] Test KNOW_013: Unknown term → Clarification request
- [ ] Test KNOW_014: Novel configuration → Uses user values
- [ ] Measure prompt token usage
- [ ] Document model used

**Add to Completion (Step 4):**
- [ ] Set up weekly quality reports
- [ ] Configure monthly test automation
- [ ] Schedule quarterly translation guide review
- [ ] Document user profile enhancement for v2

---

## Part X: Conclusion

### The Gap is Clear

```
┌──────────────┐
│   KERNEL     │  ✅ Validates physics (189/189 tests)
└──────┬───────┘
       │
       │  ❌ MISSING: Naval architecture knowledge
       │
┌──────▼───────┐
│    AGENT     │  ❌ Can't translate intent → geometry
└──────┬───────┘
       │
       │
┌──────▼───────┐
│    USER      │  ❌ Frustrated (system appears broken)
└──────────────┘
```

### The Fix is Simple

**Add Naval Architecture Translation Guide to system prompt (2-3h)**

Not architecture work. Not kernel work. Just prompt engineering.

### The Validation is Clear

**Run 12 knowledge tests, target ≥10/12 pass**

If tests pass → Agent is production ready  
If tests fail → Add few-shot examples, iterate

### The Outcome is Valuable

**Production-ready agent = Usable system**

Without agent knowledge:
- Users must write DSL directly (poor UX)
- System appears broken (even though kernel works)
- Value proposition reduced

With agent knowledge:
- Users say "make it faster" → Agent generates correct geometry
- System works as intended
- Good user experience

---

### Next Action

**RECOMMENDED:** Proceed with 5h enhancement

**Timeline:**
- Day 1 AM: Baseline testing (2h)
- Day 1 PM: Enhance prompt (3h)
- Day 2 AM: Validation (1h)
- Day 2 PM: Iterate if needed (0-2h)

**Cost:** ~$2-5 in API calls

**Outcome:** Production-ready agent with 80%+ knowledge

---

**Decision Required:** Proceed with enhancement or defer?

**Status:** Plan complete, ready to execute  
**Blocking:** None (can start immediately)

---

## Appendix: Test Execution Commands

```bash
# Set environment
cd /Users/bengibson/MAGNETV1
export SKIP_LIVE_LLM_TESTS=0

# Baseline (run before enhancement)
python3 -m pytest tests/knowledge/test_agent_naval_architecture_knowledge.py::test_agent_knowledge_summary -v -s > baseline_results.txt

# Enhanced (run after enhancement)
python3 -m pytest tests/knowledge/ -v -s > enhanced_results.txt

# Specific test (for debugging)
python3 -m pytest tests/knowledge/test_agent_naval_architecture_knowledge.py::test_know_001_make_it_faster -v -s

# Compare results
diff baseline_results.txt enhanced_results.txt

# Check for violations
grep -i "enumeration\|invented\|generic" enhanced_results.txt

# Count passes
grep "PASS" enhanced_results.txt | wc -l
```

---

## Audit Results & Plan Improvements

**Date:** January 6, 2026  
**Auditor:** User review  
**Verdict:** ✅ **Plan aligned with goals, enhanced with critical safeguards**

### Goal Alignment Verification

| Goal Component | Plan Coverage | Status |
|:---------------|:--------------|:-------|
| Human in the loop | ✅ Agent translates natural language → geometry | Aligned |
| No enumeration | ✅ Explicitly forbidden in prompt, tested | Aligned |
| Compose from primitives | ✅ Translation shows composition (bulbous bow = body + attachment) | Aligned |
| Kernel validates physics | ✅ Unchanged — agent work only | Aligned |
| Novel forms without new code | ✅ Uses existing 7 primitives | Aligned |

**Conclusion:** Plan preserves all architectural principles.

---

### Critical Issues Identified in Audit

#### Issue 1: Prompt Size May Hit Context Limits ⚠️

**Problem:** 50 → 300 lines. With conversation history, may crowd context.

**Fix Added:** 
- Prompt size monitoring function (`check_prompt_size()`)
- Threshold: Warning at 30% context usage
- Fallback: RAG if exceeds threshold
- Location: Part IX, Safeguard 1

#### Issue 2: Translation Guide May Constrain Novelty ⚠️

**Problem:** "S/L = 0.35-0.45" shows typical values. User wanting novel configurations might get forced to conventional.

**Fix Added:**
- Flexibility Guidelines section in system prompt
- Explicit: "Typical values are GUIDELINES, not rules"
- Test case: KNOW_014 (novel configuration)
- Location: Section 2 (Prompt Enhancement), Part IX Safeguard 3

#### Issue 3: No Fallback for Unknown Terms ❌

**Problem:** User says "Add a skeg" (not in guide) → Agent might hallucinate.

**Fix Added:**
- "Ask for clarification" guideline in system prompt
- Test case: KNOW_013 (unknown term)
- Set confidence < 0.5 when uncertain
- Location: Flexibility Guidelines #2, Part IX Safeguard 2

#### Issue 4: Multi-Model Compatibility Unclear ⚠️

**Problem:** Prompt designed for Claude. May not work with smaller/weaker models.

**Fix Added:**
- Model compatibility assessment (Part IX, Safeguard 4)
- Adaptation strategy for different models
- Recommendation: Re-test if switching models

#### Issue 5: No Knowledge Maintenance Plan ❌

**Problem:** Naval architecture evolves. Guide can become stale.

**Fix Added:**
- Quarterly review schedule
- Annual major revision process
- User feedback integration
- Location: Part IX, Maintenance Plan

#### Issue 6: No User Context Consideration 💡

**Problem:** "Make it faster" means different things to racing vs cargo operators.

**Fix Added:**
- User profiles documented for v2 enhancement
- Architecture supports it (not in v1 scope)
- Location: Part IX, User Context section

#### Issue 7: No Ongoing Quality Monitoring ❌

**Problem:** One-time validation, no ongoing quality tracking.

**Fix Added:**
- Real-time proposal logging
- Weekly quality reports
- Monthly automated test runs
- Quality thresholds and alerts
- Location: Part IX, Ongoing Quality Monitoring

---

### Improvements Made to Plan

**New Sections Added:**
1. **Part IX: Critical Safeguards & Ongoing Maintenance** (500+ lines)
   - 7 safeguards addressing all audit findings
   - Maintenance schedule
   - Quality monitoring strategy

2. **Flexibility Guidelines** (added to system prompt)
   - Typical values are guidelines
   - Ask for clarification on unknown terms
   - User intent overrides conventions

3. **Additional Test Cases:**
   - KNOW_013: Unknown term handling
   - KNOW_014: Novel configuration support

4. **Monitoring Infrastructure:**
   - Prompt size checking
   - Proposal quality logging
   - Weekly/monthly reporting

**Updated Sections:**
- Executive Summary: Added safeguards note
- Execution Plan: Added safeguard implementation steps
- Completion Criteria: Added safeguard requirements (10/14 pass, not 10/12)
- Validation: Added safeguard tests

---

### Audit Verdict

**APPROVED WITH ENHANCEMENTS**

| Criterion | Before Audit | After Audit |
|:----------|:------------|:------------|
| Goal alignment | ✅ Aligned | ✅ Aligned |
| Executability | ✅ Executable | ✅ Executable + Safer |
| Sustainability | ⚠️ One-time | ✅ Ongoing monitoring |
| Flexibility | ⚠️ May constrain | ✅ Explicit flexibility |
| Robustness | ⚠️ Basic | ✅ Safeguarded |
| Multi-model | ❓ Unknown | ✅ Documented |

**Key Improvements:**
- Added 7 critical safeguards
- Established maintenance schedule
- Implemented quality monitoring
- Preserved architectural integrity
- Increased test coverage (12 → 14 tests)

**Overall:** Plan strengthened without changing core approach. Still 5h effort, but now includes production-grade safeguards.

---

**END OF PLAN**

