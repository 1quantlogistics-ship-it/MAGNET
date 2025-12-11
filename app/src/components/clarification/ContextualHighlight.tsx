/**
 * MAGNET UI Contextual Highlight
 *
 * 3D component highlight effect for contextual selection in Three.js workspace.
 * Displays pulse animation around target component and handles selection.
 */

import React, { useRef, useCallback, useEffect, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import {
  getActiveContextualRequest,
  respondToClarification,
  subscribeToClarification,
} from '../../stores/domain/clarificationStore';
import { VISIONOS_TIMING } from '../../types/common';

/**
 * Contextual highlight props
 */
export interface ContextualHighlightProps {
  /** Function to resolve component ID from intersection */
  resolveComponentId?: (intersection: THREE.Intersection) => string | null;
  /** Custom highlight color */
  highlightColor?: THREE.Color;
}

/**
 * ContextualHighlight component
 *
 * Renders in Three.js scene to:
 * 1. Display selection-ready state (cursor change, hover highlighting)
 * 2. Handle click events on 3D components
 * 3. Return selected component ID to the clarification system
 *
 * @example
 * ```tsx
 * // Inside Canvas
 * <ContextualHighlight
 *   resolveComponentId={(intersection) => intersection.object.userData.componentId}
 * />
 * ```
 */
export const ContextualHighlight: React.FC<ContextualHighlightProps> = ({
  resolveComponentId = defaultResolver,
  highlightColor = new THREE.Color(0x7eb8e7),
}) => {
  const { gl, scene, camera, raycaster, pointer } = useThree();
  const [isActive, setIsActive] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const requestIdRef = useRef<string | null>(null);

  // Track active contextual request
  useEffect(() => {
    const unsubscribe = subscribeToClarification((state) => {
      const contextualRequest = state.activeContextualRequest;
      if (contextualRequest) {
        setIsActive(true);
        requestIdRef.current = contextualRequest.id;
      } else {
        setIsActive(false);
        requestIdRef.current = null;
        setHoveredId(null);
      }
    });

    // Check initial state
    const contextualRequest = getActiveContextualRequest();
    if (contextualRequest) {
      setIsActive(true);
      requestIdRef.current = contextualRequest.id;
    }

    return unsubscribe;
  }, []);

  // Handle click
  const handleClick = useCallback(
    (event: MouseEvent) => {
      if (!isActive || !requestIdRef.current) return;

      // Prevent default and stop propagation
      event.preventDefault();
      event.stopPropagation();

      // Update raycaster
      raycaster.setFromCamera(pointer, camera);

      // Find intersections
      const intersects = raycaster.intersectObjects(scene.children, true);

      if (intersects.length > 0) {
        // Find first component with ID
        for (const intersection of intersects) {
          const componentId = resolveComponentId(intersection);
          if (componentId) {
            // Respond with component ID
            respondToClarification(requestIdRef.current, componentId);
            return;
          }
        }
      }

      // No valid component found - could show feedback
    },
    [isActive, raycaster, pointer, camera, scene, resolveComponentId]
  );

  // Attach click handler
  useEffect(() => {
    if (!isActive) return;

    const domElement = gl.domElement;
    domElement.addEventListener('click', handleClick, true);
    domElement.style.cursor = 'crosshair';

    return () => {
      domElement.removeEventListener('click', handleClick, true);
      domElement.style.cursor = '';
    };
  }, [isActive, gl, handleClick]);

  // Update hover state
  useFrame(() => {
    if (!isActive) return;

    // Update raycaster
    raycaster.setFromCamera(pointer, camera);

    // Find intersections
    const intersects = raycaster.intersectObjects(scene.children, true);

    let newHoveredId: string | null = null;

    for (const intersection of intersects) {
      const componentId = resolveComponentId(intersection);
      if (componentId) {
        newHoveredId = componentId;
        break;
      }
    }

    if (newHoveredId !== hoveredId) {
      setHoveredId(newHoveredId);
    }
  });

  // Don't render anything if not active
  if (!isActive) return null;

  // Render highlight effect if hovering
  return hoveredId ? <HighlightPulse color={highlightColor} /> : null;
};

/**
 * Highlight pulse effect mesh
 */
const HighlightPulse: React.FC<{ color: THREE.Color }> = ({ color }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);

  // Pulse animation
  useFrame(({ clock }) => {
    if (!meshRef.current || !materialRef.current) return;

    const time = clock.getElapsedTime();
    const pulse = Math.sin(time * VISIONOS_TIMING.markerPulse * Math.PI * 2) * 0.5 + 0.5;

    // Scale and opacity pulse
    const scale = 1 + pulse * 0.1;
    meshRef.current.scale.setScalar(scale);
    materialRef.current.opacity = 0.15 + pulse * 0.1;
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[2, 16, 16]} />
      <meshBasicMaterial
        ref={materialRef}
        color={color}
        transparent
        opacity={0.2}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
};

/**
 * Default component ID resolver
 * Looks for componentId in userData
 */
function defaultResolver(intersection: THREE.Intersection): string | null {
  // Check intersection object
  if (intersection.object.userData?.componentId) {
    return intersection.object.userData.componentId;
  }

  // Check parent objects
  let parent = intersection.object.parent;
  while (parent) {
    if (parent.userData?.componentId) {
      return parent.userData.componentId;
    }
    parent = parent.parent;
  }

  return null;
}

export default ContextualHighlight;
