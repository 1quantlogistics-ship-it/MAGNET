/**
 * MAGNET UI Module 02: VisionSurface
 *
 * Unified glass material component for ALL PRS surfaces.
 * Single base for context menus, phase panels, toasts, etc.
 */

import React, { forwardRef, useMemo } from 'react';
import type { VisionSurfaceProps, PRSSurfaceDepth, PRSSurfaceVariant } from '../../../types/prs';
import { usePresenceAnimation, EASING } from '../../../hooks/useAnimationScheduler';
import styles from './VisionSurface.module.css';

/**
 * Spring transition config for VisionOS motion
 */
const SPRING_CONFIG = {
  stiffness: 160,
  damping: 26,
};

/**
 * VisionSurface - Unified glass material component
 */
export const VisionSurface = forwardRef<HTMLDivElement, VisionSurfaceProps & {
  /** Enable entrance animation */
  animate?: boolean;
  /** Custom transform */
  transform?: string;
  /** Render as different element */
  as?: 'div' | 'section' | 'article' | 'aside' | 'nav';
}>(
  (
    {
      variant = 'default',
      depth = 'mid',
      children,
      className = '',
      style,
      onClick,
      isFocused = false,
      animate = true,
      transform,
      as: Component = 'div',
    },
    ref
  ) => {
    // Presence animation
    const presence = usePresenceAnimation(true, {
      enterDuration: 350,
      exitDuration: 250,
      enterEasing: EASING.spring,
      exitEasing: EASING.easeOut,
    });

    // Variant class
    const variantClass = useMemo(() => {
      switch (variant) {
        case 'active':
          return styles.variantActive;
        case 'success':
          return styles.variantSuccess;
        default:
          return styles.variantDefault;
      }
    }, [variant]);

    // Depth class
    const depthClass = useMemo(() => {
      switch (depth) {
        case 'near':
          return styles.depthNear;
        case 'far':
          return styles.depthFar;
        default:
          return styles.depthMid;
      }
    }, [depth]);

    // Combined styles with animation
    const combinedStyles = useMemo((): React.CSSProperties => {
      const baseStyles: React.CSSProperties = {
        ...style,
      };

      if (animate) {
        baseStyles.opacity = presence.progress;
        baseStyles.transform = transform || `
          translateY(${(1 - presence.progress) * 12}px)
          scale(${0.98 + presence.progress * 0.02})
        `.trim();
      }

      if (transform && !animate) {
        baseStyles.transform = transform;
      }

      return baseStyles;
    }, [style, animate, presence.progress, transform]);

    return (
      <Component
        ref={ref}
        className={`
          ${styles.surface}
          ${variantClass}
          ${depthClass}
          ${isFocused ? styles.focused : ''}
          ${onClick ? styles.clickable : ''}
          ${className}
        `}
        style={combinedStyles}
        onClick={onClick}
        data-variant={variant}
        data-depth={depth}
        data-focused={isFocused}
      >
        {/* Top edge highlight - simulates light source */}
        <div className={styles.edgeHighlight} aria-hidden="true" />

        {/* Glass backdrop */}
        <div className={styles.glassBackdrop} aria-hidden="true" />

        {/* Content */}
        <div className={styles.content}>{children}</div>

        {/* Border */}
        <div className={styles.border} aria-hidden="true" />
      </Component>
    );
  }
);

VisionSurface.displayName = 'VisionSurface';

/**
 * VisionSurface with blur effect for unfocused state
 */
export const BlurredVisionSurface = forwardRef<
  HTMLDivElement,
  VisionSurfaceProps & {
    isBlurred?: boolean;
  }
>(({ isBlurred = false, className = '', style, ...props }, ref) => {
  const blurredStyle = useMemo((): React.CSSProperties => {
    return {
      ...style,
      filter: isBlurred ? 'blur(3px)' : 'none',
      opacity: isBlurred ? 0.6 : 1,
      transform: isBlurred ? 'scale(0.98)' : 'scale(1)',
      transition: 'filter 400ms ease, opacity 400ms ease, transform 400ms ease',
    };
  }, [style, isBlurred]);

  return (
    <VisionSurface
      ref={ref}
      className={`${className} ${isBlurred ? styles.blurred : ''}`}
      style={blurredStyle}
      {...props}
    />
  );
});

BlurredVisionSurface.displayName = 'BlurredVisionSurface';

export default VisionSurface;
