/**
 * MAGNET UI Glass Card
 *
 * VisionOS-style glass morphism card component.
 * Versatile container for content with glass effect.
 */

import React, { forwardRef, useMemo } from 'react';
import type { WindowVariant, Size } from '../../types/common';
import { useHoverGlow } from '../../hooks/useProximityGlow';
import { useHoverTilt } from '../../hooks/useDragTilt';
import { useElevationShadow } from '../../hooks/useDynamicShadow';
import { usePresenceAnimation, EASING } from '../../hooks/useAnimationScheduler';
import { VISIONOS_TIMING } from '../../types/common';
import styles from './GlassCard.module.css';

/**
 * GlassCard props
 */
export interface GlassCardProps {
  /** Card variant */
  variant?: WindowVariant;
  /** Card size (padding) */
  size?: Size;
  /** Enable glass blur effect */
  enableGlass?: boolean;
  /** Enable hover glow */
  enableGlow?: boolean;
  /** Enable hover tilt */
  enableTilt?: boolean;
  /** Elevation level (1-5) */
  elevation?: number;
  /** Whether card is clickable */
  clickable?: boolean;
  /** Whether card is selected */
  isSelected?: boolean;
  /** Whether card is visible (for animation) */
  isVisible?: boolean;
  /** Click handler */
  onClick?: (event: React.MouseEvent<HTMLDivElement>) => void;
  /** Custom className */
  className?: string;
  /** Custom styles */
  style?: React.CSSProperties;
  /** Children content */
  children?: React.ReactNode;
  /** Aria role */
  role?: string;
  /** Tab index */
  tabIndex?: number;
}

/**
 * GlassCard component
 */
export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  (
    {
      variant = 'default',
      size = 'md',
      enableGlass = true,
      enableGlow = true,
      enableTilt = false,
      elevation = 1,
      clickable = false,
      isSelected = false,
      isVisible = true,
      onClick,
      className = '',
      style,
      children,
      role,
      tabIndex,
    },
    ref
  ) => {
    // Presence animation
    const presence = usePresenceAnimation(isVisible, {
      enterDuration: VISIONOS_TIMING.cardExpand,
      exitDuration: VISIONOS_TIMING.tooltipReveal,
      enterEasing: EASING.spring,
      exitEasing: EASING.easeOut,
    });

    // Hover glow effect
    const glow = useHoverGlow({
      enabled: enableGlow && clickable,
      color: 'rgba(255, 255, 255, 0.15)',
      intensity: 0.1,
      radius: 60,
    });

    // Hover tilt effect
    const tilt = useHoverTilt({
      enabled: enableTilt,
      maxRotation: 3,
    });

    // Elevation shadow
    const shadow = useElevationShadow(elevation);

    // Variant class
    const variantClass = useMemo(() => {
      switch (variant) {
        case 'emphasis':
          return styles.variantEmphasis;
        case 'critical':
          return styles.variantCritical;
        default:
          return styles.variantDefault;
      }
    }, [variant]);

    // Size class
    const sizeClass = useMemo(() => {
      switch (size) {
        case 'xs':
          return styles.sizeXs;
        case 'sm':
          return styles.sizeSm;
        case 'md':
          return styles.sizeMd;
        case 'lg':
          return styles.sizeLg;
        case 'xl':
          return styles.sizeXl;
        default:
          return styles.sizeMd;
      }
    }, [size]);

    // Combined styles
    const combinedStyles = useMemo((): React.CSSProperties => {
      return {
        ...style,
        ...shadow.style,
        ...glow.glowStyle,
        ...(enableTilt ? tilt.style : {}),
        opacity: presence.progress,
        transform: `${enableTilt ? tilt.style.transform || '' : ''} scale(${0.95 + presence.progress * 0.05})`.trim(),
      };
    }, [style, shadow.style, glow.glowStyle, enableTilt, tilt.style, presence.progress]);

    // Combined handlers
    const handlers = useMemo(() => {
      const combined: Record<string, React.EventHandler<React.SyntheticEvent>> = {};

      if (enableGlow && clickable) {
        combined.onMouseEnter = glow.handlers.onMouseEnter;
        combined.onMouseLeave = glow.handlers.onMouseLeave;
      }

      if (enableTilt) {
        combined.onMouseMove = tilt.handlers.onMouseMove;
        if (!combined.onMouseLeave) {
          combined.onMouseLeave = tilt.handlers.onMouseLeave;
        } else {
          const originalLeave = combined.onMouseLeave;
          combined.onMouseLeave = (e) => {
            originalLeave(e);
            tilt.handlers.onMouseLeave();
          };
        }
      }

      return combined;
    }, [enableGlow, clickable, glow.handlers, enableTilt, tilt.handlers]);

    if (!presence.isVisible) {
      return null;
    }

    return (
      <div
        ref={(node) => {
          if (typeof ref === 'function') {
            ref(node);
          } else if (ref) {
            ref.current = node;
          }
          if (enableTilt && node) {
            (tilt.ref as React.MutableRefObject<HTMLElement | null>).current = node;
          }
        }}
        className={`${styles.card} ${variantClass} ${sizeClass} ${clickable ? styles.clickable : ''} ${isSelected ? styles.selected : ''} ${className}`}
        style={combinedStyles}
        onClick={clickable ? onClick : undefined}
        role={role || (clickable ? 'button' : undefined)}
        tabIndex={tabIndex ?? (clickable ? 0 : undefined)}
        data-variant={variant}
        data-size={size}
        data-elevation={elevation}
        data-selected={isSelected}
        {...handlers}
      >
        {/* Glass background */}
        {enableGlass && <div className={styles.glassBackground} />}

        {/* Border highlight */}
        <div className={styles.borderHighlight} />

        {/* Content */}
        <div className={styles.content}>{children}</div>
      </div>
    );
  }
);

GlassCard.displayName = 'GlassCard';

/**
 * GlassCard with header and optional footer
 */
export interface GlassCardWithHeaderProps extends GlassCardProps {
  /** Card header content */
  header?: React.ReactNode;
  /** Card title */
  title?: string;
  /** Card subtitle */
  subtitle?: string;
  /** Card footer content */
  footer?: React.ReactNode;
}

export const GlassCardWithHeader = forwardRef<HTMLDivElement, GlassCardWithHeaderProps>(
  ({ header, title, subtitle, footer, children, ...props }, ref) => {
    return (
      <GlassCard ref={ref} {...props}>
        {(header || title || subtitle) && (
          <div className={styles.header}>
            {header || (
              <>
                {title && <h3 className={styles.title}>{title}</h3>}
                {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
              </>
            )}
          </div>
        )}
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </GlassCard>
    );
  }
);

GlassCardWithHeader.displayName = 'GlassCardWithHeader';

export default GlassCard;
