/**
 * MAGNET UI v2 - Declarative Panel Configuration
 * 
 * This file defines the mapping between backend state fields and UI panel displays.
 * 
 * Adding a new field: Add entry to appropriate phase.fields array
 * Adding a new panel: Add new phase object with source + fields
 * 
 * Field schema:
 *   key: string        - Path in source object (e.g., "displacement_mt")
 *   label: string      - Display label
 *   unit?: string      - Unit suffix (e.g., "m", "t", "kW")
 *   precision?: number - Decimal places (default: 2)
 *   showIf?: function  - (sourceData) => boolean, conditional display
 *   format?: function  - (value, sourceData) => string, custom formatting
 *   group?: string     - Group header for visual organization
 *   isGroup?: boolean  - If true, this is a group header (no key needed)
 */

const PANEL_CONFIG = {
    
    // =========================================================================
    // HULL FORM PANEL
    // =========================================================================
    hull: {
        title: "Hull Form",
        source: "hull",
        // §SKELETON:PhaseRefresh — Badge now shows body_count (geometry-derived), not hull_type (enumeration)
        badge: {
            field: "body_count",
            format: function(v) {
                if (!v || v === 0) return { text: "No Geometry", type: "neutral" };
                if (v === 1) return { text: "Single Body", type: "success" };
                return { text: `${v} Bodies`, type: "success" };
            }
        },
        fields: [
            // Dimensions
            { group: "Principal Dimensions", isGroup: true },
            { key: "lwl", label: "LWL", unit: "m", precision: 2 },
            { key: "loa", label: "LOA", unit: "m", precision: 2 },
            { key: "beam", label: "Beam", unit: "m", precision: 2 },
            { key: "draft", label: "Draft", unit: "m", precision: 2 },
            { key: "depth", label: "Depth", unit: "m", precision: 2 },
            { key: "freeboard_m", label: "Freeboard", unit: "m", precision: 2 },
            
            // Coefficients
            { group: "Form Coefficients", isGroup: true },
            { key: "cb", label: "Block Coeff (Cb)", precision: 3 },
            { key: "cp", label: "Prismatic (Cp)", precision: 3 },
            { key: "cm", label: "Midship (Cm)", precision: 3 },
            { key: "cwp", label: "Waterplane (Cwp)", precision: 3 },
            
            // Shape
            { group: "Hull Shape", isGroup: true },
            { key: "deadrise_deg", label: "Deadrise", unit: "°", precision: 1 },
            { key: "bow_entrance_deg", label: "Bow Entrance", unit: "°", precision: 1 },
            { key: "transom_beam_ratio", label: "Transom Ratio", precision: 2 },
            { key: "lcb_fraction", label: "LCB (fraction)", precision: 3 },
            
            // Geometry (body_count is geometry-derived, not hull_type enumeration)
            { group: "Geometry", isGroup: true },
            { key: "body_count", label: "Body Count", format: function(v) { return v ? String(v) : "—"; } }
        ]
    },

    // =========================================================================
    // HYDROSTATICS PANEL
    // =========================================================================
    hydrostatics: {
        title: "Hydrostatics",
        source: "hull",  // Hydrostatics stored under hull.*
        badge: {
            field: "hydrostatics_method",
            format: function(v) {
                if (v === "geometry_integration") return { text: "Geometry-based", type: "success" };
                if (v === "parametric") return { text: "Parametric", type: "info" };
                return { text: "Not Calculated", type: "neutral" };
            }
        },
        fields: [
            // Displacement
            { group: "Displacement", isGroup: true },
            { key: "displacement_m3", label: "Volume", unit: "m³", precision: 1 },
            { key: "displacement_mt", label: "Mass", unit: "t", precision: 1 },
            
            // Centers
            { group: "Centers", isGroup: true },
            { key: "vcb_m", label: "KB (VCB)", unit: "m", precision: 3 },  // CRITICAL: vcb_m not kb_m
            { key: "lcb_from_ap_m", label: "LCB from AP", unit: "m", precision: 2 },
            { key: "lcf_from_ap_m", label: "LCF from AP", unit: "m", precision: 2 },
            
            // Stability params
            { group: "Stability Parameters", isGroup: true },
            { key: "bmt", label: "BM (transverse)", unit: "m", precision: 3 },  // CRITICAL: bmt not bm_m
            { key: "bml", label: "BM (longitudinal)", unit: "m", precision: 2 },
            { key: "kmt", label: "KM (transverse)", unit: "m", precision: 3 },
            { key: "it_m4", label: "IT (waterplane)", unit: "m⁴", precision: 1 },
            
            // Areas
            { group: "Areas", isGroup: true },
            { key: "waterplane_area_m2", label: "Waterplane Area", unit: "m²", precision: 1 },
            { key: "wetted_surface_m2", label: "Wetted Surface", unit: "m²", precision: 1 },
            
            // Tonnage
            { group: "Tonnage", isGroup: true },
            { key: "tpc", label: "TPC", unit: "t/cm", precision: 3 },
            { key: "mct", label: "MCT", unit: "t·m/cm", precision: 3 },
            
            // Method info
            { group: "Calculation Info", isGroup: true },
            { key: "hydrostatics_method", label: "Method", format: function(v) { return v || "—"; } },
            { 
                key: "sectional_areas", 
                label: "Sectional Areas", 
                format: function(v) { return v && v.length ? v.length + " stations" : "—"; }
            },

            // Equilibrium draft advisor (Phase 3C)
            {
                group: "Equilibrium Draft (advisory)",
                isGroup: true,
                showIf: function(d) {
                    return d && (d.equilibrium_draft_m != null || d.equilibrium_converged != null);
                }
            },
            {
                key: "equilibrium_draft_m",
                label: "Equilibrium Draft",
                unit: "m",
                precision: 3,
                showIf: function(d) { return d && d.equilibrium_draft_m != null; }
            },
            {
                key: "draft",
                label: "Δ Draft (eq - current)",
                unit: "m",
                precision: 3,
                showIf: function(d) { return d && d.equilibrium_draft_m != null && d.draft != null; },
                format: function(v, d) {
                    try {
                        const cur = Number(d.draft);
                        const eq = Number(d.equilibrium_draft_m);
                        if (!isFinite(cur) || !isFinite(eq)) return "—";
                        const delta = eq - cur;
                        const sign = delta >= 0 ? "+" : "";
                        return sign + delta.toFixed(3);
                    } catch (e) {
                        return "—";
                    }
                }
            },
            {
                key: "equilibrium_converged",
                label: "Converged",
                showIf: function(d) { return d && d.equilibrium_converged != null; },
                format: function(v) { return v === true ? "Yes" : v === false ? "No" : "—"; }
            },
            {
                key: "equilibrium_residual_mt",
                label: "Residual (disp - target)",
                unit: "t",
                precision: 3,
                showIf: function(d) { return d && d.equilibrium_residual_mt != null; }
            },
            {
                key: "equilibrium_target_displacement_mt",
                label: "Target Displacement",
                unit: "t",
                precision: 2,
                showIf: function(d) { return d && d.equilibrium_target_displacement_mt != null; }
            },
            {
                key: "equilibrium_iterations",
                label: "Iterations",
                precision: 0,
                showIf: function(d) { return d && d.equilibrium_iterations != null; }
            },
            {
                label: "Apply Equilibrium Draft",
                showIf: function(d) {
                    if (!d) return false;
                    if (d.equilibrium_draft_m == null || d.draft == null) return false;
                    const cur = Number(d.draft);
                    const eq = Number(d.equilibrium_draft_m);
                    if (!isFinite(cur) || !isFinite(eq)) return false;
                    return Math.abs(eq - cur) > 1e-3;
                },
                action: {
                    event: "applyEquilibriumDraft",
                    label: "Apply to hull.draft",
                    payload: function(d) {
                        return { draft_m: d && d.equilibrium_draft_m != null ? Number(d.equilibrium_draft_m) : null };
                    },
                    disabledIf: function(d) {
                        const eq = d && d.equilibrium_draft_m != null ? Number(d.equilibrium_draft_m) : NaN;
                        if (!isFinite(eq)) return true;
                        // If solver explicitly did not converge, do not allow apply from UI.
                        // (Still show the result for visibility, but keep action explicit + safe.)
                        if (d && d.equilibrium_converged === false) return true;
                        return false;
                    }
                }
            }
        ]
    },

    // =========================================================================
    // RESISTANCE PANEL
    // =========================================================================
    resistance: {
        title: "Resistance & Power",
        source: "resistance",
        badge: {
            field: "method_valid",
            format: function(v, data) {
                if (v === true) return { text: "Method Valid", type: "success" };
                if (v === false) return { text: data && data.validity_note ? data.validity_note : "Method Limited", type: "warning" };
                return { text: "Not Calculated", type: "neutral" };
            }
        },
        fields: [
            // Primary results
            { group: "Total Resistance", isGroup: true },
            { key: "total_resistance_kn", label: "Total Resistance", unit: "kN", precision: 2 },
            { key: "effective_power_kw", label: "Effective Power", unit: "kW", precision: 1 },
            
            // Components
            { group: "Components", isGroup: true },
            { key: "frictional_resistance_kn", label: "Frictional", unit: "kN", precision: 2 },
            { key: "residuary_resistance_kn", label: "Residuary", unit: "kN", precision: 2,
              showIf: function(d) { return d && d.method === "holtrop"; } },
            { key: "pressure_resistance_kn", label: "Pressure", unit: "kN", precision: 2,
              showIf: function(d) { return d && d.method === "savitsky"; } },
            
            // Regime
            { group: "Operating Regime", isGroup: true },
            { key: "froude_number", label: "Froude Number", precision: 3 },
            { key: "froude_beam", label: "Froude (beam)", precision: 3,
              showIf: function(d) { return d && d.method === "savitsky"; } },
            { key: "regime", label: "Regime", format: function(v) { return v ? v.replace(/_/g, "-") : "—"; } },
            { key: "reynolds_number", label: "Reynolds Number", format: function(v) { return v ? v.toExponential(2) : "—"; } },
            
            // Method
            { group: "Calculation Method", isGroup: true },
            { key: "method", label: "Method", format: function(v) { return v ? v.charAt(0).toUpperCase() + v.slice(1) : "—"; } },
            { key: "method_valid", label: "Valid", format: function(v) { return v === true ? "Yes" : v === false ? "No" : "—"; } },
            { key: "validity_note", label: "Note", 
              showIf: function(d) { return d && d.validity_note; },
              format: function(v) { return v || "—"; } },
            
            // Planing-specific
            { group: "Planing Dynamics", isGroup: true, showIf: function(d) { return d && d.method === "savitsky"; } },
            { key: "running_trim_deg", label: "Running Trim", unit: "°", precision: 1,
              showIf: function(d) { return d && d.method === "savitsky"; } },
            { key: "wetted_length_m", label: "Wetted Length", unit: "m", precision: 2,
              showIf: function(d) { return d && d.method === "savitsky"; } },
            
            // Catamaran-specific
            { group: "Catamaran Interference", isGroup: true, showIf: function(d) { return d && d.interference_factor != null; } },
            { key: "interference_factor", label: "Interference τ", precision: 3,
              showIf: function(d) { return d && d.interference_factor != null; } },
            { key: "interference_note", label: "Note",
              showIf: function(d) { return d && d.interference_note; } }
        ]
    },

    // =========================================================================
    // STABILITY PANEL
    // =========================================================================
    stability: {
        title: "Stability",
        source: "stability",
        badge: {
            field: "imo_intact_passed",
            format: function(v) {
                if (v === true) return { text: "IMO Passed", type: "success" };
                if (v === false) return { text: "IMO Failed", type: "error" };
                return { text: "Not Evaluated", type: "neutral" };
            }
        },
        fields: [
            // GM
            { group: "Metacentric Height", isGroup: true },
            { key: "gm_transverse_m", label: "GM (solid)", unit: "m", precision: 3 },
            { key: "gm_corrected_m", label: "GM (corrected)", unit: "m", precision: 3 },
            { key: "fsc_m", label: "Free Surface Corr", unit: "m", precision: 3 },
            
            // Components
            { group: "GM Components", isGroup: true },
            { key: "kb_m", label: "KB", unit: "m", precision: 3 },
            { key: "bm_m", label: "BM", unit: "m", precision: 3 },
            { key: "kg_m", label: "KG", unit: "m", precision: 3 },
            
            // GZ curve
            { group: "Righting Arm (GZ)", isGroup: true },
            { key: "gz_max_m", label: "GZ max", unit: "m", precision: 3 },
            { key: "angle_gz_max_deg", label: "Angle of GZ max", unit: "°", precision: 1 },
            { key: "angle_of_vanishing_stability_deg", label: "Vanishing Angle", unit: "°", precision: 1 },
            
            // Areas
            { group: "Stability Areas", isGroup: true },
            { key: "area_0_30_m_rad", label: "Area 0-30°", unit: "m·rad", precision: 4 },
            { key: "area_0_40_m_rad", label: "Area 0-40°", unit: "m·rad", precision: 4 },
            { key: "area_30_40_m_rad", label: "Area 30-40°", unit: "m·rad", precision: 4 },
            
            // IMO check
            { group: "IMO Intact Criteria", isGroup: true },
            { key: "imo_intact_passed", label: "Passed", format: function(v) { return v === true ? "✓ Yes" : v === false ? "✗ No" : "—"; } },
            { key: "passes_gz_criteria", label: "GZ Criteria", format: function(v) { return v === true ? "✓" : v === false ? "✗" : "—"; } }
        ]
    },

    // =========================================================================
    // MISSION PANEL
    // =========================================================================
    mission: {
        title: "Mission Requirements",
        source: "mission",
        badge: null,
        fields: [
            { group: "Vessel", isGroup: true },
            { key: "vessel_type", label: "Type", format: function(v) { return v || "—"; } },
            { key: "loa", label: "LOA", unit: "m", precision: 1 },
            
            { group: "Performance", isGroup: true },
            { key: "max_speed_kts", label: "Max Speed", unit: "kts", precision: 1 },
            { key: "cruise_speed_kts", label: "Cruise Speed", unit: "kts", precision: 1 },
            { key: "range_nm", label: "Range", unit: "nm", precision: 0 },
            
            { group: "Capacity", isGroup: true },
            { key: "crew", label: "Crew", precision: 0 },
            { key: "crew_berthed", label: "Crew Berthed", precision: 0 },
            { key: "passengers", label: "Passengers", precision: 0 },
            { key: "cargo_capacity_mt", label: "Cargo", unit: "t", precision: 1 }
        ]
    },

    // =========================================================================
    // STRUCTURE PANEL (placeholder)
    // =========================================================================
    structure: {
        title: "Structure",
        source: "structure",
        badge: null,
        fields: [
            { key: "_placeholder", label: "Structure analysis", format: function() { return "Not yet implemented"; } }
        ]
    },

    // =========================================================================
    // ARRANGEMENT PANEL (placeholder)
    // =========================================================================
    arrangement: {
        title: "Arrangement",
        source: "arrangement",
        badge: null,
        fields: [
            { key: "_placeholder", label: "Arrangement data", format: function() { return "Not yet implemented"; } }
        ]
    }
};

// Make available globally (no module system in ui_v2)
window.PANEL_CONFIG = PANEL_CONFIG;

