/**
 * MAGNET UI Scene Lighting
 *
 * Three.js lighting component for the 3D viewport.
 * Tied to ViewportStore for dynamic light positioning.
 */

import React, { useRef, useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { viewportStore } from '../../stores/geometry/viewportStore';

/**
 * Light configuration
 */
export interface LightConfig {
  /** Light type */
  type: 'ambient' | 'directional' | 'point' | 'spot' | 'hemisphere';
  /** Light color */
  color?: string | number;
  /** Secondary color (for hemisphere) */
  groundColor?: string | number;
  /** Light intensity */
  intensity?: number;
  /** Position (for directional, point, spot) */
  position?: [number, number, number];
  /** Target position (for directional, spot) */
  target?: [number, number, number];
  /** Cast shadows */
  castShadow?: boolean;
  /** Shadow map size */
  shadowMapSize?: number;
  /** Distance (for point, spot) */
  distance?: number;
  /** Angle (for spot) */
  angle?: number;
  /** Penumbra (for spot) */
  penumbra?: number;
  /** Decay (for point, spot) */
  decay?: number;
}

/**
 * SceneLighting props
 */
export interface SceneLightingProps {
  /** Scene to add lights to */
  scene: THREE.Scene;
  /** Light configurations */
  lights?: LightConfig[];
  /** Enable dynamic lighting based on camera */
  dynamicLighting?: boolean;
  /** Enable shadows */
  enableShadows?: boolean;
  /** Shadow quality (affects performance) */
  shadowQuality?: 'low' | 'medium' | 'high';
  /** Ambient light intensity multiplier */
  ambientIntensity?: number;
}

/**
 * Default VisionOS-style lighting setup
 */
const DEFAULT_LIGHTS: LightConfig[] = [
  // Soft ambient fill
  {
    type: 'ambient',
    color: 0xffffff,
    intensity: 0.4,
  },
  // Hemisphere for sky/ground gradient
  {
    type: 'hemisphere',
    color: 0xffffff,
    groundColor: 0x444444,
    intensity: 0.6,
  },
  // Main key light (top-front-right)
  {
    type: 'directional',
    color: 0xffffff,
    intensity: 1.0,
    position: [5, 10, 7],
    castShadow: true,
    shadowMapSize: 2048,
  },
  // Fill light (front-left)
  {
    type: 'directional',
    color: 0xaaccff,
    intensity: 0.3,
    position: [-3, 5, 5],
    castShadow: false,
  },
  // Rim light (back)
  {
    type: 'directional',
    color: 0xffffee,
    intensity: 0.2,
    position: [0, 3, -8],
    castShadow: false,
  },
];

/**
 * Shadow quality settings
 */
const SHADOW_QUALITY = {
  low: { mapSize: 512, bias: -0.001 },
  medium: { mapSize: 1024, bias: -0.0005 },
  high: { mapSize: 2048, bias: -0.0002 },
};

/**
 * Create a Three.js light from config
 */
function createLight(config: LightConfig): THREE.Light {
  let light: THREE.Light;

  switch (config.type) {
    case 'ambient':
      light = new THREE.AmbientLight(config.color ?? 0xffffff, config.intensity ?? 1);
      break;

    case 'hemisphere':
      light = new THREE.HemisphereLight(
        config.color ?? 0xffffff,
        config.groundColor ?? 0x444444,
        config.intensity ?? 1
      );
      break;

    case 'directional': {
      const dirLight = new THREE.DirectionalLight(config.color ?? 0xffffff, config.intensity ?? 1);
      if (config.position) {
        dirLight.position.set(...config.position);
      }
      if (config.castShadow) {
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = config.shadowMapSize ?? 1024;
        dirLight.shadow.mapSize.height = config.shadowMapSize ?? 1024;
        dirLight.shadow.camera.near = 0.5;
        dirLight.shadow.camera.far = 50;
        dirLight.shadow.camera.left = -10;
        dirLight.shadow.camera.right = 10;
        dirLight.shadow.camera.top = 10;
        dirLight.shadow.camera.bottom = -10;
      }
      light = dirLight;
      break;
    }

    case 'point': {
      const pointLight = new THREE.PointLight(
        config.color ?? 0xffffff,
        config.intensity ?? 1,
        config.distance ?? 0,
        config.decay ?? 2
      );
      if (config.position) {
        pointLight.position.set(...config.position);
      }
      if (config.castShadow) {
        pointLight.castShadow = true;
        pointLight.shadow.mapSize.width = config.shadowMapSize ?? 512;
        pointLight.shadow.mapSize.height = config.shadowMapSize ?? 512;
      }
      light = pointLight;
      break;
    }

    case 'spot': {
      const spotLight = new THREE.SpotLight(
        config.color ?? 0xffffff,
        config.intensity ?? 1,
        config.distance ?? 0,
        config.angle ?? Math.PI / 3,
        config.penumbra ?? 0,
        config.decay ?? 2
      );
      if (config.position) {
        spotLight.position.set(...config.position);
      }
      if (config.target) {
        spotLight.target.position.set(...config.target);
      }
      if (config.castShadow) {
        spotLight.castShadow = true;
        spotLight.shadow.mapSize.width = config.shadowMapSize ?? 512;
        spotLight.shadow.mapSize.height = config.shadowMapSize ?? 512;
      }
      light = spotLight;
      break;
    }

    default:
      light = new THREE.AmbientLight(0xffffff, 1);
  }

  return light;
}

/**
 * SceneLighting component
 */
export const SceneLighting: React.FC<SceneLightingProps> = ({
  scene,
  lights = DEFAULT_LIGHTS,
  dynamicLighting = false,
  enableShadows = true,
  shadowQuality = 'medium',
  ambientIntensity = 1,
}) => {
  const lightsRef = useRef<THREE.Light[]>([]);
  const keyLightRef = useRef<THREE.DirectionalLight | null>(null);

  // Create and add lights to scene
  useEffect(() => {
    // Remove existing lights
    lightsRef.current.forEach((light) => {
      scene.remove(light);
      light.dispose?.();
    });
    lightsRef.current = [];
    keyLightRef.current = null;

    // Create new lights
    const shadowSettings = SHADOW_QUALITY[shadowQuality];

    lights.forEach((config, index) => {
      const light = createLight(config);

      // Apply ambient intensity multiplier to ambient lights
      if (config.type === 'ambient' || config.type === 'hemisphere') {
        light.intensity = (config.intensity ?? 1) * ambientIntensity;
      }

      // Configure shadows
      if (enableShadows && config.castShadow && 'shadow' in light) {
        const shadowLight = light as THREE.DirectionalLight | THREE.SpotLight | THREE.PointLight;
        shadowLight.shadow.mapSize.width = shadowSettings.mapSize;
        shadowLight.shadow.mapSize.height = shadowSettings.mapSize;
        shadowLight.shadow.bias = shadowSettings.bias;
      }

      // Track key light for dynamic positioning
      if (config.type === 'directional' && index === 2) {
        keyLightRef.current = light as THREE.DirectionalLight;
      }

      scene.add(light);
      lightsRef.current.push(light);
    });

    // Cleanup
    return () => {
      lightsRef.current.forEach((light) => {
        scene.remove(light);
        light.dispose?.();
      });
      lightsRef.current = [];
    };
  }, [scene, lights, enableShadows, shadowQuality, ambientIntensity]);

  // Dynamic lighting based on camera position
  useEffect(() => {
    if (!dynamicLighting || !keyLightRef.current) return;

    const unsubscribe = viewportStore.subscribe((state) => {
      if (!keyLightRef.current) return;

      // Offset key light position based on camera
      const camera = state.camera;
      const lightOffset = new THREE.Vector3(5, 10, 7);

      // Rotate light offset based on camera position
      const cameraPos = new THREE.Vector3(camera.position.x, camera.position.y, camera.position.z);
      const targetPos = new THREE.Vector3(camera.target.x, camera.target.y, camera.target.z);
      const cameraDir = cameraPos.clone().sub(targetPos).normalize();

      // Calculate perpendicular offset
      const right = new THREE.Vector3(0, 1, 0).cross(cameraDir).normalize();
      const adjustedOffset = lightOffset.clone()
        .add(right.multiplyScalar(cameraPos.x * 0.2))
        .add(new THREE.Vector3(0, cameraPos.y * 0.1, 0));

      keyLightRef.current.position.copy(adjustedOffset);
      keyLightRef.current.target.position.copy(targetPos);
    });

    return unsubscribe;
  }, [dynamicLighting]);

  // This component doesn't render anything visible
  // It only manages Three.js lights in the scene
  return null;
};

/**
 * Hook for accessing scene lighting controls
 */
export function useSceneLighting(): {
  setAmbientIntensity: (intensity: number) => void;
  setKeyLightPosition: (position: [number, number, number]) => void;
  setShadowsEnabled: (enabled: boolean) => void;
} {
  // These would typically update a lighting store
  // For now, they're placeholders for the component interface
  return {
    setAmbientIntensity: (intensity: number) => {
      console.log('[SceneLighting] setAmbientIntensity:', intensity);
    },
    setKeyLightPosition: (position: [number, number, number]) => {
      console.log('[SceneLighting] setKeyLightPosition:', position);
    },
    setShadowsEnabled: (enabled: boolean) => {
      console.log('[SceneLighting] setShadowsEnabled:', enabled);
    },
  };
}

export default SceneLighting;
