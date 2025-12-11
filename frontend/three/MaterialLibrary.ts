/**
 * MaterialLibrary.ts - PBR material management v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Manages Three.js materials from MaterialDef schema.
 */

import * as THREE from 'three';
import type { MaterialDef, MaterialSide } from '../types/schema';

// =============================================================================
// MATERIAL LIBRARY
// =============================================================================

export class MaterialLibrary {
  private materials: Map<string, THREE.Material> = new Map();
  private definitions: MaterialDef[];

  constructor(definitions: MaterialDef[] = []) {
    this.definitions = definitions;
    this.initializeMaterials();
  }

  private initializeMaterials(): void {
    for (const def of this.definitions) {
      const material = this.createMaterial(def);
      this.materials.set(def.name, material);
    }
  }

  /**
   * Create Three.js material from MaterialDef.
   */
  private createMaterial(def: MaterialDef): THREE.Material {
    const side = this.getSide(def.side);

    if (def.type === 'MeshBasicMaterial') {
      return new THREE.MeshBasicMaterial({
        color: def.color,
        opacity: def.opacity,
        transparent: def.transparent,
        side,
      });
    }

    // Default to MeshStandardMaterial (PBR)
    return new THREE.MeshStandardMaterial({
      color: def.color,
      metalness: def.metalness,
      roughness: def.roughness,
      opacity: def.opacity,
      transparent: def.transparent,
      side,
      emissive: def.emissive,
      emissiveIntensity: def.emissiveIntensity,
    });
  }

  private getSide(side: MaterialSide): THREE.Side {
    switch (side) {
      case 'back':
        return THREE.BackSide;
      case 'double':
        return THREE.DoubleSide;
      default:
        return THREE.FrontSide;
    }
  }

  /**
   * Get material by name.
   */
  get(name: string): THREE.Material | undefined {
    return this.materials.get(name);
  }

  /**
   * Get or create material.
   */
  getOrCreate(name: string, def: MaterialDef): THREE.Material {
    let material = this.materials.get(name);
    if (!material) {
      material = this.createMaterial(def);
      this.materials.set(name, material);
    }
    return material;
  }

  /**
   * Get default hull material.
   */
  getDefaultHullMaterial(): THREE.MeshStandardMaterial {
    const existing = this.materials.get('__default_hull__');
    if (existing) return existing as THREE.MeshStandardMaterial;

    const material = new THREE.MeshStandardMaterial({
      color: 0xb8b8b8,
      metalness: 0.9,
      roughness: 0.4,
      side: THREE.FrontSide,
    });

    this.materials.set('__default_hull__', material);
    return material;
  }

  /**
   * Get default deck material.
   */
  getDefaultDeckMaterial(): THREE.MeshStandardMaterial {
    const existing = this.materials.get('__default_deck__');
    if (existing) return existing as THREE.MeshStandardMaterial;

    const material = new THREE.MeshStandardMaterial({
      color: 0x8b7355, // Wood-like color
      metalness: 0.1,
      roughness: 0.8,
      side: THREE.FrontSide,
    });

    this.materials.set('__default_deck__', material);
    return material;
  }

  /**
   * Get default structure material.
   */
  getDefaultStructureMaterial(): THREE.MeshStandardMaterial {
    const existing = this.materials.get('__default_structure__');
    if (existing) return existing as THREE.MeshStandardMaterial;

    const material = new THREE.MeshStandardMaterial({
      color: 0x666666,
      metalness: 0.8,
      roughness: 0.5,
      side: THREE.DoubleSide,
    });

    this.materials.set('__default_structure__', material);
    return material;
  }

  /**
   * Get wireframe material.
   */
  getWireframeMaterial(color: number = 0x00ff00): THREE.LineBasicMaterial {
    const key = `__wireframe_${color.toString(16)}__`;
    const existing = this.materials.get(key);
    if (existing) return existing as THREE.LineBasicMaterial;

    const material = new THREE.LineBasicMaterial({
      color,
      linewidth: 1,
    });

    this.materials.set(key, material);
    return material;
  }

  /**
   * Get highlight material for selection.
   */
  getHighlightMaterial(): THREE.MeshStandardMaterial {
    const existing = this.materials.get('__highlight__');
    if (existing) return existing as THREE.MeshStandardMaterial;

    const material = new THREE.MeshStandardMaterial({
      color: 0x00aaff,
      metalness: 0.5,
      roughness: 0.5,
      emissive: 0x0044ff,
      emissiveIntensity: 0.3,
    });

    this.materials.set('__highlight__', material);
    return material;
  }

  /**
   * Get annotation marker material.
   */
  getAnnotationMaterial(color: string = '#ffffff'): THREE.MeshBasicMaterial {
    const key = `__annotation_${color}__`;
    const existing = this.materials.get(key);
    if (existing) return existing as THREE.MeshBasicMaterial;

    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color),
    });

    this.materials.set(key, material);
    return material;
  }

  /**
   * Dispose all materials.
   */
  dispose(): void {
    for (const material of this.materials.values()) {
      material.dispose();
    }
    this.materials.clear();
  }
}

// =============================================================================
// PRESET MATERIALS
// =============================================================================

/**
 * Create steel material preset.
 */
export function createSteelMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: 0xa0a0a0,
    metalness: 0.95,
    roughness: 0.3,
  });
}

/**
 * Create aluminum material preset.
 */
export function createAluminumMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: 0xd0d0d0,
    metalness: 0.9,
    roughness: 0.35,
  });
}

/**
 * Create painted hull material.
 */
export function createPaintedMaterial(color: number = 0x1a237e): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0.1,
    roughness: 0.6,
  });
}

/**
 * Create anti-fouling paint material.
 */
export function createAntifoulingMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: 0x8b0000, // Dark red
    metalness: 0.05,
    roughness: 0.7,
  });
}

/**
 * Create glass/window material.
 */
export function createGlassMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: 0x88ccff,
    metalness: 0.1,
    roughness: 0.1,
    transparent: true,
    opacity: 0.3,
  });
}

export default MaterialLibrary;
