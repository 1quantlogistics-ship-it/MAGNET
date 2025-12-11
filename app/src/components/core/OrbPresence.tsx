/**
 * MAGNET UI Orb Presence
 *
 * VisionOS-style AI presence indicator.
 * Animated orb that shows AI agent activity state.
 */

import React, { forwardRef, useMemo, useEffect } from 'react';
import { useAnimationScheduler } from '../../hooks/useAnimationScheduler';
import { useSpringTransition, SPRING_PRESETS } from '../../hooks/useSpringTransition';
import { VISIONOS_TIMING } from '../../types/common';
import styles from './OrbPresence.module.css';

/**
 * Orb activity states
 */
export type OrbState =
  | 'idle'        // Subtle breathing
  | 'listening'   // Gentle pulse
  | 'thinking'    // Active rotation
  | 'speaking'    // Wave animation
  | 'error'       // Red pulse
  | 'success'     // Green flash
  | 'hidden';     // Not visible

/**
 * OrbPresence props
 */
export interface OrbPresenceProps {
  /** Current orb state */
  state?: OrbState;
  /** Orb size in pixels */
  size?: number;
  /** Primary color */
  color?: string;
  /** Secondary color (gradient) */
  secondaryColor?: string;
  /** Glow intensity (0-1) */
  glowIntensity?: number;
  /** Animation speed multiplier */
  speed?: number;
  /** Custom className */
  className?: string;
  /** Custom styles */
  style?: React.CSSProperties;
  /** Click handler */
  onClick?: () => void;
  /** Aria label */
  'aria-label'?: string;
}

/**
 * Default colors for states
 */
const STATE_COLORS: Record<OrbState, { primary: string; secondary: string }> = {
  idle: {
    primary: 'rgba(10, 132, 255, 0.8)',
    secondary: 'rgba(88, 86, 214, 0.6)',
  },
  listening: {
    primary: 'rgba(10, 132, 255, 0.9)',
    secondary: 'rgba(94, 92, 230, 0.7)',
  },
  thinking: {
    primary: 'rgba(175, 82, 222, 0.9)',
    secondary: 'rgba(10, 132, 255, 0.8)',
  },
  speaking: {
    primary: 'rgba(50, 215, 75, 0.9)',
    secondary: 'rgba(10, 132, 255, 0.7)',
  },
  error: {
    primary: 'rgba(255, 69, 58, 0.9)',
    secondary: 'rgba(255, 149, 0, 0.7)',
  },
  success: {
    primary: 'rgba(50, 215, 75, 0.95)',
    secondary: 'rgba(48, 209, 88, 0.8)',
  },
  hidden: {
    primary: 'transparent',
    secondary: 'transparent',
  },
};

/**
 * OrbPresence component
 */
export const OrbPresence = forwardRef<HTMLDivElement, OrbPresenceProps>(
  (
    {
      state = 'idle',
      size = 40,
      color,
      secondaryColor,
      glowIntensity = 0.5,
      speed = 1,
      className = '',
      style,
      onClick,
      'aria-label': ariaLabel,
    },
    ref
  ) => {
    // Get state colors
    const colors = useMemo(() => {
      const stateColors = STATE_COLORS[state] || STATE_COLORS.idle;
      return {
        primary: color || stateColors.primary,
        secondary: secondaryColor || stateColors.secondary,
      };
    }, [state, color, secondaryColor]);

    // Visibility spring
    const visibility = useSpringTransition(state === 'hidden' ? 0 : 1, {
      ...SPRING_PRESETS.gentle,
    });

    // Breathing animation for idle state
    const breathing = useAnimationScheduler(
      () => {},
      {
        duration: (1000 / VISIONOS_TIMING.orbBreathe) / speed,
        autoStart: state === 'idle',
        loop: state === 'idle',
      }
    );

    // Pulse animation for listening/thinking
    const pulse = useAnimationScheduler(
      () => {},
      {
        duration: 1500 / speed,
        autoStart: state === 'listening' || state === 'thinking',
        loop: state === 'listening' || state === 'thinking',
      }
    );

    // Calculate animation values
    const animationValues = useMemo(() => {
      const breatheScale = state === 'idle' ? 1 + Math.sin(breathing.progress * Math.PI * 2) * 0.05 : 1;
      const pulseScale = (state === 'listening' || state === 'thinking')
        ? 1 + Math.sin(pulse.progress * Math.PI * 2) * 0.1
        : 1;

      const rotation = state === 'thinking'
        ? pulse.progress * 360 * speed
        : 0;

      const scale = breatheScale * pulseScale * visibility.value;

      return {
        scale,
        rotation,
        glowSize: glowIntensity * (1 + (pulseScale - 1) * 2),
      };
    }, [state, breathing.progress, pulse.progress, visibility.value, speed, glowIntensity]);

    // State-specific class
    const stateClass = useMemo(() => {
      switch (state) {
        case 'idle':
          return styles.stateIdle;
        case 'listening':
          return styles.stateListening;
        case 'thinking':
          return styles.stateThinking;
        case 'speaking':
          return styles.stateSpeaking;
        case 'error':
          return styles.stateError;
        case 'success':
          return styles.stateSuccess;
        default:
          return '';
      }
    }, [state]);

    // Combined styles
    const combinedStyles = useMemo((): React.CSSProperties => {
      return {
        ...style,
        width: size,
        height: size,
        opacity: visibility.value,
        transform: `scale(${animationValues.scale}) rotate(${animationValues.rotation}deg)`,
        '--orb-primary': colors.primary,
        '--orb-secondary': colors.secondary,
        '--orb-glow-size': `${size * animationValues.glowSize}px`,
        '--orb-glow-intensity': glowIntensity,
      } as React.CSSProperties;
    }, [style, size, visibility.value, animationValues, colors, glowIntensity]);

    if (state === 'hidden' && visibility.value < 0.01) {
      return null;
    }

    return (
      <div
        ref={ref}
        className={`${styles.orb} ${stateClass} ${onClick ? styles.clickable : ''} ${className}`}
        style={combinedStyles}
        onClick={onClick}
        role={onClick ? 'button' : 'img'}
        aria-label={ariaLabel || `AI ${state}`}
        tabIndex={onClick ? 0 : undefined}
        data-state={state}
      >
        {/* Core orb */}
        <div className={styles.core} />

        {/* Inner glow layer */}
        <div className={styles.innerGlow} />

        {/* Outer glow layer */}
        <div className={styles.outerGlow} />

        {/* Ring (for thinking state) */}
        {state === 'thinking' && (
          <div className={styles.ring} />
        )}

        {/* Wave bars (for speaking state) */}
        {state === 'speaking' && (
          <div className={styles.waveBars}>
            <span className={styles.waveBar} style={{ animationDelay: '0ms' }} />
            <span className={styles.waveBar} style={{ animationDelay: '150ms' }} />
            <span className={styles.waveBar} style={{ animationDelay: '300ms' }} />
          </div>
        )}
      </div>
    );
  }
);

OrbPresence.displayName = 'OrbPresence';

/**
 * Mini orb for inline status indicators
 */
export const MiniOrb = forwardRef<HTMLDivElement, Omit<OrbPresenceProps, 'size'>>(
  (props, ref) => {
    return <OrbPresence ref={ref} size={16} glowIntensity={0.3} {...props} />;
  }
);

MiniOrb.displayName = 'MiniOrb';

export default OrbPresence;
