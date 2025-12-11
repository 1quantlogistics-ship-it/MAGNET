/**
 * SceneManager.ts - Three.js scene management v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Manages Three.js scene, camera, lights, and rendering.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

// =============================================================================
// TYPES
// =============================================================================

export interface SceneManagerOptions {
  backgroundColor?: number;
  antialias?: boolean;
  shadowsEnabled?: boolean;
  ambientLightIntensity?: number;
  directionalLightIntensity?: number;
}

const DEFAULT_OPTIONS: SceneManagerOptions = {
  backgroundColor: 0x1a1a2e,
  antialias: true,
  shadowsEnabled: true,
  ambientLightIntensity: 0.4,
  directionalLightIntensity: 0.8,
};

// =============================================================================
// SCENE MANAGER
// =============================================================================

export class SceneManager {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private container: HTMLElement;
  private options: SceneManagerOptions;

  // Lights
  private ambientLight: THREE.AmbientLight;
  private directionalLight: THREE.DirectionalLight;
  private fillLight: THREE.DirectionalLight;

  // State
  private disposed: boolean = false;
  private clippingPlanes: THREE.Plane[] = [];

  constructor(container: HTMLElement, options: SceneManagerOptions = {}) {
    this.container = container;
    this.options = { ...DEFAULT_OPTIONS, ...options };

    // Initialize scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(this.options.backgroundColor);

    // Initialize camera
    const aspect = container.clientWidth / container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
    this.camera.position.set(30, 15, 20);

    // Initialize renderer
    this.renderer = new THREE.WebGLRenderer({
      antialias: this.options.antialias,
      preserveDrawingBuffer: true, // For screenshots
    });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = this.options.shadowsEnabled ?? false;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.localClippingEnabled = true;
    container.appendChild(this.renderer.domElement);

    // Initialize controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.target.set(12, 0, 0);

    // Initialize lights
    this.ambientLight = new THREE.AmbientLight(0xffffff, this.options.ambientLightIntensity);
    this.scene.add(this.ambientLight);

    this.directionalLight = new THREE.DirectionalLight(0xffffff, this.options.directionalLightIntensity);
    this.directionalLight.position.set(50, 50, 50);
    if (this.options.shadowsEnabled) {
      this.directionalLight.castShadow = true;
      this.directionalLight.shadow.mapSize.width = 2048;
      this.directionalLight.shadow.mapSize.height = 2048;
      this.directionalLight.shadow.camera.near = 0.5;
      this.directionalLight.shadow.camera.far = 500;
    }
    this.scene.add(this.directionalLight);

    this.fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    this.fillLight.position.set(-30, -20, -30);
    this.scene.add(this.fillLight);

    // Add grid helper for reference
    const gridHelper = new THREE.GridHelper(50, 50, 0x444444, 0x333333);
    gridHelper.position.y = -5;
    this.scene.add(gridHelper);

    // Handle resize
    this.handleResize = this.handleResize.bind(this);
    window.addEventListener('resize', this.handleResize);

    // Initial resize
    this.handleResize();
  }

  // ===========================================================================
  // PUBLIC METHODS
  // ===========================================================================

  /**
   * Add object to scene.
   */
  add(object: THREE.Object3D): void {
    this.scene.add(object);
  }

  /**
   * Remove object from scene.
   */
  remove(object: THREE.Object3D): void {
    this.scene.remove(object);
  }

  /**
   * Update controls (call in animation loop).
   */
  update(): void {
    if (this.disposed) return;
    this.controls.update();
  }

  /**
   * Render scene (call in animation loop).
   */
  render(): void {
    if (this.disposed) return;
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Set camera position and target.
   */
  setCamera(
    position: [number, number, number] | readonly [number, number, number],
    target: [number, number, number] | readonly [number, number, number],
  ): void {
    this.camera.position.set(position[0], position[1], position[2]);
    this.controls.target.set(target[0], target[1], target[2]);
    this.controls.update();
  }

  /**
   * Set camera target (look-at point).
   */
  setTarget(target: [number, number, number]): void {
    this.controls.target.set(target[0], target[1], target[2]);
    this.controls.update();
  }

  /**
   * Get camera position.
   */
  getCameraPosition(): [number, number, number] {
    return [
      this.camera.position.x,
      this.camera.position.y,
      this.camera.position.z,
    ];
  }

  /**
   * Get camera target.
   */
  getCameraTarget(): [number, number, number] {
    return [
      this.controls.target.x,
      this.controls.target.y,
      this.controls.target.z,
    ];
  }

  /**
   * Set clipping plane for section cuts.
   */
  setClippingPlane(plane: THREE.Plane): void {
    this.clippingPlanes = [plane];
    this.renderer.clippingPlanes = this.clippingPlanes;
  }

  /**
   * Clear all clipping planes.
   */
  clearClippingPlanes(): void {
    this.clippingPlanes = [];
    this.renderer.clippingPlanes = [];
  }

  /**
   * Get renderer for screenshot.
   */
  toDataURL(type: string = 'image/png'): string {
    this.render();
    return this.renderer.domElement.toDataURL(type);
  }

  /**
   * Get canvas element.
   */
  getCanvas(): HTMLCanvasElement {
    return this.renderer.domElement;
  }

  /**
   * Get scene for direct access.
   */
  getScene(): THREE.Scene {
    return this.scene;
  }

  /**
   * Get camera for direct access.
   */
  getCamera(): THREE.PerspectiveCamera {
    return this.camera;
  }

  /**
   * Get renderer for direct access.
   */
  getRenderer(): THREE.WebGLRenderer {
    return this.renderer;
  }

  /**
   * Raycast from mouse position.
   */
  raycast(
    mouseX: number,
    mouseY: number,
    objects: THREE.Object3D[],
  ): THREE.Intersection[] {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    // Convert to normalized device coordinates
    const rect = this.container.getBoundingClientRect();
    mouse.x = ((mouseX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((mouseY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, this.camera);
    return raycaster.intersectObjects(objects, true);
  }

  /**
   * Project 3D point to screen coordinates.
   */
  project(point: [number, number, number]): { x: number; y: number } {
    const vector = new THREE.Vector3(point[0], point[1], point[2]);
    vector.project(this.camera);

    const rect = this.container.getBoundingClientRect();
    return {
      x: ((vector.x + 1) / 2) * rect.width,
      y: ((-vector.y + 1) / 2) * rect.height,
    };
  }

  /**
   * Unproject screen coordinates to 3D ray.
   */
  unproject(x: number, y: number): THREE.Ray {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const rect = this.container.getBoundingClientRect();
    mouse.x = ((x - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((y - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, this.camera);
    return raycaster.ray;
  }

  /**
   * Fit camera to bounding box.
   */
  fitToBounds(bounds: {
    min: [number, number, number];
    max: [number, number, number];
  }): void {
    const center = new THREE.Vector3(
      (bounds.min[0] + bounds.max[0]) / 2,
      (bounds.min[1] + bounds.max[1]) / 2,
      (bounds.min[2] + bounds.max[2]) / 2,
    );

    const size = new THREE.Vector3(
      bounds.max[0] - bounds.min[0],
      bounds.max[1] - bounds.min[1],
      bounds.max[2] - bounds.min[2],
    );

    const maxDim = Math.max(size.x, size.y, size.z);
    const distance = maxDim * 1.5;

    this.camera.position.set(
      center.x + distance,
      center.y + distance * 0.5,
      center.z + distance * 0.7,
    );
    this.controls.target.copy(center);
    this.controls.update();
  }

  /**
   * Set background color.
   */
  setBackgroundColor(color: number): void {
    (this.scene.background as THREE.Color).setHex(color);
  }

  /**
   * Enable/disable shadows.
   */
  setShadowsEnabled(enabled: boolean): void {
    this.renderer.shadowMap.enabled = enabled;
    this.directionalLight.castShadow = enabled;
  }

  /**
   * Dispose and cleanup.
   */
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    window.removeEventListener('resize', this.handleResize);

    this.controls.dispose();

    // Dispose all objects in scene
    this.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.geometry?.dispose();
        if (object.material instanceof THREE.Material) {
          object.material.dispose();
        } else if (Array.isArray(object.material)) {
          object.material.forEach((m) => m.dispose());
        }
      }
    });

    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  // ===========================================================================
  // PRIVATE METHODS
  // ===========================================================================

  private handleResize(): void {
    if (this.disposed) return;

    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }
}

export default SceneManager;
