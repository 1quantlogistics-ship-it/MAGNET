/**
 * MAGNET UI Floating Micro Window
 *
 * VisionOS-style floating glass panel component.
 * Primary container for UI panels and modals.
 */

import React, { forwardRef, useCallback, useMemo, useEffect, useRef } from 'react';
import type { ComponentContract } from '../../types/contracts';
import type { PanelId, PanelDepth, WindowVariant } from '../../types/common';
import { useSoftFocus } from '../../hooks/useSoftFocus';
import { useProximityGlow } from '../../hooks/useProximityGlow';
import { useDynamicShadow } from '../../hooks/useDynamicShadow';
import { usePresenceAnimation, EASING } from '../../hooks/useAnimationScheduler';
import { VISIONOS_TIMING } from '../../types/common';
import styles from './FloatingMicroWindow.module.css';

/**
 * FloatingMicroWindow props
 */
export interface FloatingMicroWindowProps {
  /** Panel identifier */
  panelId: PanelId;
  /** Panel depth layer */
  depth?: PanelDepth;
  /** Window variant */
  variant?: WindowVariant;
  /** Window title */
  title?: string;
  /** Whether window is visible */
  isVisible?: boolean;
  /** Enable glass blur effect */
  enableGlass?: boolean;
  /** Enable proximity glow */
  enableGlow?: boolean;
  /** Enable dynamic shadow */
  enableShadow?: boolean;
  /** Enable soft focus */
  enableFocus?: boolean;
  /** Enable parallax effect */
  enableParallax?: boolean;
  /** Custom className */
  className?: string;
  /** Custom styles */
  style?: React.CSSProperties;
  /** Header content */
  header?: React.ReactNode;
  /** Footer content */
  footer?: React.ReactNode;
  /** Children content */
  children?: React.ReactNode;
}

/**
 * FloatingMicroWindow events
 */
export interface FloatingMicroWindowEvents {
  onFocus: () => void;
  onBlur: () => void;
  onClose: () => void;
  onMinimize: () => void;
  onMaximize: () => void;
}

/**
 * Component contract type
 */
export type FloatingMicroWindowContract = ComponentContract<
  FloatingMicroWindowProps,
  FloatingMicroWindowEvents
>;

/**
 * FloatingMicroWindow component
 */
export const FloatingMicroWindow = forwardRef<
  HTMLDivElement,
  FloatingMicroWindowProps & Partial<FloatingMicroWindowEvents>
>(
  (
    {
      panelId,
      depth = 'mid',
      variant = 'default',
      title,
      isVisible = true,
      enableGlass = true,
      enableGlow = true,
      enableShadow = true,
      enableFocus = true,
      enableParallax = false,
      className = '',
      style,
      header,
      footer,
      children,
      onFocus,
      onBlur,
      onClose,
      onMinimize,
      onMaximize,
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement>(null);

    // Presence animation
    const presence = usePresenceAnimation(isVisible, {
      enterDuration: VISIONOS_TIMING.panelEnter,
      exitDuration: VISIONOS_TIMING.cardExpand,
      enterEasing: EASING.spring,
      exitEasing: EASING.easeOut,
    });

    // Soft focus
    const focus = useSoftFocus({
      panelId,
      depth,
      focusOnHover: enableFocus,
      focusOnClick: enableFocus,
    });

    // Proximity glow
    const glow = useProximityGlow({
      enabled: enableGlow,
      maxRadius: 300,
      maxIntensity: 0.08,
      color: 'rgba(255, 255, 255, 0.4)',
    });

    // Dynamic shadow
    const shadow = useDynamicShadow({
      enabled: enableShadow,
      elevation: depth === 'near' ? 3 : depth === 'mid' ? 2 : 1,
      intensity: 1,
      trackPointer: false,
    });

    // Handle focus changes
    useEffect(() => {
      if (focus.isFocused) {
        onFocus?.();
      } else {
        onBlur?.();
      }
    }, [focus.isFocused, onFocus, onBlur]);

    // Compute variant class
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

    // Compute combined styles
    const combinedStyles = useMemo((): React.CSSProperties => {
      const baseStyles: React.CSSProperties = {
        ...style,
        ...shadow.style,
        opacity: presence.progress,
        transform: `scale(${0.95 + presence.progress * 0.05}) translateY(${(1 - presence.progress) * 20}px)`,
        pointerEvents: presence.isVisible ? 'auto' : 'none',
      };

      if (enableFocus) {
        baseStyles.filter = focus.blurStyle;
        baseStyles.zIndex = focus.focusStyles.zIndex;
      }

      return baseStyles;
    }, [style, shadow.style, presence.progress, presence.isVisible, enableFocus, focus.blurStyle, focus.focusStyles.zIndex]);

    // Handle close
    const handleClose = useCallback(() => {
      onClose?.();
    }, [onClose]);

    // Handle minimize
    const handleMinimize = useCallback(() => {
      onMinimize?.();
    }, [onMinimize]);

    // Handle maximize
    const handleMaximize = useCallback(() => {
      onMaximize?.();
    }, [onMaximize]);

    if (!presence.isVisible) {
      return null;
    }

    return (
      <div
        ref={(node) => {
          // Handle both refs
          (containerRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
          if (typeof ref === 'function') {
            ref(node);
          } else if (ref) {
            ref.current = node;
          }
          // Also assign to glow ref
          if (node) {
            (glow.ref as React.MutableRefObject<HTMLElement | null>).current = node;
          }
        }}
        className={`${styles.container} ${variantClass} ${className}`}
        style={combinedStyles}
        data-panel-id={panelId}
        data-depth={depth}
        data-variant={variant}
        data-focused={focus.isFocused}
        {...focus.handlers}
      >
        {/* Glass background */}
        {enableGlass && <div className={styles.glassBackground} />}

        {/* Proximity glow overlay */}
        {enableGlow && glow.glow.isActive && (
          <div className={styles.glowOverlay} style={glow.glowStyle} />
        )}

        {/* Border highlight */}
        <div className={styles.borderHighlight} />

        {/* Header */}
        {(title || header) && (
          <div className={styles.header}>
            {title && <h2 className={styles.title}>{title}</h2>}
            {header}
            <div className={styles.windowControls}>
              {onMinimize && (
                <button
                  className={styles.windowControl}
                  onClick={handleMinimize}
                  aria-label="Minimize"
                >
                  <span className={styles.controlIcon}>-</span>
                </button>
              )}
              {onMaximize && (
                <button
                  className={styles.windowControl}
                  onClick={handleMaximize}
                  aria-label="Maximize"
                >
                  <span className={styles.controlIcon}>+</span>
                </button>
              )}
              {onClose && (
                <button
                  className={styles.windowControl}
                  onClick={handleClose}
                  aria-label="Close"
                >
                  <span className={styles.controlIcon}>&times;</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        <div className={styles.content}>{children}</div>

        {/* Footer */}
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    );
  }
);

FloatingMicroWindow.displayName = 'FloatingMicroWindow';

export default FloatingMicroWindow;
