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
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.loader = new THREE.GLTFLoader();
        this.hull = null;

        this._init();
    }

    _init() {
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setClearColor(0x0a0a0a, 1);
        this.container.appendChild(this.renderer.domElement);

        // Lights
        this.scene.add(new THREE.AmbientLight(0x404040, 0.5));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 10, 7);
        this.scene.add(dirLight);

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
        const gltf = await this.loader.loadAsync(url);

        if (this.hull) this.scene.remove(this.hull);
        this.hull = gltf.scene;
        this.scene.add(this.hull);

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
