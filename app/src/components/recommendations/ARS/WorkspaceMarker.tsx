/**
 * MAGNET UI Workspace Marker
 *
 * VisionOS-style 3D marker component for Three.js workspace.
 * Displays recommendation markers with soft glow effects and pulse animations.
 */

import React, { memo, useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type { ARSPriority, ARSMarker } from '../../../types/ars';
import { VISIONOS_TIMING } from '../../../types/common';

/**
 * Workspace marker props
 */
export interface WorkspaceMarkerProps {
  /** Marker configuration */
  marker: ARSMarker;
  /** Priority level (affects color) */
  priority: ARSPriority;
  /** Whether marker is selected */
  isSelected?: boolean;
  /** Whether marker is hovered */
  isHovered?: boolean;
  /** Label text */
  label?: string;
  /** Click handler */
  onClick?: () => void;
  /** Hover handlers */
  onPointerEnter?: () => void;
  onPointerLeave?: () => void;
}

/**
 * Get color for priority level
 */
function getPriorityColor(priority: ARSPriority): THREE.Color {
  switch (priority) {
    case 1:
      return new THREE.Color(0xff453a); // Critical - soft red
    case 2:
      return new THREE.Color(0x2997ff); // High - emphasis blue
    case 3:
      return new THREE.Color(0x7eb8e7); // Medium - accent blue
    case 4:
    case 5:
    default:
      return new THREE.Color(0xa7b4c7); // Low/Info - neutral
  }
}

/**
 * Get glow intensity for priority
 */
function getPriorityIntensity(priority: ARSPriority): number {
  switch (priority) {
    case 1:
      return 0.35;
    case 2:
      return 0.25;
    case 3:
      return 0.20;
    case 4:
    case 5:
    default:
      return 0.15;
  }
}

/**
 * Workspace marker 3D component
 *
 * @example
 * ```tsx
 * <WorkspaceMarker
 *   marker={{ position: { x: 5, y: 1, z: 0 } }}
 *   priority={2}
 *   isSelected={selectedId === rec.id}
 *   label="Adjust Fuel Tank"
 *   onClick={() => selectRecommendation(rec.id)}
 * />
 * ```
 */
export const WorkspaceMarker = memo<WorkspaceMarkerProps>(
  ({
    marker,
    priority,
    isSelected = false,
    isHovered = false,
    label,
    onClick,
    onPointerEnter,
    onPointerLeave,
  }) => {
    const groupRef = useRef<THREE.Group>(null);
    const innerRef = useRef<THREE.Mesh>(null);
    const outerRef = useRef<THREE.Mesh>(null);
    const glowRef = useRef<THREE.Mesh>(null);

    // Position from marker
    const position = useMemo(
      () =>
        new THREE.Vector3(
          marker.position.x,
          marker.position.y,
          marker.position.z
        ),
      [marker.position]
    );

    // Color based on priority
    const color = useMemo(() => getPriorityColor(priority), [priority]);
    const glowIntensity = useMemo(() => getPriorityIntensity(priority), [priority]);

    // Scale based on marker config and selection state
    const baseScale = marker.scale ?? 1;
    const scale = isSelected ? baseScale * 1.3 : isHovered ? baseScale * 1.15 : baseScale;

    // Animation - breathing pulse
    useFrame(({ clock }) => {
      if (!innerRef.current || !outerRef.current || !glowRef.current) return;

      const time = clock.getElapsedTime();
      const pulseRate = VISIONOS_TIMING.markerPulse;

      // Inner core - faster, smaller pulse
      const innerPulse = 1 + Math.sin(time * pulseRate * Math.PI * 2) * 0.08;
      innerRef.current.scale.setScalar(innerPulse);

      // Outer ring - slower, larger pulse (phase shifted)
      const outerPulse = 1 + Math.sin(time * pulseRate * Math.PI * 2 - 0.5) * 0.12;
      outerRef.current.scale.setScalar(outerPulse);

      // Glow - very slow breathing
      const glowPulse = glowIntensity + Math.sin(time * pulseRate * Math.PI * 0.5) * 0.05;
      const glowMaterial = glowRef.current.material as THREE.MeshBasicMaterial;
      glowMaterial.opacity = glowPulse * (isSelected ? 1.5 : 1);
    });

    // Materials
    const innerMaterial = useMemo(
      () =>
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.9,
        }),
      [color]
    );

    const outerMaterial = useMemo(
      () =>
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.4,
          wireframe: true,
        }),
      [color]
    );

    const glowMaterial = useMemo(
      () =>
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: glowIntensity,
          side: THREE.DoubleSide,
        }),
      [color, glowIntensity]
    );

    return (
      <group
        ref={groupRef}
        position={position}
        scale={scale}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
        onPointerEnter={(e) => {
          e.stopPropagation();
          onPointerEnter?.();
        }}
        onPointerLeave={(e) => {
          e.stopPropagation();
          onPointerLeave?.();
        }}
      >
        {/* Inner core sphere */}
        <mesh ref={innerRef} material={innerMaterial}>
          <sphereGeometry args={[0.15, 16, 16]} />
        </mesh>

        {/* Outer ring */}
        <mesh ref={outerRef} rotation={[Math.PI / 2, 0, 0]} material={outerMaterial}>
          <torusGeometry args={[0.35, 0.02, 8, 32]} />
        </mesh>

        {/* Glow halo */}
        <mesh ref={glowRef} material={glowMaterial}>
          <sphereGeometry args={[0.5, 16, 16]} />
        </mesh>

        {/* Label (HTML overlay) */}
        {(isSelected || isHovered) && label && (
          <Html
            position={[0, 0.8, 0]}
            center
            style={{
              pointerEvents: 'none',
            }}
          >
            <div
              style={{
                padding: '6px 12px',
                background: 'rgba(30, 30, 35, 0.9)',
                backdropFilter: 'blur(12px)',
                borderRadius: '8px',
                boxShadow: `
                  0 4px 12px rgba(0, 0, 0, 0.3),
                  inset 0 0 0 1px rgba(255, 255, 255, 0.08)
                `,
                whiteSpace: 'nowrap',
              }}
            >
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 500,
                  color: 'rgba(255, 255, 255, 0.95)',
                  fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
                }}
              >
                {label}
              </span>
            </div>
          </Html>
        )}
      </group>
    );
  }
);

WorkspaceMarker.displayName = 'WorkspaceMarker';

/**
 * Workspace markers container
 * Renders all ARS markers in the 3D scene
 */
export interface WorkspaceMarkersProps {
  /** Markers data from recommendations */
  markers: Array<{
    id: string;
    marker: ARSMarker;
    priority: ARSPriority;
    label?: string;
  }>;
  /** Currently selected marker ID */
  selectedId?: string | null;
  /** Select handler */
  onSelect?: (id: string) => void;
}

export const WorkspaceMarkers = memo<WorkspaceMarkersProps>(
  ({ markers, selectedId, onSelect }) => {
    const [hoveredId, setHoveredId] = React.useState<string | null>(null);

    return (
      <group name="ars-markers">
        {markers.map(({ id, marker, priority, label }) => (
          <WorkspaceMarker
            key={id}
            marker={marker}
            priority={priority}
            isSelected={selectedId === id}
            isHovered={hoveredId === id}
            label={label}
            onClick={() => onSelect?.(id)}
            onPointerEnter={() => setHoveredId(id)}
            onPointerLeave={() => setHoveredId(null)}
          />
        ))}
      </group>
    );
  }
);

WorkspaceMarkers.displayName = 'WorkspaceMarkers';

export default WorkspaceMarker;
