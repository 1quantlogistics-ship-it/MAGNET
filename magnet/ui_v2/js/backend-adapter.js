/**
 * MAGNET Backend Adapter v2
 * Translates between MAGNET backend WebSocket messages and MagnetStudio UI API
 *
 * Fixes addressed:
 * 1. Protocol-aware URLs (http/https → ws/wss)
 * 2. Auth token support
 * 3. Event handler deduplication
 * 4. Unknown message logging
 * 5. Validated API routes from api.py
 * 6. RunPod proxy URL format (no explicit port)
 * 7. Phase ID mapping (UI 'hull' ↔ backend 'hull_form')
 * 8. Validation response normalization
 */

/**
 * Phase ID Mapper - translates between UI phase IDs and backend phase IDs
 * UI v2 uses short names, backend uses full names
 */
const PhaseIdMapper = {
    // UI → Backend
    toBackend: {
        'mission': 'mission_requirements',
        'hull': 'hull_form',
        'hydrostatics': 'hydrostatics',
        'resistance': 'resistance_propulsion',
        'structure': 'structural_scantlings',
        'arrangement': 'general_arrangement',
        // Module 64: Add missing phases (verified from PHASE_DEPENDENCIES)
        'propulsion': 'propulsion',
        'systems': 'systems',
        'weight': 'weight_stability',
        'stability': 'weight_stability',
        'weight_stability': 'weight_stability',
        'compliance': 'compliance',
        'production': 'production'
    },
    // Backend → UI
    toUI: {
        'mission_requirements': 'mission',
        'hull_form': 'hull',
        'hydrostatics': 'hydrostatics',
        'resistance_propulsion': 'resistance',
        'structural_scantlings': 'structure',
        'general_arrangement': 'arrangement',
        // Module 64: Add missing phases
        'propulsion': 'propulsion',
        'systems': 'systems',
        'weight_stability': 'weight_stability',
        'compliance': 'compliance',
        'production': 'production'
    },
    // Convert UI phase ID to backend phase ID
    uiToBackend(uiPhase) {
        return this.toBackend[uiPhase] || uiPhase;
    },
    // Convert backend phase ID to UI phase ID
    backendToUI(backendPhase) {
        return this.toUI[backendPhase] || backendPhase;
    }
};

/**
 * Resolve base URLs for different deployment environments
 *
 * Module 65.2: Same-origin is the default (no config = use window.location.origin)
 * Handles RunPod proxy format: https://<pod>-8000.proxy.runpod.net (no explicit port)
 */
function resolveBaseUrls(config = {}) {
    const isSecure = window.location.protocol === 'https:';

    // Module 65.2: If no explicit host/baseUrl, use same-origin
    if (!config.host && !config.baseUrl) {
        console.log('[MAGNET] Using same-origin backend');
        return {
            baseUrl: window.location.origin,
            wsUrl: `${isSecure ? 'wss' : 'ws'}://${window.location.host}/ws`
        };
    }

    const hostname = config.host || window.location.hostname || 'localhost';

    // Check for RunPod proxy pattern: *-8000.proxy.runpod.net
    const isRunPodProxy = /^[\w-]+-\d+\.proxy\.runpod\.net$/.test(hostname);

    let baseUrl, wsUrl;

    if (config.baseUrl) {
        // Explicit URL provided - use as-is
        baseUrl = config.baseUrl;
        wsUrl = config.wsUrl || baseUrl.replace(/^http/, 'ws') + '/ws';
    } else if (isRunPodProxy) {
        // RunPod proxy: no explicit port needed (port is in hostname)
        baseUrl = `${isSecure ? 'https' : 'http'}://${hostname}`;
        wsUrl = `${isSecure ? 'wss' : 'ws'}://${hostname}/ws`;
        console.log(`[MAGNET] Detected RunPod proxy: ${hostname}`);
    } else {
        // Standard deployment: host:port
        const port = config.port || 8000;
        baseUrl = `${isSecure ? 'https' : 'http'}://${hostname}:${port}`;
        wsUrl = `${isSecure ? 'wss' : 'ws'}://${hostname}:${port}/ws`;
    }

    return { baseUrl, wsUrl };
}

class MAGNETBackendAdapter {
    constructor(config = {}) {
        // Resolve URLs with RunPod proxy support
        const { baseUrl, wsUrl } = resolveBaseUrls(config);
        this.baseUrl = baseUrl;
        this.wsUrl = wsUrl;

        this.designId = null;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;

        // Auth token (API key or Bearer token)
        this.authToken = config.authToken || localStorage.getItem('magnet-auth-token') || null;

        // Cached design state for panel rendering
        this.designState = null;

        // Guard against duplicate event bindings
        this._eventsBound = false;

        // Debug mode logs all messages
        this.debug = config.debug || false;

        // Session toggle for LLM guess auto-apply (default off until tests are green)
        // 67.7: LLM-first translator means most commands are LLM-sourced; auto-apply by default.
        this._autoApplyGuesses = true;
    }

    setAuthToken(token) {
        this.authToken = token;
        localStorage.setItem('magnet-auth-token', token);
    }

