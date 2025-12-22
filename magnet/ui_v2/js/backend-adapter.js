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

        // Guard against duplicate event bindings
        this._eventsBound = false;

        // Debug mode logs all messages
        this.debug = config.debug || false;
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

        // Module 64: Configure scene manager with design context for updateGeometry
        if (window.magnetThreeScene?.setDesignContext) {
            window.magnetThreeScene.setDesignContext(this.baseUrl, designId);
        }

        // Load initial state
        await this.loadDesignState();
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
        // Module 63.2: Intent preview/apply flow
        this._pendingPreview = null;

        MagnetStudio.on('command', async ({ command }) => {
            console.log('[MAGNET] Command handler triggered:', command);
            MagnetStudio.setStatus('Processing', 'processing');
            MagnetStudio.terminal.print(`> ${command}`);

            if (!this.designId) {
                MagnetStudio.terminal.error('No design selected. Add ?design= or pick a design first.');
                MagnetStudio.setStatus('Error', 'error');
                MagnetStudio.terminal.cursor();
                return;
            }

            const cmd = command.trim().toLowerCase();

            // Module 64: Reload geometry command
            if (cmd === 'reload' || cmd === 'reload geometry') {
                await this._loadHullGeometry();
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

            // Natural language → validate then auto-apply (compound mode)
            try {
                console.log('[MAGNET] Sending command to API:', command);
                const preview = await this.post(
                    `/api/v1/designs/${this.designId}/intent/preview`,
                    { text: command, mode: 'compound' }
                );
                console.log('[MAGNET] API Response:', preview);

                const approved = preview.approved || [];
                const proposed = preview.proposed_actions || [];
                const hasActions = approved.length || proposed.length;

                if (!hasActions) {
                    MagnetStudio.terminal.info(preview.guidance || 'No actions recognized');
                    MagnetStudio.terminal.info('Try: "60m aluminum catamaran ferry"');
                    MagnetStudio.setStatus('Ready');
                    MagnetStudio.terminal.cursor();
                    return;
                }

                // Show understanding
                if (approved.length) {
                    MagnetStudio.terminal.info('MAGNET understood:');
                    approved.forEach(a => {
                        MagnetStudio.terminal.data([
                            { key: a.path, value: `${a.value}${a.unit ? ' ' + a.unit : ''}` }
                        ]);
                    });
                }

                if (preview.rejected?.length) {
                    MagnetStudio.terminal.info('');
                    preview.rejected.forEach(r => {
                        MagnetStudio.terminal.error(`${r.action?.path || 'unknown'}: ${r.reason}`);
                    });
                }

                if (preview.missing_required?.length) {
                    MagnetStudio.terminal.info('');
                    MagnetStudio.terminal.info('MAGNET needs:');
                    preview.missing_required.forEach(m => {
                        MagnetStudio.terminal.info(`  ○ ${m.path}: ${m.reason}`);
                    });
                }

                if (preview.unsupported_mentions?.length) {
                    MagnetStudio.terminal.info('');
                    MagnetStudio.terminal.info("MAGNET can't yet model:");
                    preview.unsupported_mentions.forEach(u => {
                        MagnetStudio.terminal.info(`  "${u.text}" → ${u.future || 'future support'}`);
                    });
                }

                if (preview.warnings?.length) {
                    preview.warnings.forEach(w => MagnetStudio.terminal.info(`⚠ ${w}`));
                }

                if (!preview.apply_payload) {
                    MagnetStudio.terminal.error('No apply payload returned; nothing applied');
                    MagnetStudio.setStatus('Ready');
                    MagnetStudio.terminal.cursor();
                    return;
                }

                // Auto-apply immediately
                await this._applyPreview(preview);

            } catch (error) {
                MagnetStudio.terminal.error(error.message);
            }

            MagnetStudio.setStatus('Ready');
            MagnetStudio.terminal.cursor();
        });

        // Phase navigation - VALIDATED: POST /api/v1/designs/{id}/phases/{phase}/run exists
        // Use PhaseIdMapper to translate UI phase to backend phase
        MagnetStudio.on('phaseChange', async ({ phase }) => {
            try {
                const backendPhase = PhaseIdMapper.uiToBackend(phase);
                await this.post(`/api/v1/designs/${this.designId}/phases/${backendPhase}/run`, {});
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
            'hull.loa', 'hull.lwl', 'hull.beam', 'hull.draft',
            'hull.depth', 'hull.cb', 'hull.cp', 'hull.cm', 'hull.deadrise'
        ];
        const PROPULSION_PATHS = [
            'propulsion.total_installed_power_kw', 'propulsion.engine_count',
            'propulsion.propeller_count', 'propulsion.propeller_diameter'
        ];

        for (const action of actions || []) {
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
            return;
        }

        MagnetStudio.showLoading('Loading 3D geometry...');
        try {
            // Use design_version for deterministic cache-busting, fallback to timestamp
            // GLB endpoint returns binary only - no JSON fields available
            const cacheBust = this._lastDesignVersion || Date.now();
            const url = `${this.baseUrl}/api/v1/designs/${this.designId}/3d/export/glb?v=${cacheBust}`;
            console.log('[MAGNET] Loading GLB from:', url);
            const stats = await window.magnetThreeScene.loadGLB(url);

            MagnetStudio.setViewportStats([
                { label: 'Vertices', value: stats.vertices.toLocaleString() },
                { label: 'Faces', value: stats.faces.toLocaleString() }
            ]);
            MagnetStudio.terminal.success('3D model loaded');
        } catch (error) {
            MagnetStudio.terminal.error(`Geometry failed: ${error.message}`);
            MagnetStudio.terminal.info('Type "reload" to retry');
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
