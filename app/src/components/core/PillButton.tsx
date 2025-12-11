/**
 * MAGNET UI Pill Button
 *
 * VisionOS-style pill-shaped button component.
 * Primary interactive element with hover and press states.
 */

import React, { forwardRef, useCallback, useMemo } from 'react';
import type { ButtonVariant, Size } from '../../types/common';
import { useHoverGlow } from '../../hooks/useProximityGlow';
import { useHoverTilt } from '../../hooks/useDragTilt';
import { usePresenceAnimation, EASING } from '../../hooks/useAnimationScheduler';
import { VISIONOS_TIMING } from '../../types/common';
import styles from './PillButton.module.css';

/**
 * PillButton props
 */
export interface PillButtonProps {
  /** Button variant */
  variant?: ButtonVariant;
  /** Button size */
  size?: Size;
  /** Button text */
  children: React.ReactNode;
  /** Icon before text */
  iconBefore?: React.ReactNode;
  /** Icon after text */
  iconAfter?: React.ReactNode;
  /** Loading state */
  isLoading?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Full width */
  fullWidth?: boolean;
  /** Enable hover glow */
  enableGlow?: boolean;
  /** Enable hover tilt */
  enableTilt?: boolean;
  /** Button type */
  type?: 'button' | 'submit' | 'reset';
  /** Click handler */
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  /** Custom className */
  className?: string;
  /** Custom styles */
  style?: React.CSSProperties;
  /** Aria label */
  'aria-label'?: string;
}

/**
 * PillButton component
 */
export const PillButton = forwardRef<HTMLButtonElement, PillButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      children,
      iconBefore,
      iconAfter,
      isLoading = false,
      disabled = false,
      fullWidth = false,
      enableGlow = true,
      enableTilt = false,
      type = 'button',
      onClick,
      className = '',
      style,
      'aria-label': ariaLabel,
    },
    ref
  ) => {
    // Hover glow effect
    const glow = useHoverGlow({
      enabled: enableGlow && !disabled && !isLoading,
      color: variant === 'primary' ? 'rgba(10, 132, 255, 0.3)' : 'rgba(255, 255, 255, 0.2)',
      intensity: 0.15,
      radius: 40,
    });

    // Hover tilt effect
    const tilt = useHoverTilt({
      enabled: enableTilt && !disabled && !isLoading,
      maxRotation: 5,
    });

    // Loading spinner presence
    const loadingPresence = usePresenceAnimation(isLoading, {
      enterDuration: VISIONOS_TIMING.tooltipReveal,
      exitDuration: 150,
    });

    // Compute variant class
    const variantClass = useMemo(() => {
      switch (variant) {
        case 'primary':
          return styles.variantPrimary;
        case 'secondary':
          return styles.variantSecondary;
        case 'ghost':
          return styles.variantGhost;
        case 'danger':
          return styles.variantDanger;
        default:
          return styles.variantPrimary;
      }
    }, [variant]);

    // Compute size class
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
        ...glow.glowStyle,
        ...(enableTilt ? tilt.style : {}),
      };
    }, [style, glow.glowStyle, enableTilt, tilt.style]);

    // Handle click
    const handleClick = useCallback(
      (event: React.MouseEvent<HTMLButtonElement>) => {
        if (!disabled && !isLoading) {
          onClick?.(event);
        }
      },
      [disabled, isLoading, onClick]
    );

    // Combined handlers
    const handlers = useMemo(() => {
      const combined: Record<string, React.EventHandler<React.SyntheticEvent>> = {
        ...glow.handlers,
      };

      if (enableTilt) {
        combined.onMouseMove = tilt.handlers.onMouseMove;
        combined.onMouseLeave = (e) => {
          glow.handlers.onMouseLeave();
          tilt.handlers.onMouseLeave();
        };
        combined.onMouseEnter = glow.handlers.onMouseEnter;
      }

      return combined;
    }, [glow.handlers, enableTilt, tilt.handlers]);

    return (
      <button
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
        type={type}
        className={`${styles.button} ${variantClass} ${sizeClass} ${fullWidth ? styles.fullWidth : ''} ${className}`}
        style={combinedStyles}
        disabled={disabled || isLoading}
        onClick={handleClick}
        aria-label={ariaLabel}
        aria-busy={isLoading}
        data-variant={variant}
        data-size={size}
        data-loading={isLoading}
        {...handlers}
      >
        {/* Loading spinner */}
        {loadingPresence.isVisible && (
          <span
            className={styles.loadingSpinner}
            style={{ opacity: loadingPresence.progress }}
          >
            <span className={styles.spinnerInner} />
          </span>
        )}

        {/* Icon before */}
        {iconBefore && !isLoading && (
          <span className={styles.iconBefore}>{iconBefore}</span>
        )}

        {/* Button text */}
        <span
          className={styles.label}
          style={{ opacity: isLoading ? 0 : 1 }}
        >
          {children}
        </span>

        {/* Icon after */}
        {iconAfter && !isLoading && (
          <span className={styles.iconAfter}>{iconAfter}</span>
        )}
      </button>
    );
  }
);

PillButton.displayName = 'PillButton';

/**
 * Icon-only pill button variant
 */
export const IconPillButton = forwardRef<
  HTMLButtonElement,
  Omit<PillButtonProps, 'children' | 'iconBefore' | 'iconAfter'> & {
    icon: React.ReactNode;
  }
>(({ icon, size = 'md', ...props }, ref) => {
  return (
    <PillButton ref={ref} size={size} {...props} className={`${styles.iconOnly} ${props.className || ''}`}>
      {icon}
    </PillButton>
  );
});

IconPillButton.displayName = 'IconPillButton';

export default PillButton;
