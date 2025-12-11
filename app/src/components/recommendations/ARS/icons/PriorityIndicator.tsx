/**
 * MAGNET UI Priority Indicator Icons
 *
 * VisionOS-style priority indicator SVG icons for ARS recommendations.
 * Uses monochrome styling with subtle glow effects.
 */

import React, { memo } from 'react';
import type { ARSPriority } from '../../../../types/ars';

/**
 * Priority indicator props
 */
interface PriorityIndicatorProps {
  /** Priority level (1-5) */
  priority: ARSPriority;
  /** Size in pixels */
  size?: number;
  /** Optional className */
  className?: string;
  /** Whether to animate */
  animated?: boolean;
}

/**
 * SVG icon for priority 1 (Critical)
 * Triangle with exclamation mark
 */
const CriticalIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 3L2 21H22L12 3Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
    <path
      d="M12 10V14"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <circle cx="12" cy="17" r="1" fill="currentColor" />
  </svg>
);

/**
 * SVG icon for priority 2 (High)
 * Shield with checkmark
 */
const HighIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 2L4 5V11.09C4 16.14 7.41 20.85 12 22C16.59 20.85 20 16.14 20 11.09V5L12 2Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
    <path
      d="M12 8V12"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <circle cx="12" cy="15" r="1" fill="currentColor" />
  </svg>
);

/**
 * SVG icon for priority 3 (Medium)
 * Gauge/meter icon
 */
const MediumIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="12"
      cy="12"
      r="9"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
    />
    <path
      d="M12 7V12L15 14"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * SVG icon for priority 4 (Low)
 * Arrow up icon (improvement suggestion)
 */
const LowIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 19V5M12 5L6 11M12 5L18 11"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * SVG icon for priority 5 (Info)
 * Info circle icon
 */
const InfoIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="12"
      cy="12"
      r="9"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
    />
    <path
      d="M12 16V12"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <circle cx="12" cy="8" r="1" fill="currentColor" />
  </svg>
);

/**
 * Priority indicator component
 *
 * @example
 * ```tsx
 * <PriorityIndicator priority={1} size={20} animated />
 * ```
 */
export const PriorityIndicator = memo<PriorityIndicatorProps>(
  ({ priority, size = 20, className, animated = false }) => {
    const Icon = getIconForPriority(priority);

    return (
      <span
        className={className}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: getColorForPriority(priority),
          animation: animated && priority <= 2 ? 'pulse 2s infinite' : undefined,
        }}
        aria-label={getPriorityLabel(priority)}
      >
        <Icon size={size} />
      </span>
    );
  }
);

PriorityIndicator.displayName = 'PriorityIndicator';

/**
 * Get the appropriate icon component for a priority level
 */
function getIconForPriority(priority: ARSPriority): React.FC<{ size: number }> {
  switch (priority) {
    case 1:
      return CriticalIcon;
    case 2:
      return HighIcon;
    case 3:
      return MediumIcon;
    case 4:
      return LowIcon;
    case 5:
      return InfoIcon;
    default:
      return InfoIcon;
  }
}

/**
 * Get the color for a priority level
 * Uses VisionOS color palette with restraint
 */
function getColorForPriority(priority: ARSPriority): string {
  switch (priority) {
    case 1:
      return 'rgba(255, 69, 58, 0.9)'; // Critical - soft red
    case 2:
      return 'rgba(41, 151, 255, 0.9)'; // High - emphasis blue
    case 3:
      return 'rgba(126, 184, 231, 0.9)'; // Medium - accent blue
    case 4:
      return 'rgba(167, 180, 199, 0.9)'; // Low - neutral
    case 5:
      return 'rgba(167, 180, 199, 0.7)'; // Info - muted neutral
    default:
      return 'rgba(167, 180, 199, 0.7)';
  }
}

/**
 * Get accessible label for priority
 */
function getPriorityLabel(priority: ARSPriority): string {
  switch (priority) {
    case 1:
      return 'Critical priority';
    case 2:
      return 'High priority';
    case 3:
      return 'Medium priority';
    case 4:
      return 'Low priority';
    case 5:
      return 'Informational';
    default:
      return 'Unknown priority';
  }
}

/**
 * Get priority display name
 */
export function getPriorityName(priority: ARSPriority): string {
  switch (priority) {
    case 1:
      return 'Critical';
    case 2:
      return 'High';
    case 3:
      return 'Medium';
    case 4:
      return 'Low';
    case 5:
      return 'Info';
    default:
      return 'Unknown';
  }
}

export default PriorityIndicator;
