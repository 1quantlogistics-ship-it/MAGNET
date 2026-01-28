/**
 * MAGNET UI v2 - Generic Config-Driven Panel Renderer
 * 
 * Uses PANEL_CONFIG to render any phase's data panel.
 * Integrates with existing MagnetStudio.setDataPanel() API.
 */

var PanelRenderer = (function() {
    'use strict';

    // =========================================================================
    // VALIDATION & SAFETY
    // =========================================================================

    /**
     * Validate that PANEL_CONFIG exists and has expected structure.
     */
    function validateConfig() {
        if (typeof window.PANEL_CONFIG !== 'object' || window.PANEL_CONFIG === null) {
            console.error('[PanelRenderer] PANEL_CONFIG not found. Ensure panel-config.js is loaded first.');
            return false;
        }
        return true;
    }

    /**
     * Safely get nested value from object using dot-notation path.
     * Returns undefined if any part of path is missing.
     */
    function safeGet(obj, path) {
        if (!obj || !path) return undefined;
        
        var parts = path.split('.');
        var current = obj;
        
        for (var i = 0; i < parts.length; i++) {
            if (current === null || current === undefined) return undefined;
            if (typeof current !== 'object') return undefined;
            current = current[parts[i]];
        }
        
        return current;
    }

    /**
     * Validate field configuration.
     */
    function validateFieldConfig(field, index, phaseId) {
        if (!field) {
            console.warn('[PanelRenderer] Null field at index ' + index + ' in ' + phaseId);
            return false;
        }
        if (field.isGroup || field.group) return true;  // Group headers are valid without key
        // Action-only fields are valid without key (e.g., "Apply" buttons)
        if (field.action) return true;
        if (!field.key) {
            console.warn('[PanelRenderer] Field missing "key" at index ' + index + ' in ' + phaseId);
            return false;
        }
        if (!field.label) {
            console.warn('[PanelRenderer] Field missing "label" for key "' + field.key + '" in ' + phaseId);
            return false;
        }
        return true;
    }

    // =========================================================================
    // FORMATTING
    // =========================================================================

    /**
     * Format a value for display.
     */
    function formatValue(value, field, sourceData) {
        // Custom formatter takes precedence
        if (typeof field.format === 'function') {
            try {
                return field.format(value, sourceData);
            } catch (e) {
                console.warn('[PanelRenderer] Format error for ' + field.key + ':', e);
                return "—";
            }
        }

        // Handle null/undefined
        if (value === null || value === undefined) {
            return "—";
        }

        // Handle booleans
        if (typeof value === 'boolean') {
            return value ? "Yes" : "No";
        }

        // Handle numbers with precision
        if (typeof value === 'number') {
            if (!isFinite(value)) return "—";
            var precision = typeof field.precision === 'number' ? field.precision : 2;
            return value.toFixed(precision);
        }

        // Handle strings
        if (typeof value === 'string') {
            return value || "—";
        }

        // Handle arrays (show length)
        if (Array.isArray(value)) {
            return "[" + value.length + " items]";
        }

        // Handle objects (show type)
        if (typeof value === 'object') {
            return "[object]";
        }

        return String(value);
    }

    /**
     * Determine if field should be shown based on showIf condition.
     */
    function shouldShowField(field, sourceData) {
        if (typeof field.showIf !== 'function') return true;
        
        try {
            return field.showIf(sourceData);
        } catch (e) {
            console.warn('[PanelRenderer] showIf error for ' + field.key + ':', e);
            return false;
        }
    }

    // =========================================================================
    // CARD GENERATION
    // =========================================================================

    /**
     * Generate cards array from config and data.
     */
    function generateCards(config, sourceData) {
        if (!config || !config.fields) {
            console.warn('[PanelRenderer] Invalid config or missing fields');
            return [];
        }

        var cards = [];
        var currentGroup = null;
        var skipUntilNextGroup = false;

        for (var i = 0; i < config.fields.length; i++) {
            var field = config.fields[i];

            // Validate field
            if (!validateFieldConfig(field, i, config.title)) {
                continue;
            }

            // Handle action cards (button rows)
            if (field.action) {
                // Respect showIf on action fields
                if (!shouldShowField(field, sourceData)) {
                    continue;
                }

                var action = field.action || {};
                var payload = {};
                try {
                    if (typeof action.payload === 'function') {
                        payload = action.payload(sourceData) || {};
                    } else if (typeof action.payload === 'object' && action.payload) {
                        payload = action.payload;
                    }
                } catch (e) {
                    console.warn('[PanelRenderer] Action payload error:', e);
                    payload = {};
                }

                var disabled = false;
                try {
                    if (typeof action.disabledIf === 'function') {
                        disabled = !!action.disabledIf(sourceData);
                    } else if (typeof action.disabled === 'boolean') {
                        disabled = action.disabled;
                    }
                } catch (e) {
                    console.warn('[PanelRenderer] Action disabledIf error:', e);
                    disabled = false;
                }

                cards.push({
                    label: field.label || action.label || "Action",
                    value: "",
                    unit: "",
                    group: currentGroup,
                    isAction: true,
                    action: {
                        event: action.event || "",
                        label: action.label || "Apply",
                        payload: payload,
                        disabled: disabled
                    }
                });
                continue;
            }

            // Handle group headers
            if (field.isGroup || (field.group && !field.key)) {
                // Check if group itself has showIf
                if (typeof field.showIf === 'function') {
                    if (!field.showIf(sourceData)) {
                        skipUntilNextGroup = true;
                        currentGroup = null;
                        continue;
                    }
                }
                skipUntilNextGroup = false;
                currentGroup = field.group;
                // Add group header card
                cards.push({
                    label: field.group,
                    value: "",
                    unit: "",
                    isGroup: true
                });
                continue;
            }

            // Skip fields if we're in a hidden group
            if (skipUntilNextGroup) {
                continue;
            }

            // Check showIf condition
            if (!shouldShowField(field, sourceData)) {
                continue;
            }

            // Get and format value
            var rawValue = safeGet(sourceData, field.key);
            var formattedValue = formatValue(rawValue, field, sourceData);

            cards.push({
                label: field.label,
                value: formattedValue,
                unit: field.unit || "",
                group: currentGroup
            });
        }

        return cards;
    }

    /**
     * Generate badge from config and data.
     */
    function generateBadge(config, sourceData) {
        var defaultBadge = { text: "Ready", type: "neutral" };

        if (!config.badge) return defaultBadge;

        var badgeConfig = config.badge;
        var value = safeGet(sourceData, badgeConfig.field);

        if (typeof badgeConfig.format === 'function') {
            try {
                var result = badgeConfig.format(value, sourceData);
                if (result && result.text) {
                    return result;
                }
            } catch (e) {
                console.warn('[PanelRenderer] Badge format error:', e);
            }
        }

        return defaultBadge;
    }

    // =========================================================================
    // MAIN RENDER FUNCTION
    // =========================================================================

    /**
     * Render a phase panel using config and design state.
     * 
     * @param {string} phaseId - Phase identifier (e.g., "hydrostatics")
     * @param {object} designState - Full design state from API
     * @returns {boolean} - True if render succeeded
     */
    function render(phaseId, designState) {
        // Validate prerequisites
        if (!validateConfig()) return false;

        if (!phaseId) {
            console.error('[PanelRenderer] phaseId is required');
            return false;
        }

        // Get config for this phase
        var config = window.PANEL_CONFIG[phaseId];
        if (!config) {
            console.warn('[PanelRenderer] No config for phase: ' + phaseId);
            return false;
        }

        // SINGLE-AUTHORITY: panels read from design.state flat map only.
        // For ergonomics, config may specify sourcePrefix (e.g. "hull.") and keys may be relative.
        var flat = (designState && typeof designState.state === 'object' && designState.state) ? designState.state : null;
        var sourceData = null;

        if (flat) {
            var prefix = null;
            if (typeof config.sourcePrefix === 'string' && config.sourcePrefix) {
                prefix = config.sourcePrefix;
            } else if (typeof config.source === 'string' && config.source) {
                // Back-compat: older configs used `source: "hull"` (nested). Treat as prefix.
                prefix = config.source.endsWith('.') ? config.source : (config.source + '.');
            }

            if (prefix) {
                sourceData = {};
                for (var k in flat) {
                    if (!Object.prototype.hasOwnProperty.call(flat, k)) continue;
                    if (k.indexOf(prefix) !== 0) continue;
                    sourceData[k.slice(prefix.length)] = flat[k];
                }
            } else {
                // No prefix: pass full flat map through.
                sourceData = flat;
            }
        } else if (designState && config.source) {
            // Final fallback (legacy): nested objects.
            sourceData = designState[config.source];
        }

        // Handle missing data gracefully
        if (!sourceData) {
            console.info('[PanelRenderer] No data for ' + phaseId + ' (sourcePrefix/source: ' + (config.sourcePrefix || config.source || 'none') + ')');
            
            if (typeof MagnetStudio !== 'undefined' && MagnetStudio.setDataPanel) {
                MagnetStudio.setDataPanel(
                    config.title || phaseId,
                    [{ label: "No data available", value: "Run phase to generate", unit: "" }],
                    { text: "No Data", type: "neutral" }
                );
            }
            return true;  // Not an error, just no data
        }

        // Generate cards and badge
        var cards = generateCards(config, sourceData);
        var badge = generateBadge(config, sourceData);

        // Render using existing MagnetStudio API
        if (typeof MagnetStudio !== 'undefined' && MagnetStudio.setDataPanel) {
            MagnetStudio.setDataPanel(config.title || phaseId, cards, badge);
            console.info('[PanelRenderer] Rendered ' + phaseId + ': ' + cards.length + ' cards');
            return true;
        } else {
            console.error('[PanelRenderer] MagnetStudio.setDataPanel not available');
            return false;
        }
    }

    /**
     * Get list of available phase configs.
     */
    function getAvailablePhases() {
        if (!validateConfig()) return [];
        return Object.keys(window.PANEL_CONFIG);
    }

    /**
     * Check if a phase has config.
     */
    function hasConfig(phaseId) {
        if (!validateConfig()) return false;
        return window.PANEL_CONFIG.hasOwnProperty(phaseId);
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    return {
        render: render,
        getAvailablePhases: getAvailablePhases,
        hasConfig: hasConfig,
        // Expose for testing/debugging
        _generateCards: generateCards,
        _generateBadge: generateBadge,
        _formatValue: formatValue,
        _safeGet: safeGet
    };

})();

// Make available globally
window.PanelRenderer = PanelRenderer;