    async connect(designId) {
        this.designId = designId;

        // Build WebSocket URL with optional auth
        let wsEndpoint = `${this.wsUrl}/${designId}`;
        if (this.authToken) {
            wsEndpoint += `?token=${encodeURIComponent(this.authToken)}`;
        }

        // Connect WebSocket
        this.ws = new WebSocket(wsEndpoint);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            MagnetStudio.setConnection(true);
            MagnetStudio.terminal.success('Connected to MAGNET backend');
            console.log(`[MAGNET] WebSocket connected to ${this.wsUrl}/${designId}`);
        };

        this.ws.onclose = (event) => {
            MagnetStudio.setConnection(false);
            console.log(`[MAGNET] WebSocket closed: code=${event.code} reason=${event.reason}`);
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            MagnetStudio.terminal.error('WebSocket connection failed');
            console.error('[MAGNET] WebSocket error:', error);
            // Check for common issues
            if (window.location.protocol === 'file:') {
                console.error('[MAGNET] ERROR: Cannot connect WebSocket from file:// URL. Serve via HTTP.');
                MagnetStudio.terminal.error('Serve UI via HTTP (python -m http.server)');
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this.handleBackendMessage(msg);
            } catch (e) {
                console.error('[MAGNET] Failed to parse WebSocket message:', e, event.data);
            }
        };

        // Bind UI events ONCE (guard against reconnect duplication)
        if (!this._eventsBound) {
            this.bindUIEvents();
            this._eventsBound = true;
        }

        // Ensure 3D scene manager exists (do not silently skip geometry loads).
        // This is defensive against cases where Three.js/GLTF loader scripts were cached incorrectly
        // or the scene manager failed to initialize during DOMContentLoaded.
        if (!window.magnetThreeScene) {
            try {
                const SceneClass = window.MAGNETSceneManager || null;
                const canvas = (typeof MagnetStudio !== 'undefined' && MagnetStudio.getCanvasMount)
                    ? MagnetStudio.getCanvasMount()
                    : null;
                if (SceneClass && canvas) {
                    window.magnetThreeScene = new SceneClass(canvas);
                    console.log('[MAGNET] Scene manager initialized (late)');
                }
            } catch (e) {
                console.warn('[MAGNET] Failed to init scene manager (late):', e);
            }
        }

        // Module 64: Configure scene manager with design context for updateGeometry
        if (window.magnetThreeScene?.setDesignContext) {
            window.magnetThreeScene.setDesignContext(this.baseUrl, designId);
        }

        // Load initial state
        await this.loadDesignState();

