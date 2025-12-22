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

        this._init();
    }

    _init() {
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setClearColor(0x0a0a0a, 1);
        this.container.appendChild(this.renderer.domElement);

        // Ensure canvas receives pointer events regardless of parent CSS
        this.renderer.domElement.style.pointerEvents = 'auto';

        // Lights - bright ambient for CAD-style visibility
        this.scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        // Hemisphere light for even illumination from all angles
        this.scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 0.6));
        // Directional lights from multiple angles
        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.5);
        dirLight1.position.set(5, 10, 7);
        this.scene.add(dirLight1);
        const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        dirLight2.position.set(-5, -10, -7);
        this.scene.add(dirLight2);

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

        const gltf = await this.loader.parseAsync(arrayBuffer, '');

        if (this.hull) this.scene.remove(this.hull);
        this.hull = gltf.scene;
        this.scene.add(this.hull);

        // Replace all materials with lit standard material - uses normals for shading
        const hullMaterial = new THREE.MeshStandardMaterial({
            color: 0x6688aa,        // Steel blue-gray
            side: THREE.DoubleSide, // Render both sides
            roughness: 0.7,
            metalness: 0.3,
            flatShading: false,     // Use smooth shading with vertex normals
            polygonOffset: true,    // Help with z-fighting
            polygonOffsetFactor: 1,
            polygonOffsetUnits: 1
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

        // Fit camera
        const size = box.getSize(new THREE.Vector3()).length();
        this.camera.position.set(size * 1.5, size * 0.75, size * 1.5);
        this.camera.lookAt(0, 0, 0);

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

window.MAGNETSceneManager = MAGNETSceneManager;
