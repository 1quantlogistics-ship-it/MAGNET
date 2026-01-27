/**
 * MAGNET Scene Manager
 * Minimal Three.js loader for GLB hull geometry
 * Module 63.2: UI Integration
 */

class MAGNETSceneManager {
    constructor(container) {
        this.container = container;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(
            45, container.clientWidth / container.clientHeight, 0.1, 1000
        );
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            logarithmicDepthBuffer: true  // Helps with z-fighting on overlapping geometry
        });
        // GLTFLoader location varies by Three.js version
        // r128+: THREE.GLTFLoader (from examples/js/loaders/GLTFLoader.js)
        // r160+: May need different access pattern
        const GLTFLoaderClass = THREE.GLTFLoader || window.GLTFLoader;
        if (!GLTFLoaderClass) {
            console.error('[MAGNET] GLTFLoader not found! Check Three.js version and loader script.');
        }
        this.loader = GLTFLoaderClass ? new GLTFLoaderClass() : null;
        this.hull = null;
        this._markersGroup = null;
        this._baseUrl = null;
        this._designId = null;
        this._showDiagnostics = true;

        this._init();
    }

    _init() {
        // Performance guard for laptops: cap pixel ratio (retina displays can explode fill-rate)
        const pr = Math.min(window.devicePixelRatio || 1, 2);
        this.renderer.setPixelRatio(pr);
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setClearColor(0x0a0a0a, 1);

        // Color management / tonemapping (r128-compatible fallbacks)
        try {
            if ('outputEncoding' in this.renderer && THREE.sRGBEncoding) {
                this.renderer.outputEncoding = THREE.sRGBEncoding;
            }
            if ('toneMapping' in this.renderer && THREE.ACESFilmicToneMapping) {
                this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
                this.renderer.toneMappingExposure = 1.0;
            }
            if ('physicallyCorrectLights' in this.renderer) {
                this.renderer.physicallyCorrectLights = true;
            }
        } catch (e) {
            // Non-fatal: keep defaults
        }

        this.container.appendChild(this.renderer.domElement);

        // Ensure canvas receives pointer events regardless of parent CSS
        this.renderer.domElement.style.pointerEvents = 'auto';

        // Studio lighting setup - bright enough to see hull details clearly
        // Ambient provides base visibility
        this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));
        
        // Hemisphere light for natural sky/ground gradient
        this.scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 0.5));

        // Key light - main illumination from upper right
        const key = new THREE.DirectionalLight(0xffffff, 0.9);
        key.position.set(10, 15, 10);
        this.scene.add(key);

        // Fill light - softer from opposite side
        const fill = new THREE.DirectionalLight(0xffffff, 0.5);
        fill.position.set(-8, 8, 8);
        this.scene.add(fill);

        // Back/rim light - highlights edges
        const rim = new THREE.DirectionalLight(0xffffff, 0.4);
        rim.position.set(0, 5, -15);
        this.scene.add(rim);

        // Camera
        this.camera.position.set(50, 30, 50);
        this.camera.lookAt(0, 0, 0);

        // Orbit controls
        if (THREE.OrbitControls) {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
        }

        window.addEventListener('resize', () => this._onResize());
        this._animate();
    }

    async loadGLB(url) {
        const response = await fetch(url, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} loading GLB`);
        }

        const headerDesignId = response.headers.get('X-Design-Id');
        const headerDesignVersion = response.headers.get('X-Design-Version');
        const headerGeometryMode = response.headers.get('X-Geometry-Mode');

        if (this._designId && headerDesignId && headerDesignId !== this._designId) {
            throw new Error(`Design mismatch: expected ${this._designId}, got ${headerDesignId}`);
        }

        if (this._designVersion !== undefined && headerDesignVersion && String(this._designVersion) !== headerDesignVersion) {
            throw new Error(`Design version mismatch: expected ${this._designVersion}, got ${headerDesignVersion}`);
        }

        const arrayBuffer = await response.arrayBuffer();

        let gltf;
        // GLTFLoader API varies by Three.js version. Some versions do not have parseAsync().
        if (typeof this.loader?.parseAsync === 'function') {
            gltf = await this.loader.parseAsync(arrayBuffer, '');
        } else if (typeof this.loader?.parse === 'function') {
            gltf = await new Promise((resolve, reject) => {
                this.loader.parse(arrayBuffer, '', resolve, reject);
            });
        } else {
            throw new Error('GLTFLoader parse API not available (missing parse/parseAsync)');
        }

        if (headerGeometryMode && headerGeometryMode !== 'authoritative') {
            MagnetStudio?.setStatus?.(`Non-authoritative geometry (${headerGeometryMode})`, 'warning');
            MagnetStudio?.terminal?.warning?.(`Geometry mode: ${headerGeometryMode}`);
        } else {
            MagnetStudio?.setStatus?.('Ready');
        }

        if (this.hull) this.scene.remove(this.hull);
        this.hull = gltf.scene;
        this.scene.add(this.hull);

        // Aluminum-like material that works WITHOUT environment maps (MacBook Air friendly)
        // Key insight: metalness=1.0 looks flat/white without envmap because metals reflect environment
        // Solution: Use moderate metalness + good lighting for convincing metal look
        const hullMaterial = new THREE.MeshStandardMaterial({
            color: 0x8899aa,         // Steel blue-gray (visible against dark background)
            side: THREE.DoubleSide,
            roughness: 0.5,          // Moderate roughness for diffuse reflection
            metalness: 0.4,          // Moderate metalness - reflects lights, not just environment
            flatShading: false,
            polygonOffset: true,
            polygonOffsetFactor: 1,
            polygonOffsetUnits: 1,
        });

        this.hull.traverse(child => {
            if (child.isMesh) {
                child.material = hullMaterial;
                // Ensure normals exist - compute if missing
                if (!child.geometry.attributes.normal) {
                    console.warn('[MAGNET] Missing normals, computing...');
                    child.geometry.computeVertexNormals();
                }
            }
        });

        // Center model
        const box = new THREE.Box3().setFromObject(this.hull);
        const center = box.getCenter(new THREE.Vector3());
        this.hull.position.sub(center);

        // Remove previous markers (if any)
        try {
            if (this._markersGroup) {
                this.scene.remove(this._markersGroup);
                this._markersGroup = null;
            }
        } catch (e) {}

        // Fit camera
        const size = box.getSize(new THREE.Vector3()).length();
        this.camera.position.set(size * 1.5, size * 0.75, size * 1.5);
        this.camera.lookAt(0, 0, 0);

        // Phase 3: load and render diagnostic primitives (openings/flow_paths/attachments)
        try {
            if (this._showDiagnostics && this._baseUrl && this._designId) {
                await this._loadAndRenderPrimitives({ center });
            }
        } catch (e) {
            // Non-fatal: primitives are diagnostic only.
            console.debug('[MAGNET] Primitive marker render skipped:', e?.message || e);
        }

        // Count stats
        let vertices = 0, faces = 0;
        this.hull.traverse(child => {
            if (child.isMesh && child.geometry) {
                vertices += child.geometry.attributes.position?.count || 0;
                faces += (child.geometry.index?.count || 0) / 3;
            }
        });

        return { vertices: Math.round(vertices), faces: Math.round(faces) };
    }

    /**
     * Clear current scene geometry for a design.
     *
     * Use this when:
     * - switching to a brand-new blank design (no geometry yet)
     * - a GLB load definitively indicates "no geometry" (404/GeometryUnavailable)
     *
     * Do NOT call this during normal "update in progress" retries (avoid flicker).
     */
    clear() {
        try {
            if (this.hull) {
                // Best-effort dispose (avoid GPU memory leaks on repeated design switches)
                try {
                    this.hull.traverse(child => {
                        if (child && child.isMesh) {
                            try { child.geometry?.dispose?.(); } catch (e) {}
                            try {
                                const mat = child.material;
                                if (Array.isArray(mat)) mat.forEach(m => m?.dispose?.());
                                else mat?.dispose?.();
                            } catch (e) {}
                        }
                    });
                } catch (e) {}

                try { this.scene.remove(this.hull); } catch (e) {}
                this.hull = null;
            }

            if (this._markersGroup) {
                try { this.scene.remove(this._markersGroup); } catch (e) {}
                this._markersGroup = null;
            }

            // Reset viewport stats / status
            try { MagnetStudio?.setViewportStats?.([]); } catch (e) {}
        } catch (e) {
            console.warn('[MAGNET] Scene clear failed:', e);
        }
    }

    /**
     * Configure design context so the scene manager can fetch /3d/scene metadata.
     * Called by backend-adapter.js after connect.
     */
    setDesignContext(baseUrl, designId) {
        const prev = this._designId;
        this._baseUrl = baseUrl;
        this._designId = designId;

        // Defensive: on design switch, immediately reset truth badge + clear stale geometry.
        // This prevents "authoritative carryover" when starting a new blank design.
        try {
            if (prev && designId && prev !== designId) {
                this.clear();
                MagnetStudio?.setTruthBadge?.('DECOUPLED', 'design_context_changed');
            }
        } catch (e) {}
    }

    setShowDiagnostics(enabled) {
        this._showDiagnostics = !!enabled;
    }

    async _loadAndRenderPrimitives({ center }) {
        // Engineering Truth: do not request visual-only fallback by default.
        const url = `${this._baseUrl}/api/v1/designs/${this._designId}/3d/scene?lod=medium&allow_visual_only=false&_t=` + Date.now();
        const resp = await fetch(url, { cache: 'no-store', method: 'GET' });
        if (!resp.ok) return;
        const payload = await resp.json();
        // Truth badge (scene.simulation_integrity)
        try {
            const integrity =
                payload?.data?.simulation_integrity ||
                payload?.data?.metadata?.simulation_integrity ||
                null;
            const reason = payload?.data?.metadata?.simulation_integrity_reason || null;
            MagnetStudio?.setTruthBadge?.(integrity, reason);
        } catch (e) {}
        const primitives = payload?.data?.metadata?.primitives || null;
        if (!primitives) return;
        this._renderPrimitiveMarkers(primitives, center);
    }

    _renderPrimitiveMarkers(primitives, center) {
        // primitives schema: { semantics, openings, flow_paths, attachments }
        const group = new THREE.Group();
        group.name = 'MAGNET_PrimitiveMarkers';

        // Match hull centering transform
        group.position.sub(center);

        const addSphere = (p, color, radius) => {
            const geom = new THREE.SphereGeometry(radius, 10, 10);
            const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 });
            const m = new THREE.Mesh(geom, mat);
            m.position.set(p[0], p[1], p[2]);
            group.add(m);
        };

        const addLine = (a, b, color) => {
            const pts = [new THREE.Vector3(a[0], a[1], a[2]), new THREE.Vector3(b[0], b[1], b[2])];
            const geom = new THREE.BufferGeometry().setFromPoints(pts);
            const mat = new THREE.LineBasicMaterial({ color });
            group.add(new THREE.Line(geom, mat));
        };

        // Scale marker size from hull bounding box if available
        let baseR = 0.25;
        try {
            const box = new THREE.Box3().setFromObject(this.hull);
            const diag = box.getSize(new THREE.Vector3()).length();
            baseR = Math.max(0.05, Math.min(0.6, diag * 0.01));
        } catch (e) {}

        const openings = primitives.openings || [];
        for (const o of openings) {
            const pos = o.position;
            if (Array.isArray(pos) && pos.length >= 3) {
                addSphere(pos, 0xffcc00, baseR);
            }
        }

        const flows = primitives.flow_paths || [];
        for (const f of flows) {
            const a = f.inlet_point;
            const b = f.outlet_point;
            if (Array.isArray(a) && a.length >= 3 && Array.isArray(b) && b.length >= 3) {
                addLine(a, b, 0x00ccff);
                addSphere(a, 0x00ccff, baseR * 0.6);
                addSphere(b, 0x00ccff, baseR * 0.6);
            }
        }

        const atts = primitives.attachments || [];
        for (const a of atts) {
            // Prefer explicit buoyancy_center (Phase 3B semantics); fallback to offsets (diagnostic-only)
            const bc = a.buoyancy_center;
            const p = (Array.isArray(bc) && bc.length >= 3)
                ? bc
                : [a.offset_x_m || 0, a.offset_y_m || 0, a.offset_z_m || 0];
            addSphere(p, 0xff44aa, baseR * 0.7);
        }

        this._markersGroup = group;
        this.scene.add(group);
    }

    _makeBrushedNormalTexture() {
        try {
            if (this._brushedNormalTex) return this._brushedNormalTex;
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 256;
            const ctx = canvas.getContext('2d');
            if (!ctx) return null;

            // Neutral normal map base (128,128,255)
            ctx.fillStyle = 'rgb(128,128,255)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Add subtle horizontal "brush" streaks by perturbing the red channel
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const d = img.data;
            for (let y = 0; y < canvas.height; y++) {
                // banded noise per row
                const rowNoise = (Math.random() - 0.5) * 10;
                for (let x = 0; x < canvas.width; x++) {
                    const i = (y * canvas.width + x) * 4;
                    const streak = Math.sin((x / canvas.width) * Math.PI * 12) * 3;
                    d[i + 0] = Math.max(0, Math.min(255, 128 + rowNoise + streak)); // R
                    d[i + 1] = 128; // G
                    d[i + 2] = 255; // B
                }
            }
            ctx.putImageData(img, 0, 0);

            const tex = new THREE.CanvasTexture(canvas);
            tex.wrapS = THREE.RepeatWrapping;
            tex.wrapT = THREE.RepeatWrapping;
            tex.repeat.set(6, 6);
            this._brushedNormalTex = tex;
            return tex;
        } catch (e) {
            return null;
        }
    }

    /**
     * Check if any mesh in the scene has UV coordinates
     * Used to decide between PBR (with normal maps) and matcap fallback
     */
    _checkGeometryHasUVs(sceneRoot) {
        let hasUVs = false;
        sceneRoot.traverse(child => {
            if (child.isMesh && child.geometry?.attributes?.uv) {
                hasUVs = true;
            }
        });
        return hasUVs;
    }

    // Module 64: Geometry update triggered by snapshot_created WS event
    updateGeometry(payload) {
        // snapshot_created payload: { snapshotId, timestamp, trigger }
        // NO url field - must fetch GLB ourselves
        console.log('[MAGNET] Geometry update triggered:', payload?.trigger || 'unknown');

        if (this._designId && this._baseUrl) {
            // Use design_version for deterministic cache-bust, fallback to timestamp
            const cacheBust = this._designVersion || Date.now();
            const url = `${this._baseUrl}/api/v1/designs/${this._designId}/3d/export/glb?v=${cacheBust}`;
            this.loadGLB(url);
        } else {
            console.warn('[MAGNET] updateGeometry: no designId/baseUrl configured');
        }
    }

    setDesignContext(baseUrl, designId) {
        this._baseUrl = baseUrl;
        this._designId = designId;
    }

    setDesignVersion(version) {
        this._designVersion = version;
    }

    /**
     * Toggle wireframe rendering mode
     * @param {boolean} enabled - Whether to show wireframe
     */
    setWireframe(enabled) {
        if (!this.hull) return;
        
        this.hull.traverse(child => {
            if (child.isMesh && child.material) {
                child.material.wireframe = enabled;
            }
        });
        console.log(`[MAGNET] Wireframe mode: ${enabled ? 'ON' : 'OFF'}`);
    }

    /**
     * Toggle flat shading (for faceted panel visualization)
     * @param {boolean} enabled - Whether to use flat shading
     */
    setFlatShading(enabled) {
        if (!this.hull) return;
        
        this.hull.traverse(child => {
            if (child.isMesh && child.material) {
                child.material.flatShading = enabled;
                child.material.needsUpdate = true;
            }
        });
        console.log(`[MAGNET] Flat shading: ${enabled ? 'ON' : 'OFF'}`);
    }

    /**
     * Set layer visibility
     * @param {string} layer - Layer name ('hull', 'deck', 'structure', 'waterline')
     * @param {boolean} visible - Whether layer should be visible
     */
    setLayerVisibility(layer, visible) {
        if (!this.hull) return;
        
        this.hull.traverse(child => {
            if (child.isMesh) {
                const name = (child.name || '').toLowerCase();
                // Match by mesh name containing layer keyword
                if (layer === 'hull' && (name.includes('hull') || name === '')) {
                    child.visible = visible;
                } else if (layer === 'deck' && name.includes('deck')) {
                    child.visible = visible;
                } else if (layer === 'structure' && (name.includes('frame') || name.includes('stringer'))) {
                    child.visible = visible;
                }
            }
        });
        console.log(`[MAGNET] Layer '${layer}' visibility: ${visible}`);
    }

    /**
     * Set view mode (shaded, wireframe, etc.)
     * @param {string} mode - View mode ('shaded', 'wireframe', 'flat')
     */
    setViewMode(mode) {
        switch (mode) {
            case 'wireframe':
                this.setWireframe(true);
                this.setFlatShading(false);
                break;
            case 'flat':
                this.setWireframe(false);
                this.setFlatShading(true);
                break;
            case 'shaded':
            default:
                this.setWireframe(false);
                this.setFlatShading(false);
                break;
        }
    }

    _onResize() {
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    _animate() {
        requestAnimationFrame(() => this._animate());
        if (this.controls) this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}

// Ensure availability as a window property (some browsers treat top-level `class` as a global lexical binding,
// not a `window.*` property; the UI init prefers window.MAGNETSceneManager when available).
window.MAGNETSceneManager = MAGNETSceneManager;