        // ============================================================
        // Spiral UI wiring (new authority path)
        // - Uses /api/v1/designs/{id}/spiral/* for chat + sketch
        // - Keeps existing WebSocket + phase panel plumbing from MAGNETBackendAdapter
        // ============================================================
        this._ensureSpiralAdapter();
    }

    _ensureSpiralAdapter() {
        try {
            if (typeof window.SpiralAdapter !== 'function') return;
            // Recreate per design so it always has the current designId/baseUrl.
            window.magnetSpiral = new window.SpiralAdapter({
                designId: this.designId,
                baseUrl: this.baseUrl,
                sceneManager: window.magnetThreeScene,
                panels: {} // UIv2 uses PanelRenderer + cached state; panels are optional.
            });
        } catch (e) {
            console.warn('[MAGNET] Failed to init SpiralAdapter:', e);
        }
    }

    handleBackendMessage(msg) {
        const { type, payload = {}, message_id, design_id } = msg;

        if (this.debug) {
            console.log('[MAGNET] ←', type, payload);
        }

        switch (type) {
            // Phase events (from websocket.py MessageType enum)
            // Use PhaseIdMapper to translate backend phase IDs to UI phase IDs
            case 'phase_started': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase);
                MagnetStudio.setPhaseState(uiPhase, 'active', 'Running...');
                MagnetStudio.setStatus('Processing', 'processing');
                break;
            }

            case 'phase_completed': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase);
                MagnetStudio.setPhaseState(uiPhase, 'complete');
                MagnetStudio.terminal.success(`Phase ${uiPhase} completed`);
                MagnetStudio.setStatus('Ready');

                // Module 63.2: Load GLB after hull phase
                if ((uiPhase === 'hull' || payload.phase === 'hull_form') && window.magnetThreeScene) {
                    this._loadHullGeometry();
                }
                break;
            }

            case 'phase_failed': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase);
                MagnetStudio.setPhaseState(uiPhase, 'error', payload.error || payload.message);
                MagnetStudio.terminal.error(`Phase ${uiPhase} failed: ${payload.error || payload.message}`);
                MagnetStudio.setStatus('Error', 'error');
                break;
            }

            case 'phase_approved': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase);
                MagnetStudio.setPhaseState(uiPhase, 'complete', 'Approved');
                MagnetStudio.toast(`Phase ${uiPhase} approved`, 'success');
                break;
            }

            // Validation events - normalize response format
            // Backend returns: { validators_run: [...], results: {...}, contract_satisfied: bool }
            // UI expects: pass/fail state with detail string
            case 'validation_started': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase || payload.validator_id);
                MagnetStudio.setValidatorState(uiPhase, 'running');
                break;
            }

            case 'validation_completed': {
                const uiPhase = PhaseIdMapper.backendToUI(payload.phase || payload.validator_id);
                // Normalize validation response - handle both simple and structured formats
                let valState, detail;
                if (payload.contract_satisfied !== undefined) {
                    // Structured response from backend
                    valState = payload.contract_satisfied ? 'pass' : 'fail';
                    const failedCount = payload.results
                        ? Object.values(payload.results).filter(r => !r.passed).length
                        : 0;
                    detail = failedCount > 0 ? `${failedCount} issues` : '';
                } else {
                    // Simple response format
                    valState = payload.passed ? 'pass' : 'fail';
                    detail = payload.errors?.length ? `${payload.errors.length} issues` : '';
                }
                MagnetStudio.setValidatorState(uiPhase, valState, detail);
                break;
            }

            // Job events
            case 'job_submitted':
                MagnetStudio.showLoading(payload.job_type || 'Processing...');
                break;

            case 'job_started':
                MagnetStudio.showLoading(payload.job_type || 'Running...');
                break;

            case 'job_completed':
                MagnetStudio.hideLoading();
                MagnetStudio.toast(`${payload.job_type || 'Job'} complete`, 'success');
                break;

            case 'job_failed':
                MagnetStudio.hideLoading();
                MagnetStudio.terminal.error(payload.error || payload.message || 'Job failed');
                break;

            // Design events
            case 'design_created':
            case 'design_updated':
                MagnetStudio.terminal.info(`Design ${type.split('_')[1]}`);
                // Optionally refresh state
                this.loadDesignState();
                break;

            case 'design_deleted':
                MagnetStudio.terminal.error('Design deleted');
                break;

            // Geometry events
            case 'snapshot_created':
                // Trigger geometry refresh - updateGeometry fetches GLB internally
                if (window.magnetThreeScene?.updateGeometry) {
                    window.magnetThreeScene.updateGeometry(payload);
                    MagnetStudio.terminal.info('Geometry update triggered');
                } else {
                    console.warn('[MAGNET] snapshot_created: scene manager not ready');
                }
                break;

            // Connection events
            case 'connect':
                MagnetStudio.setConnection(true);
                break;

            case 'disconnect':
                MagnetStudio.setConnection(false);
                break;

            case 'ping':
                this.ws.send(JSON.stringify({ type: 'pong' }));
                break;

            case 'pong':
                // Heartbeat response, ignore
                break;

            // Error events
            case 'error':
                MagnetStudio.terminal.error(payload.message || 'Unknown error');
                MagnetStudio.setStatus('Error', 'error');
                break;

            // UNKNOWN MESSAGE - log it, don't silently drop
            default:
                console.warn(`[MAGNET] Unhandled message type: "${type}"`, msg);
                if (this.debug) {
                    MagnetStudio.terminal.info(`[debug] Unknown: ${type}`);
                }
        }
    }

    bindUIEvents() {
        console.log('[MAGNET] bindUIEvents() called');
        console.log('[MAGNET] MagnetStudio available:', typeof MagnetStudio !== 'undefined');
        console.log('[MAGNET] MagnetStudio.on available:', typeof MagnetStudio?.on === 'function');
        
        MagnetStudio.on('command', async (data) => {
            const command = data?.command || data;
            try {
            console.log('[MAGNET] Command handler triggered:', command);
            MagnetStudio.setStatus('Processing', 'processing');

            // Auto-create design if none exists
            if (!this.designId) {
                MagnetStudio.terminal.info('No design loaded. Creating new design...');
                try {
                    const newDesign = await this.post('/api/v1/designs', {
                        name: 'New Design',
                        type: 'monohull'
                    });
                    if (newDesign.design_id) {
                        this.designId = newDesign.design_id;
                        const v = newDesign.design_version || 1;
                        MagnetStudio.terminal.success(`══ NEW DESIGN ══`);
                        MagnetStudio.terminal.success(`ID: ${this.designId} (v${v})`);
                        // Update URL immediately (single authority)
                        try {
                            const url = new URL(window.location.href);
                            url.searchParams.set('design', this.designId);
                            window.history.replaceState({}, '', url.toString());
                            MagnetStudio.terminal.info(`URL updated: ?design=${this.designId}`);
                        } catch (e) { /* ignore */ }
                        // Load initial state
                        await this.loadDesignState();
                    } else {
                        MagnetStudio.terminal.error('Failed to create design');
                MagnetStudio.setStatus('Error', 'error');
                MagnetStudio.terminal.cursor();
                return;
                    }
                } catch (e) {
                    MagnetStudio.terminal.error(`Failed to create design: ${e.message}`);
                    MagnetStudio.setStatus('Error', 'error');
                    MagnetStudio.terminal.cursor();
                    return;
                }
            }

            const cmd = command.trim().toLowerCase();

            // Create new design command
            if (cmd === 'new' || cmd === 'new design' || cmd.startsWith('create new design')) {
                MagnetStudio.terminal.info('Creating new design...');
                try {
                    const newDesign = await this.post('/api/v1/designs', {
                        name: 'New Design',
                        type: 'monohull'
                    });
                    if (newDesign.design_id) {
                        this.designId = newDesign.design_id;
                        MagnetStudio.terminal.success(`Created design: ${this.designId}`);
                        // Update URL
                        try {
                            const url = new URL(window.location.href);
                            url.searchParams.set('design', this.designId);
                            window.history.replaceState({}, '', url.toString());
                        } catch (e) { /* ignore */ }
                        await this.loadDesignState();
                    }
                } catch (e) {
                    MagnetStudio.terminal.error(`Failed: ${e.message}`);
                }
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // Reset to brand-new blank design (explicitly requested for clean testing)
            if (cmd === 'reset' || cmd === 'reset design' || cmd === 'new blank') {
                MagnetStudio.terminal.info('Resetting to a brand-new blank design...');
                try {
                    const newDesign = await this.post('/api/v1/designs', {
                        name: 'Blank Design',
                        type: 'monohull'
                    });
                    if (newDesign.design_id) {
                        this.designId = newDesign.design_id;
                        MagnetStudio.terminal.success(`══ BLANK DESIGN ══`);
                        MagnetStudio.terminal.success(`ID: ${this.designId} (v${newDesign.design_version || 1})`);
                        try {
                            const url = new URL(window.location.href);
                            url.searchParams.set('design', this.designId);
                            window.history.replaceState({}, '', url.toString());
                        } catch (e) { /* ignore */ }
                        await this.loadDesignState();
                        await this._loadHullGeometry();
                    } else {
                        MagnetStudio.terminal.error('Failed to create blank design');
                    }
                } catch (e) {
                    MagnetStudio.terminal.error(`Reset failed: ${e.message}`);
                }
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // Module 64: Reload geometry command
            if (cmd === 'reload' || cmd === 'reload geometry') {
                await this._loadHullGeometry();
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // Force server-side geometry regeneration (clears in-memory mesh cache)
            // This avoids "looks the same" confusion due to per-process caching + browser caching.
            if (cmd === 'clear geometry cache' || cmd === 'clear geo cache' || cmd === 'clear cache') {
                try {
                    if (!this.designId) throw new Error('No design loaded');
                    await this.delete(`/api/v1/designs/${this.designId}/3d/cache`);
                    MagnetStudio.terminal.success('Geometry cache cleared (server). Reloading geometry...');
                    await this._loadHullGeometry();
                } catch (e) {
                    MagnetStudio.terminal.error(`Cache clear failed: ${e.message || e}`);
                }
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // Undo / revert commands
            if (cmd === 'undo' || cmd === 'revert' || cmd === 'go back') {
                await this._undo();
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            if (cmd.startsWith('restore version')) {
                const parts = cmd.split(' ');
                const versionStr = parts[parts.length - 1];
                const versionNum = parseInt(versionStr, 10);
                if (!isNaN(versionNum)) {
                    await this._restoreVersion(versionNum);
                    MagnetStudio.setStatus('Ready');
                    MagnetStudio.terminal.cursor();
                    return;
                }
            }

            if (cmd === 'auto-apply guesses on') {
                this._autoApplyGuesses = true;
                MagnetStudio.terminal.info('Auto-apply guesses: ON (session)');
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            if (cmd === 'auto-apply guesses off') {
                this._autoApplyGuesses = false;
                MagnetStudio.terminal.info('Auto-apply guesses: OFF (session)');
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            if (cmd === 'auto-apply guesses status') {
                MagnetStudio.terminal.info(`Auto-apply guesses is ${this._autoApplyGuesses ? 'ON' : 'OFF'}`);
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // Control Plane v1.1: "Why" query routing
            if (this._isWhyQuery(cmd)) {
                await this._handleWhyQuery(command);
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
                return;
            }

            // ============================================================
            // NEW AUTHORITY: design spiral (chat → propose → compile → validate → GLB)
            // ============================================================
            try {
                if (window.magnetSpiral && typeof window.magnetSpiral.sendChat === 'function') {
                    await window.magnetSpiral.sendChat(command);
                } else {
                    // Fallback if spiral-adapter.js isn't loaded for some reason:
                    const resp = await this.post(`/api/v1/designs/${this.designId}/spiral/chat`, {
                        message: command,
                        expected_version: this._lastDesignVersion ?? null,
                        request_id: (crypto?.randomUUID?.() ?? String(Date.now())),
                        force_apply: true,
                    });
                    // Best-effort: update version + trigger geometry load
                    if (resp?.design_version_after !== undefined) {
                        this._lastDesignVersion = resp.design_version_after;
                        window.magnetThreeScene?.setDesignVersion?.(resp.design_version_after);
                    }
                    await this._loadHullGeometry();
                }
            } catch (error) {
                MagnetStudio.terminal.error(error.message || String(error));
            }

            MagnetStudio.setStatus('Ready');
            MagnetStudio.terminal.cursor();
            } catch (outerError) {
                console.error('[MAGNET] Unhandled error in command handler:', outerError);
                MagnetStudio.terminal.error(`Error: ${outerError.message || outerError}`);
                MagnetStudio.setStatus('Error', 'error');
                MagnetStudio.terminal.cursor();
            }
        });

        // Spiral sketch upload wiring (emitted by index.html §SKELETON:UIWiring)
        MagnetStudio.on('sketchUpload', async ({ file, annotations }) => {
            try {
                if (!file) return;
                MagnetStudio.setStatus('Processing', 'processing');
                if (window.magnetSpiral && typeof window.magnetSpiral.sendSketch === 'function') {
                    await window.magnetSpiral.sendSketch(file, annotations || '');
                } else {
                    MagnetStudio.terminal.error('Sketch upload unavailable (SpiralAdapter not loaded)');
                }
            } catch (e) {
                MagnetStudio.terminal.error(e.message || String(e));
            } finally {
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
            }
        });

        // Phase navigation - VALIDATED: POST /api/v1/designs/{id}/phases/{phase}/run exists
        // Use PhaseIdMapper to translate UI phase to backend phase
        MagnetStudio.on('phaseChange', async ({ phase }) => {
            // === NEW: Render panel for the selected phase ===
            this._renderCurrentPhasePanel();
            
            try {
                const backendPhase = PhaseIdMapper.uiToBackend(phase);
                await this.post(`/api/v1/designs/${this.designId}/phases/${backendPhase}/run`, {});
                
                // === NEW: Refresh design state and re-render panel after phase run ===
                await this.loadDesignState();
            } catch (error) {
                MagnetStudio.terminal.error(`Failed to run phase: ${error.message}`);
            }
        });

        // Validator click - VALIDATED: POST /api/v1/designs/{id}/phases/{phase}/validate exists
        // Use PhaseIdMapper to translate UI phase to backend phase
        MagnetStudio.on('validatorClick', async ({ validator }) => {
            try {
                // Get current phase from UI state and translate to backend phase
                const state = MagnetStudio.getState();
                const uiPhase = state.currentPhase || 'hull';
                const backendPhase = PhaseIdMapper.uiToBackend(uiPhase);
                await this.post(`/api/v1/designs/${this.designId}/phases/${backendPhase}/validate`, {});
            } catch (error) {
                MagnetStudio.terminal.error(`Validation failed: ${error.message}`);
            }
        });

        // Export - VALIDATED: GET /api/v1/designs/{id}/3d/export/{format} exists
        MagnetStudio.on('export', async ({ format }) => {
            MagnetStudio.toast(`Exporting ${format.toUpperCase()}...`);
            try {
                const blob = await this.getBlob(`/api/v1/designs/${this.designId}/3d/export/${format}`);
                this.downloadBlob(blob, `design.${format}`);
                MagnetStudio.toast('Export complete', 'success');
            } catch (error) {
                MagnetStudio.toast(`Export failed: ${error.message}`, 'error');
            }
        });

        // Save - Use design update endpoint
        // NOTE: PATCH /api/v1/designs/{id} expects {path, value} not empty body
        MagnetStudio.on('save', async () => {
            try {
                // For now, just confirm design exists (GET is safe)
                await this.get(`/api/v1/designs/${this.designId}`);
                MagnetStudio.toast('Design state confirmed', 'success');
            } catch (error) {
                MagnetStudio.toast(`Save failed: ${error.message}`, 'error');
            }
        });

        // Advisor action: apply equilibrium draft to hull.draft (explicit user action)
        MagnetStudio.on('applyEquilibriumDraft', async ({ draft_m }) => {
            try {
                if (!this.designId) throw new Error('No design loaded');
                const nextDraft = Number(draft_m);
                if (!isFinite(nextDraft)) throw new Error('Invalid equilibrium draft');

                MagnetStudio.setStatus('Applying draft…', 'processing');
                MagnetStudio.terminal.info(`Applying equilibrium draft: ${nextDraft.toFixed(3)} m`);

                // Patch canonical state
                await this.patch(`/api/v1/designs/${this.designId}`, {
                    path: 'hull.draft',
                    value: nextDraft
                });

                // Re-run dependent phases so outputs are not stale (draft affects hydrostatics → resistance/stability).
                // Keep this explicit and finite (do not try to "run everything").
                const phasesToRun = ['hydrostatics', 'resistance', 'weight_stability'];
                for (const uiPhase of phasesToRun) {
                    try {
                        const backendPhase = PhaseIdMapper.uiToBackend(uiPhase);
                        await this.post(`/api/v1/designs/${this.designId}/phases/${backendPhase}/run`, {});
                    } catch (e) {
                        console.warn(`[MAGNET] Phase rerun after draft apply failed (${uiPhase}):`, e?.message || e);
                    }
                }

                await this.loadDesignState();
                MagnetStudio.toast('Draft updated', 'success');
            } catch (error) {
                MagnetStudio.toast(`Apply failed: ${error.message || error}`, 'error');
            } finally {
                MagnetStudio.setStatus('Ready');
                MagnetStudio.terminal.cursor();
            }
        });

        // View mode changes (shaded, wireframe, flat)
        MagnetStudio.on('viewChange', ({ mode }) => {
            // Some callers emit viewChange without a mode during init/reconnect.
            // Avoid spamming the terminal with "undefined".
            if (!mode) return;
            if (window.magnetThreeScene?.setViewMode) {
                window.magnetThreeScene.setViewMode(mode);
                MagnetStudio.terminal.info(`View mode: ${mode}`);
            }
        });

        // Layer visibility toggles (hull, deck, structure)
        MagnetStudio.on('layerToggle', ({ layer, visible }) => {
            if (window.magnetThreeScene?.setLayerVisibility) {
                window.magnetThreeScene.setLayerVisibility(layer, visible);
                MagnetStudio.terminal.info(`Layer '${layer}': ${visible ? 'visible' : 'hidden'}`);
            }
        });
    }

    // Undo last version
    async _undo() {
        try {
            const result = await this.post(`/api/v1/designs/${this.designId}/undo`, {});
            if (result.success) {
                const v = result.design_version;
                this._lastDesignVersion = v;
                window.magnetThreeScene?.setDesignVersion?.(v);
                MagnetStudio.terminal.success(`Reverted to version ${v}`);
                await this._loadHullGeometry();
            } else {
                MagnetStudio.terminal.error('Undo failed');
            }
        } catch (error) {
            MagnetStudio.terminal.error(error.message || 'Undo failed');
        }
    }

    // Restore specific version
    async _restoreVersion(version) {
        try {
            const result = await this.post(`/api/v1/designs/${this.designId}/versions/${version}/restore`, {});
            if (result.success) {
                const v = result.design_version;
                this._lastDesignVersion = v;
                window.magnetThreeScene?.setDesignVersion?.(v);
                MagnetStudio.terminal.success(`Restored version ${v}`);
                await this._loadHullGeometry();
            } else {
                MagnetStudio.terminal.error('Restore failed');
            }
        } catch (error) {
            MagnetStudio.terminal.error(error.message || 'Restore failed');
        }
    }

    // Module 63.2: Apply pending preview via /actions endpoint
    async _applyPreview(preview) {
        if (!preview?.apply_payload) {
            MagnetStudio.terminal.error('No apply payload to execute');
            return;
        }

        MagnetStudio.terminal.info('Applying changes...');

        try {
            const result = await this.post(
                `/api/v1/designs/${this.designId}/actions`,
                preview.apply_payload
            );

            if (result.success) {
                MagnetStudio.terminal.success('Applied');

                // Module 64: Echo design version for confirmation AND store for cache-busting
                if (result.design_version_after !== undefined) {
                    this._lastDesignVersion = result.design_version_after;
                    // Also update scene manager for snapshot_created triggers
                    window.magnetThreeScene?.setDesignVersion?.(result.design_version_after);

                    if (result.design_version_before !== undefined) {
                        MagnetStudio.terminal.info(`Design version: ${result.design_version_before} → ${result.design_version_after}`);
                    }
                }

                // Auto-run phase if hull params changed
                const phase = this._getPhaseToRun(result.actions_executed);
                if (phase) {
                    MagnetStudio.terminal.info(`Running ${phase} phase...`);
                    const backendPhase = PhaseIdMapper.uiToBackend(phase);
                    await this.post(`/api/v1/designs/${this.designId}/phases/${backendPhase}/run`, {});
                }

                // Auto-refresh geometry after commit
                await this._loadHullGeometry();
                
                // === NEW: Refresh design state to update data panels ===
                // This fetches fresh state and updates panel rendering
                try {
                    const design = await this.get(`/api/v1/designs/${this.designId}`);
                    this.designState = design;
                    this._renderCurrentPhasePanel();
                } catch (e) {
                    console.warn('[MAGNET] Failed to refresh state for panels:', e.message);
                }
            } else {
                MagnetStudio.terminal.error('Apply failed');
                if (result.rejections?.length) {
                    result.rejections.forEach(r => {
                        MagnetStudio.terminal.error(`${r.path}: ${r.reason}`);
                    });
                }
            }
        } catch (error) {
            const msg = error.message || '';
            if (msg.includes('409')) {
                MagnetStudio.terminal.error('Design changed since preview');
                MagnetStudio.terminal.info('Re-enter your command to preview current state');
            } else if (msg.includes('423')) {
                MagnetStudio.terminal.error('Parameter is locked');
            } else {
                MagnetStudio.terminal.error(msg || 'Apply failed');
            }
        }
    }

    // Module 63.2: Detect which phase to run based on changed paths
    _getPhaseToRun(actions) {
        const HULL_PATHS = [
            // Core dimensions
            'hull.loa', 'hull.lwl', 'hull.beam', 'hull.draft',
            'hull.depth', 'hull.cb', 'hull.cp', 'hull.cm', 'hull.deadrise',
            'hull.deadrise_deg',
            'hull.deadrise_transom_deg',
            'hull.cwp',
            'hull.hull_spacing_m',
            'hull.hull_type',
            'hull.lcb_fraction',
            'hull.transom_beam_ratio',
            'hull.bow_entrance_deg',
            'hull.freeboard_m',
            'hull.draft_fwd_m',
            'hull.draft_aft_m',
            'hull.bow_flare_deg',
            'hull.stem_rake_deg',
            // Phase 2: Chine variations
            'hull.chine_type',
            'hull.chine_count',
            'hull.chine_style',
            // Phase 3: Bow forms
            'hull.bow_style',
            'hull.bow_facet_count',
            // Phase 4: Spray rails
            'hull.spray_rail_count',
            'hull.has_spray_rails',
            // Phase 5: Transom variations
            'hull.transom_style',
            'hull.transom_rake_deg',
            // Phase 6: Tumblehome, panels, deck
            'hull.tumblehome_enabled',
            'hull.tumblehome_angle_deg',
            'hull.tumblehome_start_ratio',
            'hull.panel_style',
            'hull.deck_enabled',
            'hull.deck_camber_m',
        ];
        const PROPULSION_PATHS = [
            'propulsion.total_installed_power_kw', 'propulsion.engine_count',
            'propulsion.propeller_count', 'propulsion.propeller_diameter'
        ];

        const iterableActions = Array.isArray(actions)
            ? actions
            : Array.isArray(actions?.actions)
              ? actions.actions
              : [];
        for (const action of iterableActions) {
            if (HULL_PATHS.includes(action.path)) return 'hull';
            if (PROPULSION_PATHS.includes(action.path)) return 'propulsion';
        }
        return null;
    }

    // Module 64: Load hull GLB with loading state and design_version cache-bust
    async _loadHullGeometry() {
        // Guard: Scene manager must be ready
        if (!window.magnetThreeScene?.loadGLB) {
            console.warn('[MAGNET] Scene manager not ready, skipping geometry load');
            MagnetStudio?.terminal?.error?.('3D viewer not ready (scene manager missing) — cannot load hull geometry.');
            MagnetStudio?.terminal?.info?.('Hard refresh the page. If it persists, Three.js/GLTFLoader may be blocked.');
            return;
        }

        MagnetStudio.showLoading('Loading 3D geometry...');
        try {
            // Use design_version for deterministic cache-busting, fallback to timestamp
            // GLB endpoint returns binary only - no JSON fields available
            const cacheBust = this._lastDesignVersion || Date.now();
            const lod = (localStorage.getItem('magnet-lod') || 'medium').toLowerCase();
            const url = `${this.baseUrl}/api/v1/designs/${this.designId}/3d/export/glb?lod=${encodeURIComponent(lod)}&v=${cacheBust}`;
            console.log('[MAGNET] Loading GLB from:', url);
            const stats = await window.magnetThreeScene.loadGLB(url);

            MagnetStudio.setViewportStats([
                { label: 'Vertices', value: stats.vertices.toLocaleString() },
                { label: 'Faces', value: stats.faces.toLocaleString() }
            ]);
            MagnetStudio.terminal.success('3D model loaded');
        } catch (error) {
            // Blank designs are expected to have no geometry until the first spiral program is applied.
            const msg = String(error?.message || '');
            if (msg.includes('404') || msg.includes('No geometry') || msg.includes('GeometryUnavailable')) {
                MagnetStudio.terminal.info('No geometry yet (blank design). Send a command to generate hull geometry.');
            } else {
                MagnetStudio.terminal.error(`Geometry failed: ${msg}`);
                MagnetStudio.terminal.info('Type "reload" to retry');
            }
        } finally {
            MagnetStudio.hideLoading();
        }
    }

    async loadDesignState() {
        console.log('[MAGNET] loadDesignState called for:', this.designId);
        try {
            // VALIDATED: GET /api/v1/designs/{id} exists
            const design = await this.get(`/api/v1/designs/${this.designId}`);
            console.log('[MAGNET] Design fetched:', design.metadata?.name || design.design_name || 'unknown');

            MagnetStudio.setProjectName(design.name || design.metadata?.name || 'Untitled Design');
            MagnetStudio.setFilename(`design_${this.designId}.magnet`);

            // Phase states might be nested differently
            // Use PhaseIdMapper to translate backend phase IDs to UI phase IDs
            const phaseStates = design.phase_states || design.phases || {};
            if (Object.keys(phaseStates).length > 0) {
                Object.entries(phaseStates).forEach(([backendPhase, status]) => {
                    const uiPhase = PhaseIdMapper.backendToUI(backendPhase);
                    const state = typeof status === 'string' ? status : status.state || status.status;
                    const message = typeof status === 'object' ? status.message : '';
                    MagnetStudio.setPhaseState(uiPhase, state, message);
                });
            }

            MagnetStudio.terminal.success('Design loaded');
            const designVersion = design.design_version ?? design.metadata?.design_version ?? 0;
            MagnetStudio.setStatus(`Ready (v${designVersion})`);
            MagnetStudio.terminal.info(`Design ${this.designId} v${designVersion}`);

            // === NEW: Store design state for panel rendering ===
            this.designState = design;
            console.info('[BackendAdapter] Design state cached for panel rendering');
            
            // === NEW: Render current phase panel if data view would be shown ===
            this._renderCurrentPhasePanel();

            // Auto-load geometry on connect
            // Attempt load and treat 404 as "no geometry yet" (silent fail)
            // GLB generates on-demand even if vision.geometry_generated=false
            console.log('[MAGNET] Attempting auto-load of geometry...');
            try {
                await this._loadHullGeometry();
                console.log('[MAGNET] Geometry auto-load SUCCESS');
            } catch (e) {
                // 404 = no geometry yet, not an error worth showing
                console.log('[MAGNET] Geometry auto-load error:', e.message);
                if (!e.message?.includes('404')) {
                    console.warn('[MAGNET] Geometry auto-load failed:', e.message);
                }
            }
        } catch (error) {
            console.error('[MAGNET] Failed to load design:', error);
            MagnetStudio.terminal.error(`Failed to load design: ${error.message}`);
        }
    }

    /**
     * Render the data panel for the current phase using cached design state.
     * Called on loadDesignState and on phase change.
     */
    _renderCurrentPhasePanel() {
        if (!this.designState) {
            console.info('[BackendAdapter] No design state cached, skipping panel render');
            return;
        }
        
        // Get current phase from MagnetStudio state
        var currentPhase = (typeof MagnetStudio !== 'undefined' && MagnetStudio.getState) 
            ? MagnetStudio.getState().currentPhase 
            : null;
        
        if (!currentPhase) {
            console.info('[BackendAdapter] No current phase, skipping panel render');
            return;
        }
        
        // Check if PanelRenderer is available
        if (typeof PanelRenderer === 'undefined') {
            console.warn('[BackendAdapter] PanelRenderer not loaded');
            return;
        }
        
        // Check if this phase has panel config
        if (!PanelRenderer.hasConfig(currentPhase)) {
            console.info('[BackendAdapter] No panel config for phase: ' + currentPhase);
            return;
        }
        
        // Render the panel
        PanelRenderer.render(currentPhase, this.designState);
    }

    // HTTP helpers with auth headers
    _getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        return headers;
    }

    async get(path) {
        const res = await fetch(`${this.baseUrl}${path}`, {
            headers: this._getHeaders()
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text.slice(0, 100)}`);
        }
        return res.json();
    }

    async post(path, data) {
        const res = await fetch(`${this.baseUrl}${path}`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text.slice(0, 100)}`);
        }
        return res.json();
    }

    async patch(path, data) {
        const res = await fetch(`${this.baseUrl}${path}`, {
            method: 'PATCH',
            headers: this._getHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text.slice(0, 100)}`);
        }
        return res.json();
    }

    async getBlob(path) {
        const headers = this._getHeaders();
        delete headers['Content-Type']; // Let browser set for blob
        const res = await fetch(`${this.baseUrl}${path}`, { headers });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        return res.blob();
    }

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // =========================================================================
    // Control Plane v1.1: Why Query Support
    // =========================================================================

    /**
     * Detect if a command is a "why" query
     * @param {string} cmd - Lowercase command
     * @returns {boolean}
     */
    _isWhyQuery(cmd) {
        const patterns = [
            /^why\s+/,
            /^what\s+is\s+/,
            /^what\s+does\s+/,
            /^explain\s+/,
            /^tell\s+me\s+about\s+/,
            /what\s+(caused|changed|happened)/,
            /history\s+of\s+/,
            /when\s+did\s+.+\s+change/,
            /what\s+changed\s+in\s+(version|v)\s*\d+/i,
        ];
        return patterns.some(p => p.test(cmd));
    }

    /**
     * Handle a "why" query via Control Plane /why endpoint
     * @param {string} query - Original user query
     */
    async _handleWhyQuery(query) {
        const T = MagnetStudio.terminal;
        T.info('Asking Control Plane...');

        try {
            // Call the /why endpoint with proper body format
            const url = `/api/v1/designs/${this.designId}/why`;
            const result = await this.post(url, {
                query: query,
                context_paths: this._whyContextPaths || [],
                context_version: this._whyContextVersion || null
            });

            // Handle clarification needed
            if (result.clarification) {
                T.info(result.clarification);
                return;
            }

            // Display results
            if (!result.results || result.results.length === 0) {
                T.info('No relevant information found.');
                return;
            }

            // Show intent for debugging
            if (this.debug) {
                T.info(`[debug] Intent: ${result.intent}`);
            }

            // Display each result
            result.results.forEach((r, i) => {
                if (result.results.length > 1 && r.path) {
                    T.info('');
                    T.info(`── ${r.path} ──`);
                }
                
                // Display narrative (may contain markdown-ish formatting)
                const lines = r.narrative.split('\n');
                lines.forEach(line => {
                    if (line.startsWith('**') && line.endsWith('**')) {
                        T.info(line.slice(2, -2));
                    } else if (line.startsWith('- ')) {
                        T.info('  • ' + line.slice(2));
                    } else if (line.trim()) {
                        T.info(line);
                    }
                });
            });

            if (result.truncated) {
                T.info('');
                T.info('(Results truncated. Ask about specific items for more detail.)');
            }

        } catch (error) {
            T.error(`Query failed: ${error.message}`);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 30000);
            MagnetStudio.terminal.info(`Reconnecting in ${Math.round(delay/1000)}s...`);
            setTimeout(() => {
                // Don't re-bind events on reconnect (guard is set)
                this.connect(this.designId);
            }, delay);
        } else {
            MagnetStudio.terminal.error('Max reconnection attempts reached');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Export for use in browser
window.MAGNETBackendAdapter = MAGNETBackendAdapter;
window.PhaseIdMapper = PhaseIdMapper;
window.resolveBaseUrls = resolveBaseUrls;
