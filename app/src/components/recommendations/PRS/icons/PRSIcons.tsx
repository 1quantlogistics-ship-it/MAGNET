/**
 * MAGNET UI Module 02: PRSIcons
 *
 * SVG icon system for PRS components.
 * Unified size and color API with VisionOS aesthetic.
 */

import React from 'react';
import type { PRSCategory } from '../../../../types/prs';

/**
 * Icon props
 */
export interface PRSIconProps {
  /** Icon name */
  name: PRSIconName;
  /** Icon size in pixels */
  size?: number;
  /** Icon color (CSS color value) */
  color?: string;
  /** Additional class name */
  className?: string;
  /** Accessibility label */
  'aria-label'?: string;
}

/**
 * Available icon names
 */
export type PRSIconName =
  // Category icons
  | 'action'
  | 'clarification'
  | 'navigation'
  | 'enhancement'
  // Status icons
  | 'success'
  | 'error'
  | 'warning'
  | 'info'
  | 'pending'
  // UI icons
  | 'chevron-right'
  | 'chevron-down'
  | 'chevron-up'
  | 'close'
  | 'check'
  | 'plus'
  | 'minus'
  | 'sparkle'
  | 'lightbulb'
  | 'compass'
  | 'wand'
  | 'question'
  | 'arrow-right'
  | 'refresh'
  | 'external-link';

/**
 * Icon path definitions
 * Using 24x24 viewBox for consistency
 */
const ICON_PATHS: Record<PRSIconName, React.ReactNode> = {
  // Category: Action - Lightning bolt
  action: (
    <path
      d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // Category: Clarification - Question mark in circle
  clarification: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path
        d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="17" r="1" fill="currentColor" />
    </>
  ),

  // Category: Navigation - Compass
  navigation: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <polygon
        points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // Category: Enhancement - Sparkles/Wand
  enhancement: (
    <>
      <path
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="2" />
    </>
  ),

  // Status: Success - Checkmark in circle
  success: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path
        d="M9 12l2 2 4-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // Status: Error - X in circle
  error: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path
        d="M15 9l-6 6M9 9l6 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // Status: Warning - Triangle with exclamation
  warning: (
    <>
      <path
        d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="17" r="1" fill="currentColor" />
    </>
  ),

  // Status: Info - i in circle
  info: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="8" r="1" fill="currentColor" />
    </>
  ),

  // Status: Pending - Clock
  pending: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M12 6v6l4 2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),

  // UI: Chevron right
  'chevron-right': (
    <path
      d="M9 18l6-6-6-6"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Chevron down
  'chevron-down': (
    <path
      d="M6 9l6 6 6-6"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Chevron up
  'chevron-up': (
    <path
      d="M18 15l-6-6-6 6"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Close (X)
  close: (
    <path
      d="M18 6L6 18M6 6l12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Checkmark
  check: (
    <path
      d="M20 6L9 17l-5-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Plus
  plus: (
    <path
      d="M12 5v14M5 12h14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Minus
  minus: (
    <path
      d="M5 12h14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Sparkle (AI/Magic indicator)
  sparkle: (
    <>
      <path
        d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // UI: Lightbulb (Ideas/Suggestions)
  lightbulb: (
    <>
      <path
        d="M9 18h6M10 22h4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 2a7 7 0 0 0-4 12.7V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.3A7 7 0 0 0 12 2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // UI: Compass (Navigation/Explore)
  compass: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <polygon
        points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // UI: Wand (Magic/Transform)
  wand: (
    <>
      <path
        d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8l1.4 1.4M17.8 6.2l1.4-1.4M12.2 11.8l-1.4 1.4M12.2 6.2l-1.4-1.4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M4 22l10-10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // UI: Question mark
  question: (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path
        d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="17" r="1" fill="currentColor" />
    </>
  ),

  // UI: Arrow right
  'arrow-right': (
    <path
      d="M5 12h14M12 5l7 7-7 7"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),

  // UI: Refresh
  refresh: (
    <>
      <path
        d="M23 4v6h-6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M1 20v-6h6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  // UI: External link
  'external-link': (
    <>
      <path
        d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M15 3h6v6M10 14L21 3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),
};

/**
 * PRSIcon component
 */
export const PRSIcon: React.FC<PRSIconProps> = ({
  name,
  size = 20,
  color = 'currentColor',
  className,
  'aria-label': ariaLabel,
}) => {
  const iconContent = ICON_PATHS[name];

  if (!iconContent) {
    console.warn(`[PRSIcon] Unknown icon name: ${name}`);
    return null;
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ color }}
      role="img"
      aria-label={ariaLabel || name}
    >
      {iconContent}
    </svg>
  );
};

/**
 * Get icon name for category
 */
export function getCategoryIconName(category: PRSCategory): PRSIconName {
  const categoryIcons: Record<PRSCategory, PRSIconName> = {
    action: 'action',
    clarification: 'clarification',
    navigation: 'navigation',
    enhancement: 'enhancement',
  };
  return categoryIcons[category];
}

/**
 * CategoryIcon component - convenience wrapper
 */
export const CategoryIcon: React.FC<{
  category: PRSCategory;
  size?: number;
  className?: string;
}> = ({ category, size = 16, className }) => {
  return (
    <PRSIcon
      name={getCategoryIconName(category)}
      size={size}
      className={className}
      aria-label={`${category} category`}
    />
  );
};

export default PRSIcon;
